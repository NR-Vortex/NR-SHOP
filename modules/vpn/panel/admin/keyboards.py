from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def panel_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ اتصال پنل جدید 3X-UI", callback_data="vpnadmin:add")],
        [InlineKeyboardButton(text="📡 پنل‌های متصل", callback_data="vpnadmin:list")],
        [InlineKeyboardButton(text="🌐 مدیریت Inbound ها", callback_data="vpnadmin:inbounds")],
        [InlineKeyboardButton(text="📦 اتصال Inbound به محصولات", callback_data="vpnadmin:product_links")],
        [InlineKeyboardButton(text="🕹️ مدیریت اکانت تست", callback_data="vpnadmin:trial")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="shop:home")],
    ])
