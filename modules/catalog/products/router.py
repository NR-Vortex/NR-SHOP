from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from core.features import is_feature_enabled
from database.session import async_session
from modules.catalog.categories.service import CategoryNotFoundError, get_category
from modules.catalog.groups.service import (
    ProductGroupNotFoundError,
    get_product_group,
)
from modules.catalog.products.keyboards import product_detail_keyboard
from modules.catalog.products.service import ProductNotFoundError, get_product


router = Router(name="catalog_products")


@router.callback_query(F.data.startswith("catalog:group:"))
async def group_heading_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:product:"))
async def product_detail_handler(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split(":")[-1])
    except (TypeError, ValueError):
        await callback.answer("محصول نامعتبر است.", show_alert=True)
        return

    async with async_session() as session:
        try:
            product = await get_product(session, product_id)
        except ProductNotFoundError:
            await callback.answer("این محصول وجود ندارد.", show_alert=True)
            return

        if not product.is_active:
            await callback.answer("این محصول غیرفعال است.", show_alert=True)
            return

        try:
            category = await get_category(session, product.category_id)
        except CategoryNotFoundError:
            await callback.answer("دسته‌بندی محصول پیدا نشد.", show_alert=True)
            return

        if not category.is_active or not is_feature_enabled(category.section):
            await callback.answer("این محصول فعلاً در دسترس نیست.", show_alert=True)
            return

        if product.group_id is None:
            await callback.answer("این محصول گروه‌بندی نشده است.", show_alert=True)
            return

        try:
            group = await get_product_group(session, product.group_id)
        except ProductGroupNotFoundError:
            await callback.answer("گروه محصول پیدا نشد.", show_alert=True)
            return

        if not group.is_active:
            await callback.answer("گروه این محصول غیرفعال است.", show_alert=True)
            return

        name = escape(product.name)
        description = (
            escape(product.description)
            if product.description
            else "توضیحاتی برای این محصول ثبت نشده است."
        )
        price = product.price
        category_id = category.id

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        f"""
🛍 <b>{name}</b>

📝 <b>توضیحات محصول:</b>

{description}

━━━━━━━━━━━━━━

💰 <b>قیمت:</b> {price:,} تومان

━━━━━━━━━━━━━━

👑 <b>NR SHOP</b>
""",
        reply_markup=product_detail_keyboard(
            category_id=category_id,
            product_id=product.id,
        ),
    )
