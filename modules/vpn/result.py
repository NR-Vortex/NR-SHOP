from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def vpn_result_keyboard(order_number: str, ready: bool):
    buttons = []
    if ready:
        buttons.extend([
            [InlineKeyboardButton(text="🔗 دریافت مجدد لینک", callback_data=f"vpn:link:{order_number}")],
            [InlineKeyboardButton(text="📷 دریافت QR Code", callback_data=f"vpn:qr:{order_number}")],
        ])
    buttons.extend([
        [InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="support:menu:vpn")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی VPN", callback_data="vpn:home")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_vpn_approved_text(order, detail):
    ready = detail.provisioning_status == "delivered" and bool(detail.subscription_url)
    if not ready:
        return (
            "🎉 <b>پرداخت شما با موفقیت تأیید شد!</b>\n\n"
            "💎 سفارش شما تأیید شده و سرویس VPN در حال آماده‌سازی است.\n\n"
            f"👤 نام کاربری: {escape(detail.username)}\n"
            f"🌐 سرور: {escape(detail.server_name)}\n\n"
            "لینک و QR پس از تکمیل ساخت سرویس در دسترس قرار می‌گیرد."
        ), False
    return (
        "🎉 <b>پرداخت شما با موفقیت تأیید شد!</b>\n\n"
        "💎 سفارش شما تأیید شده و سرویس VPN آماده تحویل است.\n\n"
        f"🧾 شماره سفارش: <code>{order.order_number}</code>\n"
        f"👤 نام کاربری: {escape(detail.username)}\n"
        f"🌐 سرور: {escape(detail.server_name)}\n"
        f"📆 مدت اعتبار: {order.duration_days or 'ثبت نشده'} روز\n\n"
        f"🔗 لینک اشتراک:\n{escape(detail.subscription_url)}\n\n"
        "📷 QR Code سرویس شما در تصویر زیر قرار دارد.\n\n"
        "از خرید شما سپاسگزاریم ❤️"
    ), True


def build_vpn_rejected_text(order, detail):
    return (
        "❌ <b>درخواست شما رد شد.</b>\n\n"
        "متأسفانه پرداخت سفارش شما توسط مدیریت تأیید نشد.\n\n"
        f"🧾 شماره سفارش: <code>{order.order_number}</code>\n"
        f"👤 نام کاربری: {escape(detail.username)}\n\n"
        "برای پیگیری بیشتر با پشتیبانی NR SHOP تماس بگیرید."
    )
