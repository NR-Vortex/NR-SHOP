from core.admin_settings import content_prefix
import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.session import async_session
from modules.checkout.admin_review import get_admin_ids, is_admin
from modules.support.keyboards import (
    admin_support_keyboard, admin_ticket_keyboard, admin_tickets_keyboard,
    customer_ticket_keyboard, customer_tickets_keyboard, support_menu_keyboard,
)
from modules.support.service import (
    TicketAccessError, TicketClosedError, TicketNotFoundError, add_message,
    close_ticket, create_ticket, get_admin_tickets, get_customer_ticket,
    get_customer_tickets, get_ticket, get_ticket_messages, reopen_ticket,
)
from modules.support.states import SupportStates


logger = logging.getLogger(__name__)
router = Router(name="support")
STATUS_NAMES = {"open": "باز", "waiting_admin": "در انتظار پاسخ مدیر", "waiting_user": "در انتظار پاسخ مشتری", "closed": "بسته شده"}


def payload(message: Message):
    if message.photo:
        return dict(text=message.caption, message_type="photo", file_id=message.photo[-1].file_id, file_name=None, mime_type=None)
    if message.document:
        return dict(text=message.caption, message_type="document", file_id=message.document.file_id, file_name=message.document.file_name, mime_type=message.document.mime_type)
    if message.text: return dict(text=message.text, message_type="text", file_id=None, file_name=None, mime_type=None)
    return None


def history(ticket, messages):
    text = f"🎧 <b>تیکت پشتیبانی NR SHOP</b>\n\n🧾 <code>{ticket.ticket_number}</code>\n📌 وضعیت: {STATUS_NAMES.get(ticket.status, ticket.status)}\n📦 بخش: {escape(ticket.source_section)}\n\n━━━━━━━━━━━━━━\n"
    for item in messages[-12:]:
        sender = {"customer": "👤 مشتری", "admin": "👨‍💻 پشتیبانی", "system": "⚙️ سیستم"}.get(item.sender_type, "کاربر")
        text += f"\n<b>{sender}</b>\n{escape(item.text or '')}{'\n📎 فایل پیوست' if item.file_id else ''}\n"
    return text[:3900]


async def notify_admins(bot, text, ticket_number):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 مشاهده تیکت", callback_data=f"support:admin:ticket:{ticket_number}")]])
    for admin_id in get_admin_ids():
        try: await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=keyboard)
        except Exception: logger.exception("Support admin notification failed")


@router.callback_query(F.data.startswith("support:menu"))
async def support_menu(callback: CallbackQuery):
    section = callback.data.split(":")[2] if len(callback.data.split(":")) > 2 else "general"
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(content_prefix("texts:support") + "🎧 <b>پشتیبانی NR SHOP</b>\n\nتیکت جدید باز کن یا پاسخ تیکت‌هات رو ببین.", reply_markup=support_menu_keyboard(section))


@router.callback_query(F.data.startswith("support:new:"))
async def new_ticket(callback: CallbackQuery, state: FSMContext):
    if not get_admin_ids(): await callback.answer("سیستم پشتیبانی در دسترس نیست.", show_alert=True); return
    await state.update_data(source_section=callback.data.split(":")[-1]); await state.set_state(SupportStates.waiting_initial_message); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("📨 درخواست خود را به‌صورت متن ارسال کنید. برای انصراف /cancel")


@router.message(SupportStates.waiting_initial_message)
async def create_ticket_handler(message: Message, state: FSMContext):
    if not message.text or not message.text.strip(): await message.answer("لطفاً درخواست را به‌صورت متن ارسال کنید."); return
    if message.text == "/cancel": await state.clear(); await message.answer("ثبت درخواست لغو شد."); return
    data = await state.get_data()
    async with async_session() as session:
        ticket = await create_ticket(session, message.from_user.id, message.text, source_section=data.get("source_section", "general"))
    await state.clear()
    await notify_admins(message.bot, f"📥 <b>تیکت جدید</b>\n🧾 <code>{ticket.ticket_number}</code>\n👤 <code>{message.from_user.id}</code>\n💬 {escape(message.text)}", ticket.ticket_number)
    await message.answer(f"✅ درخواست ثبت شد.\n🧾 <code>{ticket.ticket_number}</code>")


@router.callback_query(F.data == "support:my")
async def my_tickets(callback: CallbackQuery):
    async with async_session() as session: tickets = await get_customer_tickets(session, callback.from_user.id)
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📂 <b>تیکت‌های شما</b>", reply_markup=customer_tickets_keyboard(tickets) if tickets else support_menu_keyboard())


@router.callback_query(F.data.startswith("support:ticket:"))
async def customer_details(callback: CallbackQuery):
    number = callback.data.split(":")[-1]
    async with async_session() as session:
        try: ticket = await get_customer_ticket(session, number, callback.from_user.id); messages = await get_ticket_messages(session, number)
        except TicketNotFoundError: await callback.answer("تیکت پیدا نشد.", show_alert=True); return
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(history(ticket, messages), reply_markup=customer_ticket_keyboard(ticket))


@router.callback_query(F.data.startswith("support:reply:"))
async def customer_reply_request(callback: CallbackQuery, state: FSMContext):
    number = callback.data.split(":")[-1]
    async with async_session() as session:
        try: ticket = await get_customer_ticket(session, number, callback.from_user.id)
        except TicketNotFoundError: await callback.answer("تیکت پیدا نشد.", show_alert=True); return
    if ticket.status == "closed": await callback.answer("این تیکت بسته شده است.", show_alert=True); return
    await state.update_data(ticket_number=number); await state.set_state(SupportStates.waiting_customer_reply); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("💬 پیام خود را ارسال کنید. برای انصراف /cancel")


@router.message(SupportStates.waiting_customer_reply)
async def customer_reply(message: Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); await message.answer("ارسال پیام لغو شد."); return
    data = payload(message)
    if not data: await message.answer("متن، عکس یا فایل ارسال کنید."); return
    try:
        async with async_session() as session: await add_message(session, data and (await state.get_data()).get("ticket_number"), message.from_user.id, "customer", **data)
    except (TicketNotFoundError, TicketClosedError, TicketAccessError): await state.clear(); await message.answer("امکان ارسال پیام وجود ندارد."); return
    await state.clear(); await message.answer("✅ پیام شما ارسال شد.")


@router.callback_query(F.data.startswith("support:close:"))
async def customer_close(callback: CallbackQuery):
    number = callback.data.split(":")[-1]
    async with async_session() as session:
        try: await get_customer_ticket(session, number, callback.from_user.id); ticket = await close_ticket(session, number)
        except (TicketNotFoundError, TicketClosedError): await callback.answer("امکان بستن تیکت وجود ندارد.", show_alert=True); return
    await callback.answer("تیکت بسته شد."); await callback.message.edit_text("🔒 تیکت بسته شد.", reply_markup=customer_ticket_keyboard(ticket))


@router.callback_query(F.data.startswith("support:reopen:"))
async def customer_reopen(callback: CallbackQuery):
    number = callback.data.split(":")[-1]
    async with async_session() as session:
        try: await get_customer_ticket(session, number, callback.from_user.id); ticket = await reopen_ticket(session, number)
        except (TicketNotFoundError, ValueError): await callback.answer("امکان بازگشایی تیکت وجود ندارد.", show_alert=True); return
    await callback.answer("تیکت باز شد."); await callback.message.edit_text("🔄 تیکت بازگشایی شد.", reply_markup=customer_ticket_keyboard(ticket))


@router.callback_query(F.data == "support:admin:menu")
async def admin_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await callback.answer();
    if isinstance(callback.message, Message): await callback.message.edit_text("👨‍💻 <b>مدیریت پشتیبانی NR SHOP</b>", reply_markup=admin_support_keyboard())


@router.callback_query(F.data.in_({"support:admin:new", "support:admin:active", "support:admin:all"}))
async def admin_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    action = callback.data.split(":")[-1]
    async with async_session() as session:
        tickets = await get_admin_tickets(session) if action != "all" else await get_customer_tickets(session, callback.from_user.id)
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📂 <b>فهرست تیکت‌ها</b>", reply_markup=admin_tickets_keyboard(tickets))


@router.callback_query(F.data.startswith("support:admin:ticket:"))
async def admin_details(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    number = callback.data.split(":")[-1]
    async with async_session() as session:
        try: ticket = await get_ticket(session, number); messages = await get_ticket_messages(session, number)
        except TicketNotFoundError: await callback.answer("تیکت پیدا نشد.", show_alert=True); return
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(history(ticket, messages), reply_markup=admin_ticket_keyboard(ticket))


@router.callback_query(F.data.startswith("support:admin:reply:"))
async def admin_reply_request(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    number = callback.data.split(":")[-1]
    async with async_session() as session:
        try: ticket = await get_ticket(session, number)
        except TicketNotFoundError: await callback.answer("تیکت پیدا نشد.", show_alert=True); return
    if ticket.status == "closed":
        await callback.answer("تیکت بسته شده است.", show_alert=True); return
    await state.update_data(ticket_number=number); await state.set_state(SupportStates.waiting_admin_reply); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("💬 پاسخ خود را ارسال کنید. برای انصراف /cancel")


@router.message(SupportStates.waiting_admin_reply)
async def admin_reply(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    if message.text == "/cancel": await state.clear(); await message.answer("پاسخ لغو شد."); return
    data = payload(message)
    if not data: await message.answer("متن، عکس یا فایل ارسال کنید."); return
    number = (await state.get_data()).get("ticket_number")
    try:
        async with async_session() as session:
            ticket = await get_ticket(session, number)
            await add_message(session, number, message.from_user.id, "admin", **data)
    except (TicketNotFoundError, TicketClosedError): await state.clear(); await message.answer("تیکت پیدا نشد یا بسته شده است."); return
    try:
        await message.bot.send_message(ticket.telegram_user_id, f"📨 <b>پاسخ پشتیبانی</b>\n\n🧾 تیکت: <code>{number}</code>", parse_mode="HTML")
        await message.bot.copy_message(ticket.telegram_user_id, message.chat.id, message.message_id)
    except Exception: logger.exception("Support reply delivery failed")
    await state.clear(); await message.answer("✅ پاسخ برای مشتری ارسال شد.")


@router.callback_query(F.data.startswith("support:admin:close:"))
async def admin_close(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    number = callback.data.split(":")[-1]
    async with async_session() as session:
        try: ticket = await close_ticket(session, number)
        except (TicketNotFoundError, TicketClosedError): await callback.answer("تیکت قبلاً بسته شده است.", show_alert=True); return
    await callback.answer("تیکت بسته شد.")
    await callback.bot.send_message(ticket.telegram_user_id, f"🔒 تیکت <code>{number}</code> توسط پشتیبانی بسته شد.", parse_mode="HTML")
