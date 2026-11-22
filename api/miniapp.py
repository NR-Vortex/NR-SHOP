"""Run with python -m api.miniapp behind the public HTTPS endpoint."""
import os
import time
from datetime import timezone
from pathlib import Path

from aiohttp import web
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.utils.web_app import safe_parse_webapp_init_data
from sqlalchemy import select, text

from core.config import settings
from core.features import is_feature_enabled
from database.models import User, Wallet
from database.session import async_session
from modules.admin.agency_setup import button
from modules.admin.reseller_panel import panel_account
from core.admin_settings import read_setting

INDEX = Path(__file__).resolve().parents[1] / "miniapp" / "index.html"


async def identity(request):
    authorization=request.headers.get("Authorization","")
    if not authorization.startswith("tma ") or len(authorization)>8192:
        raise web.HTTPUnauthorized()
    raw=authorization[4:]
    try:
        verified = safe_parse_webapp_init_data(settings.BOT_TOKEN.get_secret_value(), raw)
        age = time.time() - verified.auth_date.replace(tzinfo=timezone.utc).timestamp()
        if not verified.user or not -30 <= age <= 3600:
            raise ValueError
    except (TypeError, ValueError, KeyError, IndexError):
        raise web.HTTPUnauthorized()
    async with async_session() as session:
        blocked = await session.scalar(select(User.is_blocked).where(User.telegram_id == verified.user.id))
    if blocked:
        raise web.HTTPForbidden()
    return verified.user


async def dashboard(request):
    user = await identity(request)
    bot = panel_account(user.id)
    if not bot:
        raise web.HTTPForbidden()
    before = request.query.get("before")
    if before is not None and not (before.isascii() and before.isdecimal() and len(before) <= 12):
        raise web.HTTPBadRequest()
    params = {"owner":user.id, "bot":bot[0], "before":int(before) if before else 10**12}
    async with async_session() as session:
        wallet = await session.scalar(select(Wallet.balance).where(Wallet.telegram_user_id == user.id))
        volume = await session.scalar(text("SELECT balance_gb FROM agency_volume WHERE owner_id=:owner AND bot_id=:bot"),params)
        rows = (await session.execute(text("""
            SELECT split_part(reference,':',3)::bigint AS id, customer, gb, delivered
            FROM agency_services WHERE bot_id=:bot AND split_part(reference,':',3)::bigint < :before
            ORDER BY id DESC LIMIT 51
        """),params)).all()
    return web.json_response(dict(name=user.first_name,bot=bot[1],wallet=wallet or 0,volume=volume or 0,
        price=int(read_setting("agency_price_gb","0")),next=str(rows[49].id) if len(rows)>50 else None,
        services=[dict(id=str(i),customer=str(c),gb=g,delivered=d) for i,c,g,d in rows[:50]]),
        headers={"Cache-Control":"no-store"})


async def action(request):
    user = await identity(request)
    if not panel_account(user.id):
        raise web.HTTPForbidden()
    actions = {"buy":("خرید حجم پنل","panel:buy"),"connect":("ساخت کانفیگ","panel:issue")}
    key=request.match_info["key"]
    if key not in actions:
        raise web.HTTPNotFound()
    label,callback=actions[key]
    async with Bot(settings.BOT_TOKEN.get_secret_value(),session=AiohttpSession(proxy=settings.BOT_PROXY)).context() as bot:
        await bot.send_message(user.id,"ادامه در ربات نمایندگی",reply_markup=button(label,callback))
    return web.json_response({"ok":True})


async def index(request):
    return web.FileResponse(INDEX)


async def storefront(request):
    return web.FileResponse(INDEX.with_name("admin.html"))


def create_app():
    from api.admin_console import install
    app=web.Application(client_max_size=10*1024*1024)
    install(app,identity)
    app.router.add_get("/",storefront)
    app.router.add_get("/representative.html",index)
    app.router.add_get("/api/dashboard",dashboard)
    app.router.add_post("/api/action/{key}",action)
    return app


if __name__=="__main__":
    web.run_app(create_app(),host=os.getenv("MINIAPP_BIND","127.0.0.1"),port=8080)
