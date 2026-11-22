from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def grouped_products_keyboard(
    groups,
    products_by_group,
    category_id: int
):

    buttons = []

    for group in groups:

        products = products_by_group.get(group.id, [])

        if not products:
            continue

        # تیتر گروه
        buttons.append([
            InlineKeyboardButton(
                text=f"━━━━ {group.name} ━━━━",
                callback_data=f"catalog:group:{group.id}"
            )
        ])

        # محصولات گروه
        for product in products:

            buttons.append([
                InlineKeyboardButton(
                    text=f"🛍 {product.name}",
                    callback_data=f"catalog:product:{product.id}"
                ),
                InlineKeyboardButton(
                    text=f"💰 {product.price:,} تومان",
                    callback_data=f"catalog:product:{product.id}"
                )
            ])

    # بازگشت
    buttons.append([
        InlineKeyboardButton(
            text="بازگشت به دسته‌بندی‌ها",
            callback_data="ai:buy"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="منوی اصلی",
            callback_data="shop:home"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def product_detail_keyboard(category_id: int, product_id: int):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 خرید این محصول",
                    callback_data=f"checkout:buy:{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به محصولات",
                    callback_data=f"catalog:category:{category_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 منوی اصلی",
                    callback_data="shop:home"
                )
            ]
        ]
    )
