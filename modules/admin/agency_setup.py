import secrets
import sqlite3
from contextlib import closing, suppress

from aiogram import Bot, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.token import TokenValidationError
from sqlalchemy import select, text

from core.config import settings
from core.admin_settings import read_setting, write_setting
from core.features import is_feature_enabled
from database.models import Wallet, WalletTransaction
from database.session import async_session
from modules.admin.reseller_panel import panel_account
from modules.admin.agency_bots import connection
from modules.checkout.admin_review import is_admin
from modules.admin.agency_bots import token_cipher

router = Router(name="agency_registration")
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


class Setup(StatesGroup):
    token = State()
    chat = State()
    amount = State()
    confirm = State()
    price = State()
    server = State()


def button(label, action):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=action)]])


def agency(owner):
    with closing(connection()) as db:
        return db.execute("SELECT b.bot_id,b.username FROM agency_tokens b JOIN representatives r ON r.telegram_id=b.owner AND lower(r.bot)=lower(b.username) WHERE b.owner=? AND r.active=1",(owner,)).fetchone()


async def balance(owner, bot_id):
    async with async_session() as session:
        return await session.scalar(text("SELECT balance_gb FROM agency_volume WHERE owner_id=:owner AND bot_id=:bot"), {"owner":owner,"bot":bot_id}) or 0


@router.callback_query(F.data == "agency:bot")
async def menu(callback,state):
    await state.clear()
    await callback.answer()
    if not is_feature_enabled("vps"):
        await callback.message.answer("نمایندگی غیرفعال است.")
        return
    owner = callback.from_user.id
    row = agency(owner)
    if row:
        gb = await balance(owner,row[0])
        await callback.message.answer(f"ربات {row[1]}\nحجم خریداری‌شده: {gb} گیگابایت",reply_markup=button("خرید حجم","agency:buy"))
    await callback.message.answer("برای اتصال یا به‌روزرسانی ربات خود وارد ثبت توکن شوید.",reply_markup=button("ثبت توکن ربات","agency:connect"))


@router.callback_query(F.data == "agency:connect")
async def begin(callback,state):
    await callback.answer()
    if not is_feature_enabled("vps"):
        return
    await state.set_state(Setup.token)
    await callback.message.answer("توکن ربات خود را از BotFather بگیرید و همین‌جا بفرستید. لغو با /cancel")


@router.message(Setup.token,Command("cancel"))
@router.message(Setup.chat,Command("cancel"))
@router.message(Setup.amount,Command("cancel"))
@router.message(Setup.confirm,Command("cancel"))
@router.message(Setup.server,Command("cancel"))
@router.message(Setup.price,Command("cancel"))
async def cancel(message,state):
    await state.clear()
    await message.answer("لغو شد.")


@router.message(Setup.token,F.text)
async def token(message,state):
    value = message.text.strip()
    with suppress(TelegramAPIError):
        await message.delete()
    try:
        sealed = token_cipher().encrypt(value.encode()).decode()
        child = Bot(value,session=AiohttpSession(proxy=settings.BOT_PROXY))
        async with child.context():
            me = await child.get_me()
            if me.id == message.bot.id or (await child.get_webhook_info()).url:
                await message.answer("ربات اصلی یا ربات دارای وب‌هوک قابل اتصال نیست.")
                return
    except RuntimeError:
        await message.answer("مدیر باید کلید رمزگذاری سرور را تنظیم کند.")
        return
    except (TokenValidationError,TelegramAPIError):
        await message.answer("اعتبار توکن تأیید نشد. دوباره بررسی کنید.")
        return
    await state.update_data(sealed=sealed,child=me.id,username="@"+me.username)
    await state.set_state(Setup.chat)
    await message.answer(f"ربات @{me.username} شناسایی شد. آن را Start کنید، سپس چت‌آیدی عددی خود یا گروهی که مدیرش هستید را بفرستید.")


@router.message(Setup.chat,F.text)
async def chat(message,state):
    data = await state.get_data()
    owner = message.from_user.id
    try:
        chat_id = int(message.text.strip())
        if not -(2**63)<chat_id<2**63 or (chat_id>=0 and chat_id!=owner):
            raise ValueError
        child = Bot(token_cipher().decrypt(data["sealed"].encode()).decode(),session=AiohttpSession(proxy=settings.BOT_PROXY))
        async with child.context():
            await child.get_chat(chat_id)
            if chat_id<0 and (await child.get_chat_member(chat_id,owner)).status not in {"creator","administrator"}:
                raise ValueError
    except (ValueError,TelegramAPIError):
        await message.answer("دسترسی ربات و شناسه چت را بررسی کنید.")
        return
    try:
        with closing(connection()) as db,db:
            db.execute("BEGIN IMMEDIATE")
            rep = db.execute("SELECT active FROM representatives WHERE telegram_id=?",(owner,)).fetchone()
            existing = db.execute("SELECT bot_id FROM agency_tokens WHERE owner=?",(owner,)).fetchone()
            managed = db.execute("SELECT owner FROM agency_bots WHERE bot_id=?",(data["child"],)).fetchone()
            if (rep and not rep[0]) or (existing and existing[0]!=data["child"]) or managed:
                await message.answer("این اتصال مجاز نیست. برای تغییر ربات با پشتیبانی تماس بگیرید.")
                return
            db.execute("INSERT INTO agency_tokens VALUES(?,?,?,?,?) ON CONFLICT(owner) DO UPDATE SET token=excluded.token,chat_id=excluded.chat_id,username=excluded.username",(owner,data["child"],data["username"],data["sealed"],chat_id))
            db.execute("INSERT INTO representatives VALUES(?,?,?,1) ON CONFLICT(telegram_id) DO UPDATE SET bot=excluded.bot",(owner,message.from_user.full_name,data["username"]))
    except sqlite3.IntegrityError:
        await message.answer("ربات قبلاً ثبت شده است.")
        return
    await state.clear()
    await message.answer("توکن و چت‌آیدی ثبت شدند. برای فعال‌سازی ربات حجم بخرید.",reply_markup=button("خرید حجم","agency:buy"))


@router.callback_query(F.data=="admin:agency:price")
async def price_start(callback,state):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی غیرمجاز",show_alert=True)
        return
    await callback.answer()
    await state.set_state(Setup.price)
    await callback.message.answer("قیمت فروش هر گیگابایت را به تومان بفرستید.")


@router.message(Setup.price,F.text)
async def price_save(message,state):
    if not is_admin(message.from_user.id):
        return
    value=message.text.strip()
    if not value.isdecimal() or len(value)>12 or int(value)<1:
        await message.answer("قیمت مثبت و معتبر بفرستید.")
        return
    write_setting("agency_price_gb",str(int(value)))
    await state.clear()
    await message.answer("تعرفه ذخیره شد.")


@router.callback_query(F.data.in_({"agency:buy","panel:buy"}))
async def buy(callback,state):
    await callback.answer()
    panel = callback.data == "panel:buy"
    account = panel_account(callback.from_user.id) if panel else agency(callback.from_user.id)
    if not is_feature_enabled("vps") or not account:
        return
    if not read_setting("agency_inbound"):
        await callback.message.answer("فروش حجم پس از تنظیم سرور نمایندگی توسط مدیر فعال می‌شود.")
        return
    price = int(read_setting("agency_price_gb","0"))
    if not price:
        await callback.message.answer("تعرفه فروش حجم هنوز توسط مدیر ثبت نشده است.")
        return
    await state.clear()
    await state.update_data(panel=panel)
    await state.set_state(Setup.amount)
    await callback.message.answer(f"هر گیگابایت {price:,} تومان است. چند گیگابایت می‌خواهید؟")


@router.message(Setup.amount,F.text)
async def quote(message,state):
    count = message.text.strip()
    if not count.isdecimal() or len(count)>6 or not int(count):
        await message.answer("حجم را با عدد صحیح مثبت وارد کنید.")
        return
    price=int(read_setting("agency_price_gb","0"))
    row=panel_account(message.from_user.id) if (await state.get_data()).get("panel") else agency(message.from_user.id)
    if not row or not price:
        await state.clear()
        return
    ref=secrets.token_hex(12)
    amount=int(count)*price
    await state.update_data(ref=ref,gb=int(count),amount=amount,child=row[0])
    await state.set_state(Setup.confirm)
    await message.answer(f"خرید {int(count)} گیگابایت برای {row[1]} با برداشت {amount:,} تومان از کیف پول؟",reply_markup=button("تأیید خرید",f"agency:pay:{ref}"))


@router.callback_query(F.data.startswith("agency:pay:"))
async def pay(callback,state):
    owner=callback.from_user.id
    data=await state.get_data()
    row=panel_account(owner) if data.get("panel") else agency(owner)
    if not is_feature_enabled("vps") or not row or row[0]!=data.get("child") or data.get("ref")!=callback.data.split(":")[-1] or await state.get_state()!=Setup.confirm.state:
        await callback.answer("درخواست منقضی شده است.",show_alert=True)
        return
    ref="agency:"+data["ref"]
    async with async_session.begin() as session:
        wallet=await session.scalar(select(Wallet).where(Wallet.telegram_user_id==owner).with_for_update())
        if await session.scalar(select(WalletTransaction.id).where(WalletTransaction.reference==ref)):
            await callback.answer("این خرید قبلاً ثبت شده است.",show_alert=True)
            return
        if wallet is None or wallet.balance<data["amount"]:
            await callback.answer("موجودی کیف پول کافی نیست.",show_alert=True)
            return
        wallet.balance-=data["amount"]
        session.add(WalletTransaction(wallet_id=wallet.id,kind="debit",amount=data["amount"],balance_after=wallet.balance,reference=ref,description=f"خرید {data['gb']} گیگابایت نمایندگی"))
        await session.execute(text("INSERT INTO agency_volume(bot_id,owner_id,balance_gb) VALUES (:bot,:owner,:gb) ON CONFLICT(bot_id) DO UPDATE SET balance_gb=agency_volume.balance_gb+excluded.balance_gb"),{"bot":row[0],"owner":owner,"gb":data["gb"]})
    await state.clear()
    await callback.answer("خرید ثبت شد.",show_alert=True)
    await callback.message.answer(f"{data['gb']} گیگابایت به اعتبار {row[1]} اضافه شد.")

@router.callback_query(F.data=="admin:agency:server")
async def server_start(callback,state):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی غیرمجاز",show_alert=True)
        return
    from database.models import VPNInbound,VPNPanel
    async with async_session() as session:
        ids=(await session.scalars(select(VPNInbound.id).join(VPNPanel).where(VPNInbound.enabled,VPNPanel.is_active,VPNInbound.protocol.in_(["vless","vmess"])).order_by(VPNInbound.id).limit(100))).all()
    await callback.answer()
    await state.set_state(Setup.server)
    await callback.message.answer("شناسه ورودی فعال و آدرس پایه HTTPS اشتراک همان پنل را با فاصله بفرستید.\nورودی‌ها: "+(", ".join(map(str,ids)) or "هیچ ورودی فعالی نیست"))


@router.message(Setup.server,F.text)
async def server_save(message,state):
    from urllib.parse import urlsplit
    from database.models import VPNInbound,VPNPanel
    if not is_admin(message.from_user.id):
        return
    fields=message.text.strip().split()
    if len(fields)!=2 or not fields[0].isdecimal() or len(fields[0])>9:
        await message.answer("فرمت: شناسه‌ورودی https://example.com/sub")
        return
    inbound=int(fields[0])
    try:
        url=urlsplit(fields[1])
        if url.scheme!="https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError
    except ValueError:
        await message.answer("آدرس پایه اشتراک معتبر نیست.")
        return
    async with async_session() as session:
        valid=await session.scalar(select(VPNInbound.id).join(VPNPanel).where(VPNInbound.id==inbound,VPNInbound.enabled,VPNPanel.is_active,VPNInbound.protocol.in_(["vless","vmess"])))
    if not valid:
        await message.answer("ورودی فعال پیدا نشد.")
        return
    write_setting(f"agency_subscription:{inbound}",fields[1].rstrip("/"))
    write_setting("agency_inbound",str(inbound))
    await state.clear()
    await message.answer("سرور فروش نمایندگی ذخیره شد.")
