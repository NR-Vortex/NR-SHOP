import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.session import async_session
from modules.checkout.admin_review import get_admin_ids, notify_admins
from modules.checkout.keyboards import receipt_request_keyboard
from modules.checkout.service import (
    OrderNotFoundError,
    OrderStatusError,
    get_user_order,
    submit_receipt,
)
from modules.checkout.states import CheckoutStates


logger = logging.getLogger(__name__)
router = Router(name="checkout_receipt")


@router.callback_query(F.data.startswith("checkout:receipt:"))
async def request_receipt(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[-1]
    async with async_session() as session:
        try:
            order = await get_user_order(session, order_number, callback.from_user.id)
        except OrderNotFoundError:
            await callback.answer("سفارش پیدا نشد.", show_alert=True); return
        if order.status != "awaiting_payment":
            await callback.answer("این سفارش آماده دریافت رسید نیست.", show_alert=True); return

    if not get_admin_ids():
        await callback.answer("شناسه مدیر تنظیم نشده است.", show_alert=True); return
    await state.update_data(order_number=order_number)
    await state.set_state(CheckoutStates.waiting_receipt)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📸 <b>ارسال رسید پرداخت NR SHOP</b>\n\n"
            "لطفاً تصویر رسید یا فایل PDF پرداخت را ارسال کنید.\n\n"
            "برای انصراف /cancel را ارسال کنید.",
            reply_markup=receipt_request_keyboard(order_number),
        )


async def process_receipt(message: Message, state: FSMContext, file_id: str, receipt_type: str):
    order_number = (await state.get_data()).get("order_number")
    if not order_number:
        await state.clear(); await message.answer("اطلاعات سفارش پیدا نشد."); return
    if not get_admin_ids():
        await message.answer("امکان ارسال رسید به مدیر وجود ندارد."); return
    try:
        async with async_session() as session:
            order = await submit_receipt(
                session, order_number, message.from_user.id, file_id, receipt_type
            )
            await notify_admins(message.bot, order, message.from_user.full_name)
    except (OrderNotFoundError, OrderStatusError):
        await state.clear(); await message.answer("سفارش پیدا نشد یا قبلاً بررسی شده است."); return
    except Exception:
        logger.exception("Receipt processing failed")
        await message.answer("خطا در ثبت رسید. لطفاً دوباره تلاش کنید."); return
    await state.clear()
    await message.answer(
        f"✅ <b>رسید شما دریافت شد.</b>\n\n"
        f"🧾 شماره سفارش: <code>{order.order_number}</code>\n\n"
        "📨 سفارش برای بررسی مدیر ارسال شد."
    )


@router.message(CheckoutStates.waiting_receipt, F.photo)
async def receive_photo(message: Message, state: FSMContext):
    await process_receipt(message, state, message.photo[-1].file_id, "photo")


@router.message(CheckoutStates.waiting_receipt, F.document)
async def receive_document(message: Message, state: FSMContext):
    allowed_types = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
    if message.document.mime_type not in allowed_types:
        await message.answer("❌ فقط فایل PDF یا تصویر رسید قابل قبول است."); return
    await process_receipt(message, state, message.document.file_id, "document")


@router.message(CheckoutStates.waiting_receipt, F.text == "/cancel")
async def cancel_receipt(message: Message, state: FSMContext):
    await state.clear(); await message.answer("ارسال رسید لغو شد.")
