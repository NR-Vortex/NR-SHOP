from core.admin_settings import content_prefix
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.session import async_session
from database.models import VPNOrderDetails
from modules.checkout.coupon import (
    CouponExpiredError,
    CouponInactiveError,
    CouponMinimumAmountError,
    CouponNotFoundError,
    CouponNotStartedError,
    CouponOrderStatusError,
    CouponUsageLimitError,
    CouponUserLimitError,
    apply_coupon_to_order,
)
from modules.checkout.keyboards import (
    checkout_back_keyboard,
    checkout_payment_keyboard,
    order_summary_keyboard,
    payment_back_keyboard,
    payment_receipt_keyboard,
)
from modules.checkout.payment import build_payment_text, payment_is_configured
from modules.checkout.service import (
    OrderNotFoundError,
    OrderStatusError,
    ProductUnavailableError,
    cancel_order,
    continue_without_discount,
    create_order,
    get_user_order,
)
from modules.checkout.states import CheckoutStates


router = Router(name="checkout")


async def _vpn_invoice_for_order(session, order):
    detail = (await session.execute(
        select(VPNOrderDetails).where(VPNOrderDetails.order_id == order.id)
    )).scalar_one_or_none()
    if detail is None:
        return None
    from modules.vpn.keyboards import vpn_invoice_keyboard
    from modules.vpn.router import invoice
    return invoice(order, detail), vpn_invoice_keyboard(order.order_number)


def get_order_text(order):
    duration = f"{order.duration_days} روز" if order.duration_days else "ثبت نشده"
    service_type = escape(order.service_type) if order.service_type else "ثبت نشده"
    delivery = escape(order.delivery_method) if order.delivery_method else "ثبت نشده"
    return content_prefix("texts:invoice") + f"""
🛍 <b>مرور سفارش</b>

━━━━━━━━━━━━━━━━━━

📦 <b>محصول:</b>
{escape(order.product_name)}

⏳ <b>مدت سرویس:</b>
{duration}

⚙️ <b>نوع سرویس:</b>
{service_type}

🚚 <b>روش تحویل:</b>
{delivery}

━━━━━━━━━━━━━━━━━━

💰 <b>قیمت محصول:</b>
{order.product_price:,} تومان

🎟 <b>تخفیف:</b>
{order.discount_amount:,} تومان

━━━━━━━━━━━━━━━━━━

💳 <b>مبلغ قابل پرداخت:</b>
{order.final_amount:,} تومان

🧾 <b>شماره سفارش:</b>
<code>{order.order_number}</code>
"""


@router.callback_query(F.data.startswith("checkout:buy:"))
async def buy_product_handler(callback: CallbackQuery, state: FSMContext):
    try:
        product_id = int(callback.data.split(":")[-1])
    except (TypeError, ValueError):
        await callback.answer("محصول نامعتبر است.", show_alert=True)
        return

    async with async_session() as session:
        try:
            order = await create_order(session, callback.from_user.id, product_id)
        except ProductUnavailableError:
            await callback.answer("این محصول در حال حاضر موجود نیست.", show_alert=True)
            return

    await state.clear()
    await callback.answer("سفارش ایجاد شد.")
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            get_order_text(order),
            reply_markup=order_summary_keyboard(order.order_number),
        )


@router.callback_query(F.data.startswith("checkout:coupon:"))
async def request_coupon_handler(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[-1]
    async with async_session() as session:
        try:
            order = await get_user_order(session, order_number, callback.from_user.id)
        except OrderNotFoundError:
            await callback.answer("سفارش پیدا نشد.", show_alert=True)
            return
        if order.status != "awaiting_discount":
            await callback.answer("امکان تغییر تخفیف وجود ندارد.", show_alert=True)
            return

    await state.update_data(order_number=order_number)
    await state.set_state(CheckoutStates.waiting_discount_code)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🎟 <b>کد تخفیف NR SHOP</b>\n\n"
            "لطفاً کد تخفیف خود را ارسال کنید.\n\n"
            "برای انصراف /cancel را ارسال کنید."
        )


@router.message(CheckoutStates.waiting_discount_code)
async def coupon_code_handler(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("لطفاً کد تخفیف را به‌صورت متنی ارسال کنید.")
        return
    code = message.text.strip()
    if code == "/cancel":
        await state.clear(); await message.answer("وارد کردن کد تخفیف لغو شد."); return
    order_number = (await state.get_data()).get("order_number")
    if not order_number:
        await state.clear(); await message.answer("اطلاعات سفارش پیدا نشد. لطفاً دوباره خرید کنید."); return

    async with async_session() as session:
        try:
            order = await apply_coupon_to_order(session, order_number, message.from_user.id, code)
        except CouponNotFoundError:
            await message.answer("❌ کد تخفیف معتبر نیست. دوباره تلاش کنید."); return
        except CouponInactiveError:
            await message.answer("❌ این کد تخفیف غیرفعال است."); return
        except CouponExpiredError:
            await message.answer("⏰ مهلت استفاده از این کد تمام شده است."); return
        except CouponNotStartedError:
            await message.answer("⏳ زمان استفاده از این کد هنوز شروع نشده است."); return
        except CouponMinimumAmountError:
            await message.answer("مبلغ سفارش برای استفاده از این کد کافی نیست."); return
        except CouponUsageLimitError:
            await message.answer("ظرفیت استفاده از این کد تکمیل شده است."); return
        except CouponUserLimitError:
            await message.answer("شما قبلاً به تعداد مجاز از این کد استفاده کرده‌اید."); return
        except CouponOrderStatusError:
            await state.clear(); await message.answer("وضعیت سفارش اجازه استفاده از کد تخفیف را نمی‌دهد."); return
        except ValueError:
            await message.answer("کد تخفیف قابل استفاده نیست."); return

    await state.clear()
    await message.answer("✅ کد تخفیف با موفقیت اعمال شد.")
    vpn_view = None
    async with async_session() as session:
        vpn_view = await _vpn_invoice_for_order(session, order)
    if vpn_view:
        text, keyboard = vpn_view
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(
            get_order_text(order),
            reply_markup=checkout_payment_keyboard(order.order_number),
        )


@router.callback_query(F.data.startswith("checkout:skip:"))
async def skip_coupon_handler(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[-1]
    async with async_session() as session:
        try:
            existing = await get_user_order(session, order_number, callback.from_user.id)
            order = await continue_without_discount(session, existing.id)
        except (OrderNotFoundError, OrderStatusError):
            await callback.answer("سفارش قابل پردازش نیست.", show_alert=True); return
    await state.clear(); await callback.answer()
    if isinstance(callback.message, Message):
        async with async_session() as session:
            vpn_view = await _vpn_invoice_for_order(session, order)
        if vpn_view:
            text, keyboard = vpn_view
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(
                get_order_text(order),
                reply_markup=checkout_payment_keyboard(order.order_number),
            )


@router.callback_query(F.data.startswith("checkout:cancel:"))
async def cancel_order_handler(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[-1]
    async with async_session() as session:
        try:
            await cancel_order(session, order_number, callback.from_user.id)
        except (OrderNotFoundError, OrderStatusError):
            await callback.answer("امکان لغو این سفارش وجود ندارد.", show_alert=True); return
    await state.clear(); await callback.answer("سفارش لغو شد.")
    if isinstance(callback.message, Message):
        await callback.message.edit_text("❌ سفارش شما لغو شد.", reply_markup=checkout_back_keyboard())


@router.callback_query(F.data.startswith("checkout:pay:"))
async def payment_handler(callback: CallbackQuery):
    order_number = callback.data.split(":")[-1]
    if not payment_is_configured():
        await callback.answer(
            "اطلاعات حساب بانکی هنوز تنظیم نشده است.",
            show_alert=True,
        )
        return

    async with async_session() as session:
        try:
            order = await get_user_order(session, order_number, callback.from_user.id)
        except OrderNotFoundError:
            await callback.answer("سفارش پیدا نشد.", show_alert=True)
            return
        if order.status != "awaiting_payment":
            await callback.answer("این سفارش آماده پرداخت نیست.", show_alert=True)
            return
        payment_text = build_payment_text(order)
        vpn_detail = (await session.execute(
            select(VPNOrderDetails).where(VPNOrderDetails.order_id == order.id)
        )).scalar_one_or_none()
        if vpn_detail:
            payment_text += (
                f"\n\n👤 <b>نام کاربری VPN:</b> {escape(vpn_detail.username)}"
                f"\n🌐 <b>سرور:</b> {escape(vpn_detail.server_name)}"
                f"\n⌛ <b>حجم:</b> {escape(vpn_detail.volume)}"
            )

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            payment_text,
            reply_markup=payment_receipt_keyboard(order_number),
        )


@router.callback_query(F.data.startswith("checkout:summary:"))
async def checkout_summary_handler(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[-1]
    async with async_session() as session:
        try:
            order = await get_user_order(session, order_number, callback.from_user.id)
        except OrderNotFoundError:
            await callback.answer("سفارش پیدا نشد.", show_alert=True)
            return
        if order.status != "awaiting_payment":
            await callback.answer("امکان مشاهده این سفارش وجود ندارد.", show_alert=True)
            return

    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            get_order_text(order),
            reply_markup=checkout_payment_keyboard(order.order_number),
        )
