from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from modules.start.content import build_welcome_message
from modules.shop.keyboards import main_menu_keyboard
from core.message_manager import send_replacing_message
from modules.referral.service import register_referral
from database.session import async_session
from modules.users.service import upsert_user


router = Router(name="start")


@router.message(CommandStart())
async def start_handler(message: Message):
    async with async_session() as session: await upsert_user(session, message.from_user)
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("ref_"):
            try: referrer_id = int(parts[1][4:])
            except ValueError: referrer_id = None
            if referrer_id is not None:
                async with async_session() as session: await register_referral(session, referrer_id, message.from_user.id)

    await send_replacing_message(
        message.bot,
        message.chat.id,
        build_welcome_message(
            message.from_user.full_name
        ),
        reply_markup=main_menu_keyboard()
    )
