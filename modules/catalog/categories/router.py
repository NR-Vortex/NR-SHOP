from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from database.session import async_session

from modules.catalog.categories.service import (
    get_category,
    CategoryNotFoundError
)

from modules.catalog.groups.service import (
    get_product_groups
)

from modules.catalog.products.service import (
    get_products
)

from modules.catalog.products.keyboards import (
    grouped_products_keyboard
)

from core.features import is_feature_enabled


router = Router(name="catalog_categories")


@router.callback_query(
    F.data.startswith("catalog:category:")
)
async def category_handler(callback: CallbackQuery):

    try:

        category_id = int(
            callback.data.split(":")[-1]
        )

    except ValueError:

        await callback.answer(
            "دسته‌بندی نامعتبر است.",
            show_alert=True
        )

        return

    async with async_session() as session:

        try:

            category = await get_category(
                session,
                category_id
            )

        except CategoryNotFoundError:

            await callback.answer(
                "دسته‌بندی پیدا نشد.",
                show_alert=True
            )

            return

        if not category.is_active:

            await callback.answer(
                "این دسته‌بندی غیرفعال است.",
                show_alert=True
            )

            return

        if not is_feature_enabled(category.section):

            await callback.answer(
                "این بخش فروشگاه غیرفعال است.",
                show_alert=True
            )

            return

        # دریافت گروه‌های فعال
        groups = await get_product_groups(
            session=session,
            category_id=category.id,
            active_only=True
        )

        # دریافت محصولات فعال
        products = await get_products(
            session=session,
            category_id=category.id,
            active_only=True
        )

        # گروه‌بندی محصولات
        products_by_group = {}

        for product in products:

            if product.group_id is None:
                continue

            products_by_group.setdefault(
                product.group_id,
                []
            ).append(product)

        # فقط گروه‌های دارای محصول
        visible_groups = [
            group
            for group in groups
            if products_by_group.get(group.id)
        ]

        category_name = escape(category.name)

    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    if not visible_groups:

        await callback.message.edit_text(
            f"""
📂 <b>{category_name}</b>

📦 در حال حاضر محصول فعالی برای نمایش وجود ندارد.
""",
            reply_markup=grouped_products_keyboard(
                [],
                {},
                category_id
            )
        )

        return

    await callback.message.edit_text(
        f"""
<b>{category_name}</b>

لطفاً محصول موردنظر خود را انتخاب کنید:
""",
        reply_markup=grouped_products_keyboard(
            visible_groups,
            products_by_group,
            category_id
        )
    )