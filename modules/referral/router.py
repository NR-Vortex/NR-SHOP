from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from urllib.parse import quote
from database.session import async_session
from modules.referral.service import referral_stats

router = Router(name="referral")

def referral_keyboard(link: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 اشتراک‌گذاری لینک", url=f"https://t.me/share/url?url={quote(link)}")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی AI", callback_data="ai:home")],
    ])

@router.callback_query(F.data == "ai:referral")
async def referral_handler(callback: CallbackQuery):
    me = await callback.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    async with async_session() as session: rows = await referral_stats(session, callback.from_user.id)
    names = "\n".join(f"• <code>{user_id}</code>" for user_id, _ in rows) or "هنوز دوستی دعوت نشده است."
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(
        "👥 <b>دعوت دوستان و اعتبار</b>\n\n"
        f"🔗 لینک دعوت اختصاصی شما:\n<code>{link}</code>\n\n"
        f"👤 تعداد دعوت‌شدگان: {len(rows)}\n\n📋 فهرست دوستان:\n{names}",
        reply_markup=referral_keyboard(link))
