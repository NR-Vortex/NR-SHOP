from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def trial_customer_keyboard(enabled: bool, claimed: bool = False):
    buttons = []
    if enabled and not claimed: buttons.append([InlineKeyboardButton(text="🎁 دریافت اکانت تست", callback_data="vpn:trial:claim")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به منوی VPN", callback_data="vpn:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trial_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ تنظیمات اکانت تست", callback_data="vpnadmin:trial:settings")],
        [InlineKeyboardButton(text="🌐 انتخاب پنل", callback_data="vpnadmin:trial:panel")],
        [InlineKeyboardButton(text="📡 انتخاب Inbound", callback_data="vpnadmin:trial:inbound")],
        [InlineKeyboardButton(text="🔴/🟢 فعال / غیرفعال", callback_data="vpnadmin:trial:toggle")],
        [InlineKeyboardButton(text="📊 آمار دریافت‌کنندگان", callback_data="vpnadmin:trial:stats")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="vpnadmin:menu")],
    ])
