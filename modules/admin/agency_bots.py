import asyncio
import logging
from contextlib import closing

from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ManagedBotUpdated, Message

from core.admin_settings import representative_db
from core.config import settings
from core.features import is_feature_enabled

router = Router(name="agency_bots")
logger = logging.getLogger(__name__)


def token_cipher():
    import os
    from cryptography.fernet import Fernet
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("AGENCY_TOKEN_KEY")
    if not key:
        raise RuntimeError("Agency encryption key missing")
    return Fernet(key.encode())


def connection():
    db = representative_db()
    db.execute("CREATE TABLE IF NOT EXISTS agency_bots (owner INTEGER PRIMARY KEY, bot_id INTEGER UNIQUE NOT NULL, username TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS agency_tokens (owner INTEGER PRIMARY KEY,bot_id INTEGER UNIQUE NOT NULL,username TEXT NOT NULL,token TEXT NOT NULL,chat_id INTEGER NOT NULL)")
    return db


def active_bots():
    with closing(connection()) as db:
        return db.execute(
            "SELECT a.bot_id, r.telegram_id, r.name FROM agency_bots a JOIN representatives r "
            "ON a.owner=r.telegram_id WHERE r.active=1 AND lower(r.bot)=lower(a.username)"
        ).fetchall()


@router.managed_bot()
async def managed_update(event: ManagedBotUpdated):
    owner, child = event.user.id, event.bot_user
    if not child.username:
        return
    username = "@" + child.username
    with closing(connection()) as db, db:
        row = db.execute("SELECT active,bot FROM representatives WHERE telegram_id=?", (owner,)).fetchone()
        if not row or not row[0] or row[1].lower() not in ("-", username.lower()):
            return
        db.execute("INSERT INTO agency_bots VALUES (?,?,?) ON CONFLICT(owner) DO UPDATE SET bot_id=excluded.bot_id,username=excluded.username",
                   (owner, child.id, username))
        db.execute("UPDATE representatives SET bot=? WHERE telegram_id=?", (username, owner))


async def serve(manager, child_id, owner, manager_name):
    with closing(connection()) as db:
        registered = db.execute("SELECT token,chat_id FROM agency_tokens WHERE owner=? AND bot_id=?", (owner,child_id)).fetchone()
    if registered:
        token = token_cipher().decrypt(registered[0].encode()).decode()
    else:
        token = await manager.get_managed_bot_token(user_id=child_id)
    child = Bot(token, session=AiohttpSession(proxy=settings.BOT_PROXY))
    from core.button_theme import style_keyboard
    child.session.middleware(style_keyboard)
    from aiogram.fsm.storage.memory import SimpleEventIsolation
    from core.message_manager import register_navigation
    dispatcher = Dispatcher(events_isolation=SimpleEventIsolation())
    register_navigation(dispatcher,child.session)
    if registered:
        from modules.admin.agency_services import register_service_commands
        register_service_commands(dispatcher,owner,child_id)
        from modules.admin.agency_store import register_store, storefront, register_customer
        register_store(dispatcher,owner,child_id)

    @dispatcher.message(CommandStart())
    async def welcome(message: Message):
        if not is_feature_enabled("vps"):
            return
        name = next((name for bot_id, uid, name in active_bots() if bot_id == child_id and uid == owner), None)
        if registered:
            with closing(connection()) as db:
                row = db.execute("SELECT r.name FROM representatives r JOIN agency_tokens t ON t.owner=r.telegram_id WHERE r.telegram_id=? AND t.bot_id=? AND lower(r.bot)=lower(t.username) AND r.active=1",(owner,child_id)).fetchone()
            name = row[0] if row else None
        if name is None:
            return
        link = f"https://t.me/{manager_name}?start=ref_{owner}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ورود به فروشگاه", url=link)]])
        if registered:
            if message.chat.type != "private":
                return
            if message.from_user.id != owner:
                await register_customer(child_id,message.from_user)
            keyboard = storefront(message.from_user.id == owner)
        if registered and message.from_user.id == owner:
            await message.answer("ساخت سرویس مشتری: /issue شناسه‌عددی‌مشتری حجم‌به‌گیگابایت")
        await message.answer(f"به نمایندگی {name} خوش آمدید.", reply_markup=keyboard)

    try:
        await dispatcher.start_polling(child, handle_signals=False, handle_as_tasks=False, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await child.session.close()


async def supervise(manager):
    tasks = {}
    try:
        while True:
            wanted = {bot_id: owner for bot_id, owner, _ in active_bots()} if is_feature_enabled("vps") else {}
            if is_feature_enabled("vps"):
                from database.session import async_session
                from sqlalchemy import text
                with closing(connection()) as db:
                    registered = dict(db.execute("SELECT t.bot_id,t.owner FROM agency_tokens t JOIN representatives r ON r.telegram_id=t.owner WHERE r.active=1 AND lower(t.username)=lower(r.bot)"))
                if registered:
                    try:
                        async with async_session() as session:
                            paid = (await session.execute(text("SELECT bot_id,owner_id FROM agency_volume WHERE balance_gb>=0"))).all()
                        wanted.update((bid,uid) for bid,uid in paid if registered.get(bid)==uid)
                    except Exception:
                        logger.warning("Agency volume database unavailable")
            for child_id, task in list(tasks.items()):
                if child_id not in wanted or task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    del tasks[child_id]
            for child_id, owner in wanted.items():
                if child_id not in tasks:
                    me = await manager.me()
                    tasks[child_id] = asyncio.create_task(serve(manager, child_id, owner, me.username))
            await asyncio.sleep(15)
    finally:
        for task in tasks.values():
            task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)
