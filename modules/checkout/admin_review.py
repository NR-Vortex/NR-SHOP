import logging
import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv
from sqlalchemy import select

from database.session import async_session
from modules.checkout.service import (
    OrderNotFoundError,
    OrderStatusError,
    approve_order,
    get_order,
    reject_order,
)
from modules.checkout.states import CheckoutStates
from database.models import AICodeRequest, Category, Product, VPNOrderDetails
from modules.vpn.provisioning import ProvisioningError, provision_vpn_order
from modules.vpn.result import build_vpn_approved_text, build_vpn_rejected_text, vpn_result_keyboard


load_dotenv()
logger = logging.getLogger(__name__)
router = Router(name="admin_order_review")


@router.callback_query(F.data.startswith("admin:ai_code:"))
async def ai_code_admin_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    try: order_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError: await callback.answer("درخواست نامعتبر است.", show_alert=True); return
    await state.update_data(ai_code_order_id=order_id)
    await state.set_state(CheckoutStates.waiting_ai_login_code)
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("🔐 کد ورود و 2FA را برای مشتری ارسال کنید:")


@router.message(CheckoutStates.waiting_ai_login_code)
async def ai_code_admin_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    code = (message.text or "").strip()
    if not code: await message.answer("کد معتبر ارسال کنید."); return
    order_id = (await state.get_data()).get("ai_code_order_id")
    async with async_session() as session:
        request = (await session.execute(select(AICodeRequest).where(AICodeRequest.order_id == order_id, AICodeRequest.status == "pending"))).scalar_one_or_none()
        if not request: await state.clear(); await message.answer("درخواست فعال پیدا نشد."); return
        request.status = "answered"; request.response = code
        user_id = request.telegram_user_id
        await session.commit()
    await state.clear()
    await message.bot.send_message(user_id, f"🔐 <b>کد ورود و 2FA شما</b>\n\n<code>{code}</code>\n\nلطفاً این اطلاعات را محرمانه نگه دارید.", parse_mode="HTML")
    await message.answer("✅ کد برای مشتری ارسال شد.")


def get_admin_ids():
    return {int(value.strip()) for value in os.getenv("ADMIN_IDS", "").split(",") if value.strip().isdigit()}


def is_admin(user_id: int):
    return user_id in get_admin_ids()


def admin_order_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 تأیید پرداخت", callback_data=f"admin:approve:{order_id}")],
        [InlineKeyboardButton(text="🔴 رد پرداخت", callback_data=f"admin:reject:{order_id}")],
    ])


async def notify_admins(bot, order, customer_name: str):
    admin_ids = get_admin_ids()
    if not admin_ids: raise RuntimeError("ADMIN_IDS is empty")
    caption = f"""
📥 <b>سفارش جدید NR SHOP</b>

🧾 شماره سفارش: <code>{order.order_number}</code>
👤 مشتری: {customer_name}
🆔 شناسه مشتری: <code>{order.telegram_user_id}</code>
📦 محصول: {order.product_name}
💰 مبلغ اصلی: {order.product_price:,} تومان
🎟 تخفیف: {order.discount_amount:,} تومان
💳 مبلغ پرداختی: <b>{order.final_amount:,} تومان</b>

📌 وضعیت: در انتظار بررسی
"""
    successful = 0
    for admin_id in admin_ids:
        try:
            if order.receipt_type == "photo":
                await bot.send_photo(admin_id, order.receipt_file_id, caption=caption, parse_mode="HTML", reply_markup=admin_order_keyboard(order.id))
            else:
                await bot.send_document(admin_id, order.receipt_file_id, caption=caption, parse_mode="HTML", reply_markup=admin_order_keyboard(order.id))
            successful += 1
        except Exception:
            logger.exception("Could not notify admin %s", admin_id)
    if successful == 0: raise RuntimeError("Could not deliver receipt to any admin")
    return successful


@router.callback_query(F.data.startswith("admin:approve:"))
async def approve_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("شما اجازه انجام این عملیات را ندارید.", show_alert=True); return
    try: order_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("شناسه سفارش نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        try: order = await approve_order(session, order_id, "Payment approved by admin")
        except (OrderNotFoundError, OrderStatusError):
            await callback.answer("این سفارش قبلاً بررسی شده است.", show_alert=True); return

    provisioning_message = ""
    vpn_detail = None
    is_ai_order = False
    async with async_session() as session:
        vpn_detail = (await session.execute(select(VPNOrderDetails).where(VPNOrderDetails.order_id == order.id))).scalar_one_or_none()
        if vpn_detail:
            try:
                await provision_vpn_order(session, order.id)
                provisioning_message = "\n\n💎 سرویس VPN برای تحویل آماده شد."
            except ProvisioningError:
                provisioning_message = "\n\n⚠️ پرداخت تأیید شد، اما ساخت خودکار سرویس انجام نشد و نیاز به تلاش مجدد مدیر دارد."
        else:
            is_ai_order = (await session.execute(
                select(Category.id)
                .join(Product, Product.category_id == Category.id)
                .where(Product.id == order.product_id, Category.section == "ai")
            )).scalar_one_or_none() is not None
            if is_ai_order:
                order.status = "provisioning"
                await session.commit()
                await session.refresh(order)
    await callback.answer("پرداخت تأیید شد.")
    if isinstance(callback.message, Message): await callback.message.edit_reply_markup(reply_markup=None)
    try:
        if vpn_detail:
            text, ready = build_vpn_approved_text(order, vpn_detail)
            await callback.bot.send_message(order.telegram_user_id, text, parse_mode="HTML", reply_markup=vpn_result_keyboard(order.order_number, ready))
        elif is_ai_order:
            async with async_session() as session:
                account_type = (await session.execute(select(Product.account_type).where(Product.id == order.product_id))).scalar_one_or_none() or "shared"
            if account_type == "dedicated":
                await callback.bot.send_message(
                    order.telegram_user_id,
                    "✅ <b>پرداخت شما با موفقیت تأیید شد!</b>\n\n"
                    "💎 سفارش شما تأیید شد.\n\n"
                    "برای فعال‌سازی حساب اختصاصی، ایمیل خود را ارسال کنید.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📧 ثبت ایمیل", callback_data=f"ai:email:{order.id}")]]),
                )
                return
            await callback.bot.send_message(
                order.telegram_user_id,
                "✅ <b>پرداخت شما با موفقیت تأیید شد!</b>\n\n"
                "💎 سفارش شما تأیید شد.\n\n"
                "در حال آماده‌سازی اشتراک شما هستیم...",
                parse_mode="HTML",
            )
            await callback.bot.send_message(
                order.telegram_user_id,
                "⏳ <b>در حال ساخت حساب کاربری شما هستیم...</b>\n\n"
                "لطفاً منتظر بمانید. پس از آماده‌شدن اشتراک، اطلاعات حساب برای شما ارسال خواهد شد. ❤️\n\n"
                "💎 از اعتماد شما به NR SHOP سپاسگزاریم.",
                parse_mode="HTML",
            )
        else:
            await callback.bot.send_message(order.telegram_user_id, f"🎉 <b>پرداخت سفارش شما تأیید شد!</b>\n\n🧾 سفارش: <code>{order.order_number}</code>\n📦 محصول: {order.product_name}\n💰 مبلغ: {order.final_amount:,} تومان{provisioning_message}", parse_mode="HTML")
    except Exception: logger.exception("Customer notification failed")


@router.callback_query(F.data.startswith("admin:reject:"))
async def reject_request(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    order_id = int(callback.data.split(":")[-1])
    await state.update_data(order_id=order_id, admin_chat_id=callback.message.chat.id, admin_message_id=callback.message.message_id)
    await state.set_state(CheckoutStates.waiting_rejection_reason)
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("🔴 لطفاً دلیل رد پرداخت را ارسال کنید.")


@router.message(CheckoutStates.waiting_rejection_reason)
async def reject_reason_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    if not message.text or not message.text.strip():
        await message.answer("لطفاً دلیل رد را به‌صورت متن ارسال کنید."); return
    data = await state.get_data()
    try:
        async with async_session() as session:
            order = await reject_order(session, data["order_id"], message.text.strip())
    except (OrderNotFoundError, OrderStatusError):
        await state.clear(); await message.answer("سفارش پیدا نشد یا قبلاً بررسی شده است."); return
    await state.clear()
    try:
        async with async_session() as session:
            vpn_detail = (await session.execute(select(VPNOrderDetails).where(VPNOrderDetails.order_id == order.id))).scalar_one_or_none()
        if vpn_detail:
            await message.bot.send_message(order.telegram_user_id, build_vpn_rejected_text(order, vpn_detail), parse_mode="HTML", reply_markup=vpn_result_keyboard(order.order_number, False))
        else:
            await message.bot.send_message(order.telegram_user_id, f"❌ <b>پرداخت سفارش تأیید نشد.</b>\n\n🧾 سفارش: <code>{order.order_number}</code>\n📌 دلیل: {order.admin_note}", parse_mode="HTML")
        await message.bot.edit_message_reply_markup(chat_id=data["admin_chat_id"], message_id=data["admin_message_id"], reply_markup=None)
    except Exception: logger.exception("Rejection notification failed")
    await message.answer("🔴 سفارش با موفقیت رد شد.")
