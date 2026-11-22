from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def categories_keyboard(categories, back_callback="ai:home"):

    buttons = []

    for category in categories:

        buttons.append([
            InlineKeyboardButton(
                text=category.name,
                callback_data=f"catalog:category:{category.id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data=back_callback
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )