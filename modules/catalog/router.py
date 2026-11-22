from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from core.features import is_feature_enabled

from .keyboards import product_detail_keyboard
from .service import get_product


router = Router(name="catalog")


@router.callback_query(F.data.startswith("catalog:product:"))
async def product_detail(callback: CallbackQuery):
    product_id = callback.data.removeprefix("catalog:product:")
    product = get_product(product_id)

    if not product or not product.enabled:
        await callback.answer("❌ این محصول در دسترس نیست.", show_alert=True)
        return

    if not is_feature_enabled(product.category):
        await callback.answer("🔴 این دسته‌بندی غیرفعال شده است.", show_alert=True)
        return

    stock_text = f"✅ موجودی: {product.stock}" if product.stock > 0 else "❌ ناموجود"
    text = f"""
🛍 <b>{escape(product.title)}</b>

📝 توضیحات:
{escape(product.description)}

💰 قیمت:
{product.price:,} تومان

📦 {stock_text}

━━━━━━━━━━━━━━
<b>NR SHOP</b>
"""

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text,
            reply_markup=product_detail_keyboard(product.category),
        )
