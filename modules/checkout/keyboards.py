from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def order_summary_keyboard(order_number: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 کد تخفیف دارم", callback_data=f"checkout:coupon:{order_number}")],
        [InlineKeyboardButton(text="ادامه بدون کد تخفیف ➡️", callback_data=f"checkout:skip:{order_number}")],
        [InlineKeyboardButton(text="❌ لغو سفارش", callback_data=f"checkout:cancel:{order_number}")],
    ])


def checkout_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 بازگشت به فروشگاه", callback_data="shop:home")
    ]])


def checkout_payment_keyboard(order_number: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 مشاهده اطلاعات پرداخت",
            callback_data=f"checkout:pay:{order_number}",
        )],
        [InlineKeyboardButton(
            text="❌ لغو سفارش",
            callback_data=f"checkout:cancel:{order_number}",
        )],
    ])


def payment_back_keyboard(order_number: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔙 بازگشت به خلاصه سفارش",
            callback_data=f"checkout:summary:{order_number}",
        )],
        [InlineKeyboardButton(
            text="❌ لغو سفارش",
            callback_data=f"checkout:cancel:{order_number}",
        )],
    ])


def payment_receipt_keyboard(order_number: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📸 ارسال رسید پرداخت",
            callback_data=f"checkout:receipt:{order_number}",
        )],
        [InlineKeyboardButton(
            text="🔙 بازگشت به خلاصه سفارش",
            callback_data=f"checkout:summary:{order_number}",
        )],
    ])


def receipt_request_keyboard(order_number: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔙 بازگشت به پرداخت",
            callback_data=f"checkout:pay:{order_number}",
        )],
        [InlineKeyboardButton(
            text="❌ لغو ارسال رسید",
            callback_data=f"checkout:summary:{order_number}",
        )],
    ])
