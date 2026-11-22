import os
from urllib.parse import urljoin
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def admin_dashboard_keyboard():
    rows = [
        (("👥 کاربران", "admin:section:users"), ("📊 گزارش‌ها", "admin:section:reports")),
        (("🤖 بخش AI", "admin:section:ai"), ("🌐 بخش VPN", "admin:vpn")),
        (("👑 پنل نمایندگی", "admin:section:agency_panel"), ("🤖 ربات نمایندگی", "admin:section:agency_bot")),
        (("💰 بخش مالی", "admin:section:finance"), ("🎧 پشتیبانی", "support:admin:menu")),
        (("🎁 هدایا", "admin:section:gifts"), ("📚 راهنما", "admin:section:guides")),
        (("📢 پیام همگانی", "admin:section:broadcast"), ("📝 مدیریت متن‌ها", "admin:section:texts")),
        (("🏢 مدیریت نمایندگان", "admin:section:representatives"), ("🗄 دیتابیس", "admin:section:database")),
        (("📣 تبلیغات", "admin:section:ads"), ("⚙️ تنظیمات ربات", "admin:section:settings")),
        (("🔙 بازگشت به منوی اصلی", "shop:home"),),
    ]
    keyboard = [[InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows]
    url = os.getenv("MINIAPP_URL","").strip()
    if url.startswith("https://"):
        keyboard.insert(0,[InlineKeyboardButton(text="پنل مدیریت مینی‌اپ",web_app=WebAppInfo(url=urljoin(url,"admin.html")))])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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
