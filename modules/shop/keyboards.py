import os
from core.button_theme import layout_keyboard
from urllib.parse import urljoin
from aiogram.types import (
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from core.features import is_feature_enabled


CATEGORIES = {
    "ai": "🧠 هوش مصنوعی",
    "vpn": "🌐 سرویس VPN",
    "telegram": "✈️ امکانات تلگرام",
    "vps": "🤖 ربات نمایندگی",
}


def main_menu_keyboard():

    buttons = []

    url = os.getenv('MINIAPP_URL', '').strip()
    if url.startswith('https://'):
        buttons.append([InlineKeyboardButton(text='🛍 ورود به فروشگاه', web_app=WebAppInfo(url=urljoin(url,'shop.html')))])
        if is_feature_enabled('vps'):
            buttons.append([InlineKeyboardButton(text='داشبورد نمایندگی', web_app=WebAppInfo(url=url))])

    # دسته بندی های فروشگاه
    for key, title in CATEGORIES.items():

        if is_feature_enabled(key):

            buttons.append([
                InlineKeyboardButton(
                    text=title,
                    callback_data="agency:bot" if key == "vps" else f"shop:category:{key}"
                )
            ])

    # سفارش های من
    if is_feature_enabled("orders"):
        buttons.append([InlineKeyboardButton(text="📦 محصولات من", callback_data="shop:orders")])

    if is_feature_enabled("vps"):

        buttons.append([
            InlineKeyboardButton(
                text="👑 پنل نمایندگی",
                callback_data="agency:panel"
            )
        ])

    # پشتیبانی
    if is_feature_enabled("support"):

        buttons.append([
            InlineKeyboardButton(
                text="🎧 پشتیبانی",
                callback_data="support:menu"
            )
        ])

    return InlineKeyboardMarkup(
        inline_keyboard=layout_keyboard(buttons,pack_tiles=True)
    )


def back_to_shop_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به فروشگاه",
                    callback_data="shop:home"
                )
            ]
        ]
    )


def ai_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="ai:buy")],
        [
            InlineKeyboardButton(text="📦 سفارش‌های من", callback_data="shop:orders"),
            InlineKeyboardButton(text="🛡️ سرویس‌های من", callback_data="ai:services"),
        ],
        [
            InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="shop:support"),
            InlineKeyboardButton(text="💳 کیف پول", callback_data="ai:wallet"),
        ],
        [InlineKeyboardButton(text="👥 دعوت دوستان و اعتبار", callback_data="ai:referral")],
        [
            InlineKeyboardButton(text="📑 راهنما", callback_data="ai:help"),
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="shop:home"),
        ],
    ])


def back_to_ai_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔙 بازگشت به منوی هوش مصنوعی",
            callback_data="ai:home",
        )
    ]])


def ai_services_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="ChatGPT",
                callback_data="ai:service:chatgpt",
            ),
            InlineKeyboardButton(
                text="Gemini",
                callback_data="ai:service:gemini",
            ),
        ],
        [InlineKeyboardButton(
            text="Super Grok",
            callback_data="ai:service:grok",
        )],
        [InlineKeyboardButton(
            text="Cursor",
            callback_data="ai:service:cursor",
        )],
        [InlineKeyboardButton(
            text="منوی اصلی",
            callback_data="shop:home",
        )],
    ])


def orders_keyboard(orders, page=0, has_next=False):
    status_icons = {
        "awaiting_payment": "🟡",
        "awaiting_discount": "🟡",
        "under_review": "🔵",
        "provisioning": "🟠",
        "paid": "🟢",
        "rejected": "🔴",
        "cancelled": "⚫",
    }
    rows = []
    for order, section in orders:
        icon = status_icons.get(order.status, "⚪")
        rows.append([InlineKeyboardButton(
            text=f"{icon} {section} · {order.product_name[:52]} · {order.final_amount:,} تومان",
            callback_data=f"shop:order:{order.id}:{page}",
        )])
    navigation = []
    if page:
        navigation.append(InlineKeyboardButton(text="قبلی", callback_data=f"shop:orders:{page-1}"))
    if has_next:
        navigation.append(InlineKeyboardButton(text="بعدی", callback_data=f"shop:orders:{page+1}"))
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(text="بازگشت به فروشگاه", callback_data="shop:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_detail_keyboard(order, section, page, *, is_vpn=False):
    rows = []
    if order.status == "awaiting_discount":
        rows.append([InlineKeyboardButton(text="ادامهٔ پرداخت", callback_data=f"checkout:skip:{order.order_number}")])
    elif order.status == "awaiting_payment":
        rows.append([InlineKeyboardButton(text="مشاهدهٔ اطلاعات پرداخت", callback_data=f"checkout:pay:{order.order_number}")])
    elif order.status in {"paid","provisioning"} and is_vpn:
        rows.append([InlineKeyboardButton(text="مشاهدهٔ سرویس VPN", callback_data=f"vpn:service:{order.id}")])
    elif order.status == "paid" and section == "ai":
        rows.append([InlineKeyboardButton(text="دریافت اطلاعات حساب", callback_data=f"ai:account:{order.id}")])
    rows.append([InlineKeyboardButton(text="پشتیبانی", callback_data="support:menu")])
    rows.append([InlineKeyboardButton(text="بازگشت به محصولات من", callback_data=f"shop:orders:{page}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ai_account_delivery_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 دریافت مجدد اطلاعات حساب", callback_data=f"ai:account:{order_id}")],
        [InlineKeyboardButton(text="📚 آموزش استفاده", callback_data="ai:help")],
        [InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="shop:support")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی AI", callback_data="ai:home")],
    ])


def ai_shared_account_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 دریافت کد ورود و 2FA", callback_data=f"ai:code:{order_id}")],
        [InlineKeyboardButton(text="📚 آموزش ورود", callback_data="ai:help")],
        [InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="shop:support")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="ai:home")],
    ])


def ai_tutorials_keyboard(products):
    rows = [[InlineKeyboardButton(
        text=f"📚 {product.name}",
        callback_data=f"ai:tutorial:{product.id}",
    )] for product in products]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت به منوی هوش مصنوعی", callback_data="ai:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ai_tutorial_detail_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به آموزش‌ها", callback_data="ai:help")],
        [InlineKeyboardButton(text="🏠 منوی هوش مصنوعی", callback_data="ai:home")],
    ])


def ai_wallet_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 افزایش اعتبار", callback_data="ai:wallet:topup")],
        [InlineKeyboardButton(text="📜 تاریخچه تراکنش‌ها", callback_data="ai:wallet:history")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی هوش مصنوعی", callback_data="ai:home")],
    ])


def ai_services_keyboard(orders):
    icons = {"provisioning": "🔵", "paid": "🟢", "rejected": "🔴", "cancelled": "⚫"}
    rows = []
    for order, delivery in orders:
        icon = icons.get(order.status, "🟡")
        kind = "اختصاصی" if delivery and delivery.account_type == "dedicated" else "اشتراکی"
        rows.append([InlineKeyboardButton(text=f"{icon} {order.product_name} | {kind}", callback_data=f"ai:service:{order.id}")])
    rows.append([InlineKeyboardButton(text="🏠 بازگشت به منوی هوش مصنوعی", callback_data="ai:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ai_service_detail_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📧 مشاهده اطلاعات حساب", callback_data=f"ai:account:{order_id}")],
        [InlineKeyboardButton(text="📚 آموزش استفاده", callback_data="ai:help")],
        [InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="shop:support")],
        [InlineKeyboardButton(text="🔙 بازگشت به سرویس‌های من", callback_data="ai:services")],
    ])
