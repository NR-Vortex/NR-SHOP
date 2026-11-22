import logging

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatType
from modules.referral.service import parse_start_referrer, remember_referral

from .service import (
    get_missing_channels,
    MembershipCheckError
)

from .keyboards import join_keyboard
from .config import CHECK_CALLBACK

from modules.start.content import JOIN_MESSAGE
from core.message_manager import send_replacing_message
from database.session import async_session
from database.models import User
from sqlalchemy import select


logger = logging.getLogger(__name__)


class ForceJoinMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler,
        event,
        data
    ):

        user = event.from_user

        if not user or user.is_bot:
            return await handler(event, data)

        async with async_session() as session:
            blocked = (await session.execute(select(User.is_blocked).where(User.telegram_id == user.id))).scalar_one_or_none()
        if blocked:
            if isinstance(event, Message): await event.answer("🚫 دسترسی شما به ربات مسدود شده است.")
            elif isinstance(event, CallbackQuery): await event.answer("🚫 دسترسی شما مسدود شده است.", show_alert=True)
            return

        if isinstance(event, Message) and event.chat.type==ChatType.PRIVATE:
            referrer=parse_start_referrer(event.text)
            if referrer:
                async with async_session() as session:
                    await remember_referral(session,referrer,user.id)

        # اجازه عبور به دکمه بررسی عضویت
        if (
            isinstance(event, CallbackQuery)
            and event.data == CHECK_CALLBACK
        ):
            return await handler(event, data)

        bot: Bot = data["bot"]

        try:

            missing_channels = await get_missing_channels(
                bot,
                user.id
            )

        except MembershipCheckError:

            error_text = (
                "⚠️ در حال حاضر امکان بررسی عضویت وجود ندارد. "
                "لطفاً کمی بعد دوباره تلاش کنید."
            )

            if isinstance(event, Message):

                await event.answer(error_text)

            elif isinstance(event, CallbackQuery):

                await event.answer(
                    error_text,
                    show_alert=True
                )

            return

        # کاربر عضو تمام کانال هاست
        if not missing_channels:

            return await handler(event, data)

        # کاربر عضو نیست
        if isinstance(event, Message):

                await send_replacing_message(
                    bot,
                    user.id,
                    JOIN_MESSAGE,
                reply_markup=join_keyboard()
            )

        elif isinstance(event, CallbackQuery):

            await event.answer(
                "⚠️ شما هنوز عضو تمام کانال‌های تعیین‌شده نیستید.",
                show_alert=True
            )

            if (
                isinstance(event.message, Message)
                and event.message.text != JOIN_MESSAGE
            ):

                await send_replacing_message(
                    bot,
                    user.id,
                    JOIN_MESSAGE,
                    reply_markup=join_keyboard()
                )

        return
