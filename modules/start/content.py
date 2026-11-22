from html import escape
from core.admin_settings import content_prefix


def build_welcome_message(full_name: str):
    name = escape(full_name or 'همراه NR SHOP')
    return content_prefix('texts:welcome') + (
        f'سلام <b>{name}</b>، به <b>NR SHOP</b> خوش اومدی.\n\n'
        'از منوی پایین سرویس‌ت رو انتخاب کن یا سفارش‌هات رو پیگیری کن.'
    )


JOIN_MESSAGE = (
    'برای ورود به فروشگاه، در کانال‌های زیر عضو شو.\n\n'
    'بعد «بررسی عضویت» رو بزن تا وارد فروشگاه بشی.'
)
