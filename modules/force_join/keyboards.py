from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from .config import (
    required_channels,
    CHECK_CALLBACK
)


def join_keyboard():

    buttons = []

    for channel in required_channels():

        if not channel.enabled:
            continue

        buttons.append([
            InlineKeyboardButton(
                text=f"عضویت در کانال {channel.title}",
                url=channel.invite_url
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="بررسی عضویت ✓",
            callback_data=CHECK_CALLBACK
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )