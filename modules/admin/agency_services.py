import json
import secrets
import time
from contextlib import closing
from uuid import uuid4

from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from sqlalchemy import select, text

from core.admin_settings import read_setting
from core.features import is_feature_enabled
from database.models import VPNInbound, VPNPanel
from database.session import async_session
from modules.vpn.panel.client import ThreeXUIClient


async def reserve(reference, bot_id, owner, customer, gb, inbound_id, days=0):
    params = dict(ref=reference, bot=bot_id, owner=owner, customer=customer, gb=gb, inbound=inbound_id,
                  client=str(uuid4()), sub=secrets.token_hex(12),expiry=(int(time.time())+days*86400)*1000 if days else 0)
    async with async_session.begin() as session:
        credit = await session.scalar(text("SELECT balance_gb FROM agency_volume WHERE bot_id=:bot AND owner_id=:owner FOR UPDATE"), params)
        row = (await session.execute(text("SELECT * FROM agency_services WHERE reference=:ref"), params)).mappings().first()
        if row:
            return dict(row)
        if credit is None or credit < gb:
            raise ValueError("حجم نمایندگی کافی نیست.")
        await session.execute(text("UPDATE agency_volume SET balance_gb=balance_gb-:gb WHERE bot_id=:bot"),params)
        row = (await session.execute(text("""INSERT INTO agency_services(reference,bot_id,customer,gb,inbound_id,client_id,subscription,expiry_ms)
            VALUES(:ref,:bot,:customer,:gb,:inbound,:client,:sub,:expiry) RETURNING *"""),params)).mappings().one()
        return dict(row)


async def provision(row):
    async with async_session.begin() as session:
        delivered = await session.scalar(text("SELECT delivered FROM agency_services WHERE reference=:ref FOR UPDATE"),{"ref":row["reference"]})
        if delivered:
            return
        panel, inbound = (await session.execute(select(VPNPanel,VPNInbound).join(VPNInbound).where(
            VPNInbound.id==row["inbound_id"],VPNInbound.enabled,VPNPanel.is_active))).one()
        async with ThreeXUIClient(panel.base_url,panel.username,panel.encrypted_password) as api:
            remote = next(i for i in await api.list_inbounds() if i["id"]==inbound.remote_inbound_id and i.get("enable") and i.get("protocol") in {"vless","vmess"})
            config = remote["settings"]
            clients = (json.loads(config) if isinstance(config,str) else config)["clients"]
            if not any(c.get("id")==row["client_id"] for c in clients):
                await api.add_client(inbound.remote_inbound_id,{"id":row["client_id"],"email":"agency-"+row["subscription"],
                    "subId":row["subscription"],"enable":True,"totalGB":row["gb"]*1024**3,"expiryTime":row["expiry_ms"]})
        await session.execute(text("UPDATE agency_services SET delivered=true WHERE reference=:ref"),{"ref":row["reference"]})


def register_service_commands(dispatcher, owner, bot_id):
    from modules.admin.agency_bots import connection

    @dispatcher.message(Command("issue","retry"))
    async def issue(message):
        if message.chat.type!="private" or message.from_user.id!=owner or not is_feature_enabled("vps"):
            return
        with closing(connection()) as db:
            registration=db.execute("SELECT t.chat_id FROM agency_tokens t JOIN representatives r ON r.telegram_id=t.owner WHERE t.owner=? AND t.bot_id=? AND lower(t.username)=lower(r.bot) AND r.active=1",(owner,bot_id)).fetchone()
        if not registration:
            return
        fields=message.text.split()
        retry=fields[0].split("@")[0]=="/retry"
        try:
            if retry:
                if len(fields)!=2 or not fields[1].isdecimal():
                    raise ValueError("فرمت: /retry شماره‌درخواست")
                ref=f"{bot_id}:{owner}:{int(fields[1])}"
                async with async_session() as session:
                    row=(await session.execute(text("SELECT * FROM agency_services WHERE reference=:ref"),{"ref":ref})).mappings().first()
                if not row:
                    raise ValueError("درخواست پیدا نشد.")
            else:
                if len(fields)!=3 or not all(s.isdecimal() for s in fields[1:]):
                    raise ValueError("فرمت: /issue شناسه‌عددی‌مشتری حجم‌به‌گیگابایت")
                customer,gb=map(int,fields[1:])
                if not 0<customer<2**63 or not 0<gb<=999999:
                    raise ValueError("شناسه یا حجم نامعتبر است.")
                inbound_id=int(read_setting("agency_inbound","0"))
                if not inbound_id or not read_setting(f"agency_subscription:{inbound_id}"):
                    raise ValueError("مدیر هنوز سرور فروش نمایندگی را تنظیم نکرده است.")
                ref=f"{bot_id}:{owner}:{message.message_id}"
                row=await reserve(ref,bot_id,owner,customer,gb,inbound_id)
        except ValueError as exc:
            await message.answer(str(exc))
            return
        request_id=ref.rsplit(":",1)[1]
        try:
            await provision(row)
        except Exception:
            await message.answer(f"حجم رزرو شد. پس از بررسی اتصال پنل دوباره بفرستید: /retry {request_id}")
            return
        base=read_setting(f"agency_subscription:{row['inbound_id']}")
        if not base:
            await message.answer(f"آدرس اشتراک سرور تنظیم نشده است. پس از تنظیم: /retry {request_id}")
            return
        link=base.rstrip("/")+"/"+row["subscription"]
        try:
            await message.bot.send_message(row["customer"],f"اشتراک {row['gb']} گیگابایتی شما\n{link}")
        except TelegramAPIError:
            await message.answer(f"سرویس ساخته شد. مشتری باید این ربات را Start کند. ارسال دوباره: /retry {request_id}")
            return
        await message.answer(f"سرویس به مشتری تحویل داده شد. شماره درخواست {request_id}")
        try:
            await message.bot.send_message(registration[0],f"تحویل {row['gb']} گیگابایت به مشتری {row['customer']} · درخواست {request_id}")
        except TelegramAPIError:
            await message.answer("ارسال گزارش به چت ثبت‌شده ناموفق بود.")
