from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from modules.start.content import build_welcome_message
from modules.shop.keyboards import main_menu_keyboard
from core.message_manager import send_replacing_message
from modules.referral.service import complete_referral
from database.session import async_session
from modules.users.service import upsert_user


router = Router(name="start")


@router.message(Command("shop"),F.chat.type=="private")
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


@router.message(Command("orders","support"),F.chat.type=="private")
async def public_shortcuts(message: Message):
    from core.features import is_feature_enabled
    command=message.text.split()[0].split("@")[0]
    if command=="/orders":
        feature,label,action="orders","محصولات من","shop:orders"
    else:
        feature,label,action="support","پشتیبانی","support:menu"
    if not is_feature_enabled(feature):
        await message.answer("این بخش فعلاً غیرفعال است.",reply_markup=main_menu_keyboard())
        return
    await send_replacing_message(message.bot,message.chat.id,f"برای باز کردن «{label}» دکمه را بزن.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=label,callback_data=action)],
            [InlineKeyboardButton(text="بازگشت به فروشگاه",callback_data="shop:home")],
        ]))
