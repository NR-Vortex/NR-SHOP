"""Authenticated web presentation of the bot's existing admin handlers."""
import asyncio
import re
import secrets
import time
from contextvars import ContextVar
from html import unescape
from io import BytesIO
from pathlib import Path

from aiohttp import web
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BufferedInputFile, Message, MessageId, Update, User

from core.button_theme import button_key, theme, save_theme, storefront_theme
from core.config import settings
from core.loader import register_routers
from modules.admin.keyboards import admin_dashboard_keyboard
from modules.shop.keyboards import main_menu_keyboard
from modules.force_join.keyboards import join_keyboard
from modules.force_join.service import MembershipCheckError,get_missing_channels
from modules.users.service import upsert_user
from database.session import async_session

UPLOAD_STATES = {
    "SupportStates:waiting_admin_reply",
    "SupportStates:waiting_initial_message",
    "SupportStates:waiting_customer_reply",
    "CheckoutStates:waiting_receipt",
}
from modules.checkout.admin_review import is_admin

current=ContextVar("admin_web_view",default=None)


def plain(value):
    return unescape(re.sub(r"</?(?:b|i|u|s|strong|em|pre|code|blockquote|a)(?:\s[^>]*)?>","",str(value or ""),flags=re.I))


class Screen:
    def __init__(self,uid,mode):
        self.mode=mode
        self.uid=uid
        self.lock=asyncio.Lock()
        self.media={}
        self.reset()

    def reset(self):
        self.is_home=True
        self.caption="مدیریت فروشگاه" if self.mode=="admin" else "به NR SHOP خوش اومدی. سرویس‌ت رو انتخاب کن یا سفارش‌هات رو پیگیری کن."
        self.markup=admin_dashboard_keyboard() if self.mode=="admin" else main_menu_keyboard()
        self.media.clear()
        self.file=None
        self.notice=""
        self.revision=secrets.token_hex(12)

    def rows(self):
        if not self.markup:
            return []
        rows=[]
        for row in self.markup.inline_keyboard:
            items=[]
            for button in row:
                action=button.callback_data
                url=button.url
                if action and (self.mode=="admin" and action!="shop:home" or self.mode=="shop" and not action.startswith(("admin:","vpnadmin:","support:admin:","updates:"))):
                    items.append({"text":button.text,"action":action,"key":button_key(button)})
                elif url and url.startswith("https://"):
                    items.append({"text":button.text,"url":url,"key":button_key(button)})
            if items:
                rows.append(items)
        return rows


async def present(make_request,bot,method):
    view=current.get()
    if not view:
        return await make_request(bot,method)
    name=method.__api_method__
    if name=="answerCallbackQuery":
        if method.text:
            view.notice=plain(method.text)
        return True
    if name=="copyMessage" and method.from_chat_id==view.uid and method.message_id==view.input_id and view.input_text is not None:
        result=await bot.send_message(method.chat_id,view.input_text,parse_mode=None)
        return MessageId(message_id=result.message_id)
    if getattr(method,"chat_id",None)!=view.uid or name not in {"sendMessage","editMessageText","editMessageReplyMarkup","sendPhoto","sendDocument","editMessageCaption","deleteMessage"}:
        return await make_request(bot,method)
    if name=="deleteMessage":
        return True
    if name!="editMessageReplyMarkup":
        view.is_home=False
        view.caption=plain(getattr(method,"text",None) or getattr(method,"caption",None))
        view.file=None
    view.markup=getattr(method,"reply_markup",None)
    if name in {"sendPhoto","sendDocument"}:
        key=secrets.token_urlsafe(18)
        view.media.clear()
        view.media[key]=getattr(method,"photo",None) or getattr(method,"document",None)
        view.file={"key":key,"photo":name=="sendPhoto"}
    return Message.model_validate({"message_id":1,"date":int(time.time()),"chat":{"id":view.uid,"type":"private"},"text":view.caption or " "},context={"bot":bot})


async def lifecycle(app):
    dispatcher=Dispatcher()
    register_routers(dispatcher)
    bot=Bot(settings.BOT_TOKEN.get_secret_value(),session=AiohttpSession(proxy=settings.BOT_PROXY),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.session.middleware(present)
    app["console"]=(dispatcher,bot,{})
    try:
        yield
    finally:
        await dispatcher.storage.close()
        await bot.session.close()


def install(app,identity):
    async def authorized(request,mode="admin"):
        user=await identity(request)
        if mode=="admin" and not is_admin(user.id):
            raise web.HTTPForbidden()
        dp,bot,screens=app["console"]
        return user,dp,bot,screens.setdefault(user.id,Screen(user.id,mode))

    async def payload(dp,bot,screen):
        state=dp.fsm.get_context(bot=bot,chat_id=screen.uid,user_id=screen.uid)
        step=await state.get_state()
        return web.json_response(dict(caption=screen.caption,is_home=screen.is_home,rows=screen.rows(),notice=screen.notice,media=screen.file,
            revision=screen.revision,input=bool(step),password="password" in str(step).lower(),
            upload=step in UPLOAD_STATES,theme=theme() if screen.mode=="admin" else storefront_theme()),headers={"Cache-Control":"no-store"})

    async def access(request):
        user=await identity(request)
        return web.json_response({'admin':is_admin(user.id)},headers={'Cache-Control':'no-store'})

    async def activate(dp,bot,screen,user,mode):
        state=dp.fsm.get_context(bot=bot,chat_id=user.id,user_id=user.id)
        if screen.mode!=mode:
            await state.clear()
            screen.mode=mode
            screen.reset()
        if mode=="shop":
            try:
                missing=await get_missing_channels(bot,user.id)
            except MembershipCheckError:
                raise web.HTTPServiceUnavailable()
            if missing:
                await state.clear()
                screen.reset()
                screen.caption="برای ورود، ابتدا عضو کانال شوید و دوباره بررسی کنید."
                screen.markup=join_keyboard()
                return False
            if screen.caption.startswith("برای ورود،"):
                screen.reset()
            if not getattr(screen,"customer_registered",False):
                async with async_session() as db:
                    await upsert_user(db,User(id=user.id,is_bot=False,first_name=user.first_name,last_name=user.last_name,username=user.username))
                screen.customer_registered=True
        return True

    async def screen(request):
        mode=request.match_info.get("mode","admin")
        user,dp,bot,v=await authorized(request,mode)
        async with v.lock:
            await activate(dp,bot,v,user,mode)
            return await payload(dp,bot,v)

    async def event(request):
        mode=request.match_info.get("mode","admin")
        user,dp,bot,v=await authorized(request,mode)
        async with v.lock:
            if v.mode!=mode:
                raise web.HTTPConflict()
            if not await activate(dp,bot,v,user,mode):
                return await payload(dp,bot,v)
            body=await request.post()
            if body.get("revision")!=v.revision:
                raise web.HTTPConflict()
            action=body.get("action","")
            state=dp.fsm.get_context(bot=bot,chat_id=user.id,user_id=user.id)
            v.revision=secrets.token_hex(12)
            v.notice=""
            if action=="home":
                await state.clear()
                v.reset()
                return await payload(dp,bot,v)
            v.input_text=None
            v.input_id=secrets.randbelow(1000000000)+1
            msg={"message_id":v.input_id,"date":int(time.time()),"chat":{"id":user.id,"type":"private"}}
            sender={"id":user.id,"is_bot":False,"first_name":user.first_name,"last_name":user.last_name,"username":user.username}
            update={"update_id":v.input_id}
            if action=="input" and await state.get_state():
                upload=body.get("file")
                step=await state.get_state()
                if isinstance(upload,web.FileField) and step in UPLOAD_STATES:
                    content=upload.file.read()
                    is_photo=content.startswith((b"\xff\xd8\xff",b"\x89PNG\r\n\x1a\n"))
                    is_pdf=content.startswith(b"%PDF-")
                    if not is_photo and not is_pdf:
                        raise web.HTTPBadRequest()
                    attachment=BufferedInputFile(content,filename="receipt.png" if content.startswith(b"\x89PNG") else "receipt.jpg" if is_photo else "attachment.pdf")
                    if is_photo:
                        posted=await bot.send_photo(user.id,attachment,caption="تصویر ثبت‌شده از مینی‌اپ")
                        msg["photo"]=[photo.model_dump() for photo in posted.photo]
                    else:
                        posted=await bot.send_document(user.id,attachment,caption="فایل ثبت‌شده از مینی‌اپ")
                        msg["document"]=posted.document.model_dump()
                    msg["message_id"]=posted.message_id
                else:
                    value=body.get("value")
                    if not isinstance(value,str) or not value.strip() or len(value)>4096 or (mode=="shop" and value.lstrip().startswith("/") and value.strip()!="/cancel"):
                        raise web.HTTPBadRequest()
                    v.input_text=value
                    msg["text"]=value
                update["message"]={**msg,"from":sender}
            elif action in {b.get("action") for row in v.rows() for b in row}:
                update["callback_query"]={"id":secrets.token_hex(12),"from":sender,"chat_instance":"admin-web","data":action,
                    "message":{**msg,"text":v.caption or " "}}
            else:
                raise web.HTTPBadRequest()
            token=current.set(v)
            try:
                await dp.feed_update(bot,Update.model_validate(update,context={"bot":bot}))
            finally:
                current.reset(token)
                v.input_text=None
            return await payload(dp,bot,v)

    async def media(request):
        mode=request.match_info.get("mode","admin")
        _,_,bot,v=await authorized(request,mode)
        if v.mode!=mode:
            raise web.HTTPNotFound()
        file=v.media.get(request.match_info["key"])
        if isinstance(file,BufferedInputFile):
            return web.Response(body=file.data,content_type="image/png",headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})
        if not isinstance(file,str):
            raise web.HTTPNotFound()
        buf=BytesIO()
        await bot.download(file,destination=buf)
        return web.Response(body=buf.getvalue(),content_type="image/jpeg" if v.file and v.file["photo"] else "application/octet-stream",
            headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})

    async def colors(request):
        await authorized(request)
        try:
            save_theme(await request.json())
        except (ValueError,TypeError):
            raise web.HTTPBadRequest()
        return web.json_response(theme())

    async def page(request):
        return web.FileResponse(Path(__file__).resolve().parents[1]/"miniapp"/"admin.html")

    async def assets(request):
        file=request.match_info["file"]
        return web.FileResponse(Path(__file__).resolve().parents[1]/"miniapp"/file)

    async def public_theme(request):
        return web.json_response(storefront_theme(),headers={"Cache-Control":"no-store"})

    app.cleanup_ctx.append(lifecycle)
    app.router.add_get(r"/{file:studio\.css|studio\.js}",assets)
    app.router.add_get("/admin.html",page)
    app.router.add_get("/shop.html",page)
    app.router.add_get("/api/{mode:shop}/screen",screen)
    app.router.add_post("/api/{mode:shop}/event",event)
    app.router.add_get("/api/{mode:shop}/media/{key}",media)
    app.router.add_get("/api/access",access)
    app.router.add_get("/api/admin/screen",screen)
    app.router.add_post("/api/admin/event",event)
    app.router.add_get("/api/admin/media/{key}",media)
    app.router.add_post("/api/admin/theme",colors)
    app.router.add_get("/api/theme",public_theme)
