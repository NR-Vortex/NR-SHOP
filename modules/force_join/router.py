import logging

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message

from .config import CHECK_CALLBACK

from .service import (
    get_missing_channels,
    MembershipCheckError
)

from .keyboards import join_keyboard
from modules.shop.keyboards import main_menu_keyboard

from modules.start.content import build_welcome_message
from core.message_manager import send_replacing_message


router = Router(name="force_join")

logger = logging.getLogger(__name__)


@router.callback_query(F.data == CHECK_CALLBACK)
async def verify_membership(
    callback: CallbackQuery,
    bot: Bot
):

    try:

        missing_channels = await get_missing_channels(
            bot,
            callback.from_user.id
        )

    except MembershipCheckError:

        await callback.answer(
            "خطا در بررسی عضویت. دوباره تلاش کنید.",
            show_alert=True
        )

        return

    # هنوز عضو نشده
    if missing_channels:

        await callback.answer(
            "❌ شما هنوز عضو تمام کانال‌ها نشده‌اید!",
            show_alert=True
        )

        return

    # عضویت تایید شد
    await callback.answer(
        "✅ عضویت شما تأیید شد!",
        show_alert=True
    )

    if isinstance(callback.message, Message):

        await callback.message.edit_text(
            build_welcome_message(callback.from_user.full_name),
            reply_markup=main_menu_keyboard()
        )

    else:

        await send_replacing_message(
            bot,
            callback.from_user.id,
            build_welcome_message(callback.from_user.full_name),
            reply_markup=main_menu_keyboard()
        )
