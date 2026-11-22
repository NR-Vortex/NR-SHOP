import os
from core.button_theme import layout_keyboard
from urllib.parse import urljoin
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


ADMIN_GROUPS = {
    "shop": ("کاتالوگ و فروش", [
        (("هوش مصنوعی", "admin:section:ai"), ("سرویس VPN", "admin:vpn")),
        (("تخفیف و هدیه", "admin:section:gifts"), ("گزارش‌ها", "admin:section:reports")),
    ]),
    "agency": ("نمایندگی", [
        (("مدیریت نمایندگان", "admin:section:representatives"),),
        (("پنل نمایندگی", "admin:section:agency_panel"), ("ربات نمایندگی", "admin:section:agency_bot")),
    ]),
    "content": ("محتوا و ارتباطات", [
        (("پیام همگانی", "admin:section:broadcast"), ("تبلیغات و عضویت", "admin:section:ads")),
        (("متن‌های ربات", "admin:section:texts"), ("راهنماها", "admin:section:guides")),
    ]),
    "system": ("تنظیمات و نگهداری", [
        (("تنظیمات ربات", "admin:section:settings"), ("دیتابیس و بکاپ", "admin:section:database")),
        (("به‌روزرسانی", "updates:menu"),),
    ]),
}


def admin_buttons(rows):
    return [[InlineKeyboardButton(text=label, callback_data=action) for label,action in row] for row in rows]


def admin_dashboard_keyboard():
    keyboard = admin_buttons([
        (("💳 رسیدهای پرداخت", "admin:finance:payments"), ("📊 گزارش فروش", "admin:reports:sales")),
        (("👥 کاربران", "admin:section:users"), ("🎧 پشتیبانی", "support:admin:menu")),
        (("💰 امور مالی", "admin:section:finance"), ("🛍 کاتالوگ و فروش", "admin:hub:shop")),
        (("🏢 نمایندگی", "admin:hub:agency"), ("📣 محتوا و ارتباطات", "admin:hub:content")),
        (("⚙️ تنظیمات و نگهداری", "admin:hub:system"),),
        (("↩️ بازگشت به فروشگاه", "shop:home"),),
    ])
    keyboard = layout_keyboard(keyboard)
    url = os.getenv("MINIAPP_URL","").strip()
    if url.startswith("https://"):
        keyboard.insert(0,[InlineKeyboardButton(text="🖥 باز کردن مینی‌اپ مدیریت",web_app=WebAppInfo(url=urljoin(url,"admin.html")))])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_group_keyboard(group):
    _, rows = ADMIN_GROUPS[group]
    return InlineKeyboardMarkup(inline_keyboard=layout_keyboard(admin_buttons([*rows, (("↩️ داشبورد مدیریت", "admin:dashboard"),)])))


def admin_users_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 جستجوی کاربر", callback_data="admin:users:search")],
        [InlineKeyboardButton(text="👤 لیست کاربران", callback_data="admin:users:list")],
        [InlineKeyboardButton(text="📊 آمار کاربران", callback_data="admin:users:stats")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_reports_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 گزارش فروش", callback_data="admin:reports:sales")],
        [InlineKeyboardButton(text="👥 گزارش کاربران", callback_data="admin:reports:users")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_ai_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 دسته‌بندی‌ها", callback_data="admin:ai:categories")],
        [InlineKeyboardButton(text="🗂 گروه محصولات", callback_data="admin:ai:groups")],
        [InlineKeyboardButton(text="📦 محصولات", callback_data="admin:ai:products")],
        [InlineKeyboardButton(text="🧾 سفارش‌های AI", callback_data="admin:ai:orders")],
        [InlineKeyboardButton(text="🎁 اکانت‌ها و فعال‌سازی", callback_data="admin:ai:accounts")],
        [InlineKeyboardButton(text="📚 آموزش محصولات", callback_data="admin:ai:tutorials")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_finance_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 پرداخت‌ها و رسیدها", callback_data="admin:finance:payments")],
        [InlineKeyboardButton(text="🪙 کیف پول‌ها", callback_data="admin:finance:wallets")],
        [InlineKeyboardButton(text="📜 تراکنش‌ها", callback_data="admin:finance:transactions")],
        [InlineKeyboardButton(text="💰 گزارش درآمد", callback_data="admin:reports:sales")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_gifts_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 کدهای تخفیف", callback_data="admin:gifts:coupons")],
        [InlineKeyboardButton(text="👥 آمار Referral", callback_data="admin:gifts:referral")],
        [InlineKeyboardButton(text="🎁 کد هدیه", callback_data="admin:gifts:gift")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_database_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🩺 سلامت اتصال", callback_data="admin:database:health")],
        [InlineKeyboardButton(text="📊 آمار جداول", callback_data="admin:database:stats")],
        [InlineKeyboardButton(text="💾 بکاپ دستی", callback_data="admin:database:backup")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_settings_keyboard():
    from core.features import is_feature_enabled
    labels = {"ai": "هوش مصنوعی", "vpn": "VPN", "telegram": "تلگرام", "vps": "نمایندگی", "support": "پشتیبانی", "orders": "سفارش‌ها"}
    rows = []
    for key, label in labels.items():
        status = "فعال" if is_feature_enabled(key) else "غیرفعال"
        rows.append([InlineKeyboardButton(text=f"{label} — {status}", callback_data=f"admin:settings:feature:{key}")])
    rows.append([InlineKeyboardButton(text="سرور فروش نمایندگی", callback_data="admin:agency:server")])
    rows.append([InlineKeyboardButton(text="تعرفه حجم نمایندگی", callback_data="admin:agency:price")])
    url = os.getenv("MINIAPP_URL","").strip()
    if url.startswith("https://"):
        rows.append([InlineKeyboardButton(text="🎨 چیدمان و رنگ دکمه‌ها",
            web_app=WebAppInfo(url=urljoin(url,"admin.html?view=appearance")))])

    rows.append([InlineKeyboardButton(text="بازگشت", callback_data="admin:dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_broadcast_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 ارسال پیام متنی", callback_data="admin:broadcast:text")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_guides_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 آموزش‌های AI", callback_data="admin:guides:ai")],
        [InlineKeyboardButton(text="🌐 آموزش‌های VPN", callback_data="admin:guides:vpn")],
        [InlineKeyboardButton(text="➕ افزودن آموزش", callback_data="admin:guides:add")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])

def admin_texts_keyboard():
    keys = [("👋 خوشامدگویی", "welcome"), ("🤖 منوی AI", "ai_menu"), ("🌐 منوی VPN", "vpn_menu"), ("🧾 پیش‌فاکتور", "invoice"), ("💳 پرداخت", "payment"), ("🎧 پشتیبانی", "support")]
    rows = [[InlineKeyboardButton(text=t, callback_data=f"admin:texts:{k}")] for t, k in keys]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_ads_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 کانال‌های عضویت اجباری", callback_data="admin:ads:channels")],
        [InlineKeyboardButton(text="🟢 وضعیت عضویت اجباری", callback_data="admin:ads:force_join")],
        [InlineKeyboardButton(text="📢 تبلیغات", callback_data="admin:ads:campaigns")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:dashboard")],
    ])
