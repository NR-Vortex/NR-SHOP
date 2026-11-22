import asyncio
import json
import os
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.admin_settings import read_setting, write_setting
from core.releases import REPOSITORY, installed, latest_release, version_tuple, write_json
from modules.checkout.admin_review import get_admin_ids, is_admin

router = Router(name="release_updates")
router.callback_query.filter(F.from_user.id.func(is_admin),F.message.chat.type=="private")
ROOT = Path(__file__).resolve().parents[2]
QUEUE = Path(os.getenv("NR_SHOP_UPDATE_DIR") or ROOT/".updates")


def release_buttons(tag):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="جزئیات نسخه در GitHub",url=f"https://github.com/{REPOSITORY}/releases/tag/{tag}")],
        [InlineKeyboardButton(text="نصب روی همین سرور",callback_data=f"updates:confirm:{tag}")],
    ])


async def available():
    current = installed(ROOT)
    tag = await asyncio.to_thread(latest_release)
    return current,tag if version_tuple(tag)>version_tuple(current) else None


@router.callback_query(F.data=="updates:menu")
async def menu(callback):
    await callback.answer()
    try:
        current,tag = await available()
    except (OSError,ValueError,KeyError):
        await callback.message.answer("بررسی نسخهٔ جدید انجام نشد. اتصال سرور به GitHub را بررسی کن.")
        return
    try:
        status=json.loads((QUEUE/"status.json").read_text(encoding="utf8"))
    except (OSError,ValueError):
        status={}
    statuses={"running":"در حال نصب","done":"نصب شد","failed":"نصب ناموفق بود. گزارش سرویس به‌روزرسانی سرور را ببین."}
    suffix=f"\nآخرین درخواست {status.get('tag','')} · {statuses[status['state']]}" if status.get("state") in statuses else ""
    await callback.message.answer(f"نسخهٔ فعلی {current}"+(f"\nنسخهٔ آمادهٔ نصب {tag}" if tag else "\nنسخهٔ جدیدتری منتشر نشده.")+suffix,
                                  reply_markup=release_buttons(tag) if tag else None)


@router.callback_query(F.data.regexp(r"^updates:confirm:v[0-9]+\.[0-9]+\.[0-9]+$"))
async def confirmation(callback):
    tag=callback.data.rsplit(":",1)[1]
    await callback.answer()
    await callback.message.answer(f"نسخهٔ {tag} روی همین سرور نصب می‌شود. ربات و مینی‌اپ ممکن است برای مدت کوتاهی قطع شوند.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="تأیید و نصب",callback_data=f"updates:apply:{tag}")],
            [InlineKeyboardButton(text="بازگشت",callback_data="updates:menu")],
        ]))


@router.callback_query(F.data.regexp(r"^updates:apply:v[0-9]+\.[0-9]+\.[0-9]+$"))
async def apply(callback):
    tag=callback.data.rsplit(":",1)[1]
    if not os.getenv("NR_SHOP_UPDATE_DIR") or not (QUEUE/"enabled").is_file():
        await callback.answer("سرویس نصب به‌روزرسانی روی این سرور فعال نیست.",show_alert=True)
        return
    await callback.answer()
    try:
        _,expected=await available()
        if tag!=expected:
            await callback.message.answer("نسخهٔ قابل نصب تغییر کرده است. بخش به‌روزرسانی را دوباره باز کن.")
            return
        write_json(QUEUE/"request.json",{"tag":tag})
    except (OSError,ValueError,KeyError):
        await callback.message.answer("درخواست ثبت نشد. اتصال GitHub و سرویس به‌روزرسانی را بررسی کن.")
        return
    await callback.message.answer(f"درخواست نصب {tag} ثبت شد. نتیجه در «به‌روزرسانی» نمایش داده می‌شود.")


async def notify_releases(bot):
    while True:
        try:
            _,tag=await available()
            if tag:
                for admin in get_admin_ids():
                    key=f"release_notice:{admin}"
                    if read_setting(key)==tag:
                        continue
                    try:
                        await bot.send_message(admin,f"نسخهٔ پایدار {tag} برای NR SHOP منتشر شد.",reply_markup=release_buttons(tag))
                    except TelegramAPIError:
                        continue
                    write_setting(key,tag)
        except (OSError,ValueError,KeyError):
            pass
        await asyncio.sleep(3600)
