from core.admin_settings import content_prefix
from html import escape

import os
from dotenv import dotenv_values


def get_payment_settings():
    values = {**dotenv_values(".env"), **os.environ}
    return {
        "bank_name": values.get("PAYMENT_BANK_NAME", "") or "",
        "card_number": values.get("PAYMENT_CARD_NUMBER", "") or "",
        "cardholder": values.get("PAYMENT_CARDHOLDER", "") or "",
        "description": values.get(
            "PAYMENT_DESCRIPTION",
            "بعد از واریز، «ارسال رسید» رو بزن و عکس یا PDF رسید رو بفرست.",
        ) or "",
    }


def payment_is_configured():
    settings = get_payment_settings()
    return all(settings[key].strip() for key in ("bank_name", "card_number", "cardholder"))


def build_payment_text(order):
    settings = get_payment_settings()
    return content_prefix("texts:payment") + f"""
💳 <b>پرداخت سفارش</b>

━━━━━━━━━━━━━━━━━━

🏦 <b>بانک:</b>
{escape(settings['bank_name'])}

💳 <b>شماره کارت:</b>
<code>{escape(settings['card_number'])}</code>

👤 <b>صاحب حساب:</b>
{escape(settings['cardholder'])}

━━━━━━━━━━━━━━━━━━

📦 <b>محصول:</b>
{escape(order.product_name)}

🧾 <b>شماره سفارش:</b>
<code>{escape(order.order_number)}</code>

💰 <b>مبلغ قابل پرداخت:</b>
<b>{order.final_amount:,} تومان</b>

━━━━━━━━━━━━━━━━━━

📌 {escape(settings['description'])}

👑 <b>NR SHOP</b>
"""
