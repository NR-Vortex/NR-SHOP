from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def support_menu_keyboard(section="general"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 ثبت درخواست جدید", callback_data=f"support:new:{section}")],
        [InlineKeyboardButton(text="📂 تیکت‌های من", callback_data="support:my")],
        [InlineKeyboardButton(text="🔙 بازگشت به فروشگاه", callback_data="shop:home")],
    ])


def customer_tickets_keyboard(tickets):
    icons = {"open": "🟢", "waiting_admin": "🟡", "waiting_user": "🔵", "closed": "🔴"}
    buttons = [[InlineKeyboardButton(text=f"{icons.get(t.status, '⚪')} {t.ticket_number}", callback_data=f"support:ticket:{t.ticket_number}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="support:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def customer_ticket_keyboard(ticket):
    buttons = []
    if ticket.status == "closed":
        buttons.append([InlineKeyboardButton(text="🔄 بازگشایی تیکت", callback_data=f"support:reopen:{ticket.ticket_number}")])
    else:
        buttons.extend([
            [InlineKeyboardButton(text="💬 ارسال پیام", callback_data=f"support:reply:{ticket.ticket_number}")],
            [InlineKeyboardButton(text="🔒 بستن تیکت", callback_data=f"support:close:{ticket.ticket_number}")],
        ])
    buttons.append([InlineKeyboardButton(text="🔙 تیکت‌های من", callback_data="support:my")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_support_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 تیکت‌های جدید", callback_data="support:admin:new")],
        [InlineKeyboardButton(text="💬 تیکت‌های فعال", callback_data="support:admin:active")],
        [InlineKeyboardButton(text="📂 همه تیکت‌ها", callback_data="support:admin:all")],
    ])


def admin_tickets_keyboard(tickets):
    icons = {"open": "🟢", "waiting_admin": "🟡", "waiting_user": "🔵", "closed": "🔴"}
    buttons = [[InlineKeyboardButton(text=f"{icons.get(t.status, '⚪')} {t.ticket_number}", callback_data=f"support:admin:ticket:{t.ticket_number}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="🔙 منوی پشتیبانی", callback_data="support:admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_ticket_keyboard(ticket):
    buttons = []
    if ticket.status != "closed":
        buttons.extend([
            [InlineKeyboardButton(text="💬 پاسخ به مشتری", callback_data=f"support:admin:reply:{ticket.ticket_number}")],
            [InlineKeyboardButton(text="🔒 بستن تیکت", callback_data=f"support:admin:close:{ticket.ticket_number}")],
        ])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="support:admin:active")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
