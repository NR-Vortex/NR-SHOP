from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from modules.start.content import build_welcome_message
from modules.shop.keyboards import main_menu_keyboard
from core.message_manager import send_replacing_message
from modules.referral.service import complete_referral
from database.session import async_session
from modules.users.service import upsert_user


router = Router(name="start")


@router.message(CommandStart(),F.chat.type=="private")
async def start_handler(message: Message):
    async with async_session() as session:
        await upsert_user(session,message.from_user)
        await complete_referral(session,message.from_user.id)

    await send_replacing_message(
        message.bot,
        message.chat.id,
        build_welcome_message(
            message.from_user.full_name
        ),
        reply_markup=main_menu_keyboard()
    )
