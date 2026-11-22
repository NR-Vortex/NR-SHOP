"""Quota accounts for representatives using the central panel without a storefront bot."""
from contextlib import closing
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import text

from core.admin_settings import read_setting, representative_db
from core.features import is_feature_enabled
from database.session import async_session
from modules.admin.agency_services import provision, reserve

router = Router(name="reseller_panel")
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


class Issue(StatesGroup):
    limits = State()


def panel_account(owner):
    # Telegram bot IDs are positive. Negative IDs isolate central-panel quota
    # from credits bought separately for a representative's own storefront.
    with closing(representative_db()) as db:
        row = db.execute("SELECT active FROM representatives WHERE telegram_id=?", (owner,)).fetchone()
    if not is_feature_enabled("vps") or (row and not row[0]):
        return None
    return -owner, "پنل نمایندگی"


def buttons(entries):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label,callback_data=action)] for label,action in entries])


@router.callback_query(F.data=="agency:panel")
async def home(q,state):
    await state.clear()
    owner=q.from_user.id
    account=panel_account(owner)
    if not account:
        await q.answer("پنل غیرفعال است.",show_alert=True)
        return
    from modules.admin.agency_setup import balance
    available=await balance(owner,account[0])
    await q.answer()
    await q.message.answer(f"پنل نمایندگی\nسهمیه آمادهٔ تخصیص {available:,} گیگابایت",reply_markup=buttons([
        ("خرید حجم پنل","panel:buy"),("ساخت کانفیگ","panel:issue"),("کانفیگ‌های من","panel:list:0")]))


@router.callback_query(F.data=="panel:issue")
async def issue_start(q,state):
    if not panel_account(q.from_user.id):
        await q.answer("پنل غیرفعال است.",show_alert=True)
        return
    await q.answer()
    await state.set_state(Issue.limits)
    await q.message.answer("اول حجم و بعد مدت رو با فاصله بفرست. مثلاً ۱۰ ۳۰ یعنی ۱۰ گیگ برای ۳۰ روز. برای لغو، /cancel رو بفرست.")


@router.message(Issue.limits,Command("cancel"))
async def cancel(m,state):
    await state.clear()
    await m.answer("لغو شد.")


async def deliver(message,row):
    base=read_setting(f"agency_subscription:{row['inbound_id']}")
    if not base:
        await message.answer("آدرس اشتراک پنل مرکزی تنظیم نشده است.")
        return
    try:
        await provision(row)
    except Exception:
        await message.answer("حجم رزرو شد. پس از اتصال پنل مرکزی، از «کانفیگ‌های من» دوباره دریافت کنید.")
        return
    await message.answer(f"کانفیگ {row['gb']} گیگابایتی شما\n<code>{escape(base.rstrip('/')+'/'+row['subscription'])}</code>")


@router.message(Issue.limits,F.text)
async def issue(m,state):
    owner=m.from_user.id
    account=panel_account(owner)
    if not account:
        await state.clear()
        return
    parts=m.text.split()
    if len(parts)!=2 or not all(x.isdecimal() and len(x)<=6 for x in parts):
        await m.answer("دو عدد مثبت برای حجم و مدت وارد کنید.")
        return
    gb,days=map(int,parts)
    if not (0<gb<=999999 and 0<days<=3650):
        await m.answer("حجم یا مدت معتبر نیست.")
        return
    inbound=int(read_setting("agency_inbound","0"))
    if not inbound or not read_setting(f"agency_subscription:{inbound}"):
        await m.answer("سرور فروش نمایندگی هنوز توسط مدیر تنظیم نشده است.")
        return
    try:
        row=await reserve(f"panel:{owner}:{m.message_id}",account[0],owner,owner,gb,inbound,days)
    except ValueError as exc:
        await m.answer(str(exc),reply_markup=buttons([("خرید حجم","panel:buy")]))
        return
    await state.clear()
    await deliver(m,row)


@router.callback_query(F.data.regexp(r"^panel:(list|get):[0-9]{1,12}$"))
async def configs(q):
    owner=q.from_user.id
    account=panel_account(owner)
    if not account:
        await q.answer("پنل غیرفعال است.",show_alert=True)
        return
    _,action,raw=q.data.split(":")
    await q.answer()
    async with async_session() as db:
        if action=="get":
            row=(await db.execute(text("SELECT * FROM agency_services WHERE bot_id=:tenant AND reference=:ref"),
                {"tenant":account[0],"ref":f"panel:{owner}:{raw}"})).mappings().first()
            if row:
                await deliver(q.message,row)
            return
        page=int(raw)
        rows=(await db.execute(text("""SELECT reference,gb,delivered FROM agency_services WHERE bot_id=:tenant
            ORDER BY split_part(reference,':',3)::bigint DESC LIMIT 11 OFFSET :skip"""),
            {"tenant":account[0],"skip":page*10})).mappings().all()
    entries=[(f"{r['gb']} گیگ · "+("دریافت لینک" if r["delivered"] else "تلاش مجدد"),"panel:get:"+r["reference"].split(":")[-1]) for r in rows[:10]]
    if page:
        entries.append(("قبلی",f"panel:list:{page-1}"))
    if len(rows)>10:
        entries.append(("بعدی",f"panel:list:{page+1}"))
    entries.append(("بازگشت","agency:panel"))
    await q.message.answer("کانفیگ‌های شما" if rows else "هنوز کانفیگی نساخته‌اید.",reply_markup=buttons(entries))
