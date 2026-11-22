from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .data import Product


def products_keyboard(category: str, products: list[Product]) -> InlineKeyboardMarkup:
    buttons = []
    for product in products:
        price_text = f"{product.price:,} تومان" if product.stock > 0 else "ناموجود"
        buttons.append([
            InlineKeyboardButton(
                text=f"🛍 {product.title} | {price_text}",
                callback_data=f"catalog:product:{product.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="shop:home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_keyboard(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔙 بازگشت به محصولات",
            callback_data=f"shop:category:{category}",
        )
    ]])
