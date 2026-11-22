from core.admin_settings import content_prefix
from html import escape

from core.features import is_feature_enabled


SERVICE_FEATURES = [
    "ai",
    "vpn",
    "telegram",
    "vps",
]


def get_active_services_count():

    return sum(
        is_feature_enabled(feature)
        for feature in SERVICE_FEATURES
    )


def build_welcome_message(full_name: str):

    name = escape(full_name or "دوست عزیز")

    active_count = get_active_services_count()

    return content_prefix("texts:welcome") + f"""
💠 سلام <b>{name}</b> عزیز

به ربات <b>NR SHOP</b> خوش آمدید.

🛡️ سرویس فعال: <b>{active_count}</b> عدد

✨ با ما تجربه خرید متفاوتی داشته باشید.
    """


JOIN_MESSAGE = """
1️⃣ لطفا با استفاده از گزینه
(عضویت در کانال NR SHOP👑)
در کانال ما عضو بشید ✔️

2️⃣ بعد با استفاده از گزینه
(تایید عضویت ✅)
عضویت خودتون رو تایید کنید 🙏
"""
