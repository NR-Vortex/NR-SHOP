from contextlib import closing

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import text

from core.admin_settings import read_setting, write_setting
from core.features import is_feature_enabled
from database.session import async_session
from modules.admin.agency_services import reserve, provision


def keyboard(entries):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label,callback_data=action)] for label,action in entries])


async def register_customer(bot_id, user):
    async with async_session.begin() as db:
        await db.execute(text("""INSERT INTO agency_customers(bot_id,customer,display_name)
            VALUES (:bot,:customer,:name) ON CONFLICT(bot_id,customer)
            DO UPDATE SET display_name=excluded.display_name"""),
            {"bot":bot_id,"customer":user.id,"name":user.full_name})


def storefront(is_owner):
    entries=[("بسته‌ها و خرید","rs:plans:0"),("سفارش‌های من","rs:mine:0")]
    if is_owner:
        entries.append(("مدیریت فروش","rs:manage"))
    return keyboard(entries)


def register_store(dispatcher,owner,bot_id):
    from modules.admin.agency_bots import connection

    router=Router()
    dispatcher.include_router(router)

    def enabled(event):
        with closing(connection()) as db:
            active=db.execute("SELECT 1 FROM representatives r JOIN agency_tokens t ON t.owner=r.telegram_id AND lower(t.username)=lower(r.bot) WHERE r.active=1 AND t.bot_id=? AND t.owner=?",(bot_id,owner)).fetchone()
        return bool(active and is_feature_enabled("vps"))

    router.message.filter(F.chat.type=="private",enabled)
    router.callback_query.filter(F.message.chat.type=="private",enabled)
    card_key=f"agency_card:{bot_id}"

    async def records(sql,**params):
        async with async_session.begin() as db:
            result=await db.execute(text(sql),dict(bot=bot_id,**params))
            return result.mappings().all() if result.returns_rows else []

    @router.callback_query(F.data=="rs:manage",F.from_user.id==owner)
    async def manage(q):
        await q.answer()
        await q.message.answer("تنظیم مقصد واریز مشتری کارتی به نام خودتان:\n/card شماره‌کارت نام‌دارنده\nساخت بسته:\n/plan حجم‌گیگ روز قیمت‌تومان نام‌بسته\nمثال: /plan 10 30 150000 ماهانه\nتوقف فروش بسته: /hide شناسه‌بسته",reply_markup=keyboard([("رسیدهای در انتظار و تحویل مجدد","rs:review:0"),("مشتری‌های این ربات","rs:customers:0")]))

    @router.callback_query(F.data.regexp(r"^rs:customers:[0-9]{1,8}$"), F.from_user.id==owner)
    async def customers(q):
        page=int(q.data.rsplit(":",1)[1])
        rows=await records("""SELECT customer,display_name FROM agency_customers
            WHERE bot_id=:bot AND customer<>:owner ORDER BY customer LIMIT 16 OFFSET :skip""",
            owner=owner,skip=page*15)
        entries=[]
        if page:
            entries.append(("قبلی",f"rs:customers:{page-1}"))
        if len(rows)>15:
            entries.append(("بعدی",f"rs:customers:{page+1}"))
        entries.append(("مدیریت فروش","rs:manage"))
        lines=[f"{(r['display_name'] or 'مشتری')[:100]} · {r['customer']}" for r in rows[:15]]
        await q.answer()
        await q.message.answer("\n".join(lines) or "هنوز مشتری ثبت نشده است.",reply_markup=keyboard(entries))

    @router.message(Command("card"),F.from_user.id==owner)
    async def card(m):
        fields=m.text.split(maxsplit=2)
        if len(fields)!=3 or not fields[1].isascii() or not fields[1].isdigit() or len(fields[1])!=16 or len(fields[2])>80:
            await m.answer("شماره ۱۶ رقمی با ارقام انگلیسی و نام صاحب کارت را وارد کنید.")
            return
        write_setting(card_key,fields[1]+" · "+fields[2])
        await m.answer("مقصد پرداخت سفارش‌های جدید ذخیره شد.")

    @router.message(Command("plan"),F.from_user.id==owner)
    async def plan(m):
        fields=m.text.split(maxsplit=4)
        if len(fields)!=5 or not all(x.isdecimal() and len(x)<=12 for x in fields[1:4]):
            await m.answer("فرمت: /plan حجم‌گیگ روز قیمت‌تومان نام‌بسته")
            return
        gb,days,price=map(int,fields[1:4])
        if not (0<gb<=999999 and 0<days<=3650 and price>0 and len(fields[4])<=80):
            await m.answer("مقادیر بسته معتبر نیست.")
            return
        rows=await records("INSERT INTO agency_plans(bot_id,name,gb,days,price) VALUES(:bot,:name,:gb,:days,:price) RETURNING id",name=fields[4],gb=gb,days=days,price=price)
        await m.answer(f"بسته شماره {rows[0]['id']} ثبت شد.")

    @router.message(Command("hide"),F.from_user.id==owner)
    async def hide(m):
        fields=m.text.split()
        if len(fields)!=2 or not fields[1].isdecimal() or len(fields[1])>18:
            await m.answer("فرمت: /hide شناسه‌بسته")
            return
        rows=await records("UPDATE agency_plans SET active=false WHERE id=:id AND bot_id=:bot RETURNING id",id=int(fields[1]))
        await m.answer("فروش بسته متوقف شد." if rows else "بسته پیدا نشد.")

    @router.callback_query(F.data.regexp(r"^rs:(plans|mine|review):[0-9]{1,8}$"))
    async def listing(q):
        _,kind,offset=q.data.split(":")
        page=int(offset)
        if kind=="review" and q.from_user.id!=owner:
            await q.answer("دسترسی غیرمجاز")
            return
        await q.answer()
        if kind=="plans":
            rows=await records("SELECT * FROM agency_plans WHERE bot_id=:bot AND active ORDER BY id DESC LIMIT 11 OFFSET :skip",skip=page*10)
            entries=[(f"#{r['id']} {r['name']} · {r['gb']} گیگ · {r['days']} روز · {r['price']:,} تومان",f"rs:order:{r['id']}") for r in rows[:10]]
        else:
            predicate="status IN ('review','paid')" if kind=="review" else "customer=:customer"
            rows=await records("SELECT * FROM agency_retail_orders WHERE bot_id=:bot AND "+predicate+" ORDER BY id DESC LIMIT 11 OFFSET :skip",customer=q.from_user.id,skip=page*10)
            labels={"open":"در انتظار رسید","review":"بررسی رسید","paid":"در انتظار تحویل","done":"تحویل‌شده","rejected":"ردشده"}
            entries=[(f"#{r['id']} {r['name']} · {labels[r['status']]}",f"rs:show:{r['id']}") for r in rows[:10]]
        if page:
            entries.append(("قبلی",f"rs:{kind}:{page-1}"))
        if len(rows)>10:
            entries.append(("بعدی",f"rs:{kind}:{page+1}"))
        await q.message.answer("انتخاب کنید." if rows else "موردی ثبت نشده است.",reply_markup=keyboard(entries) if entries else None)

    @router.callback_query(F.data.regexp(r"^rs:order:[0-9]+$"))
    async def order(q):
        account=read_setting(card_key)
        if not account:
            await q.answer("مقصد پرداخت تنظیم نشده است.",show_alert=True)
            return
        rows=await records("""INSERT INTO agency_retail_orders(bot_id,customer,plan_id,name,gb,days,price,checkout_key,payment_destination)
            SELECT p.bot_id,:customer,p.id,p.name,p.gb,p.days,p.price,:key,:account FROM agency_plans p
            JOIN agency_volume v ON v.bot_id=p.bot_id AND v.owner_id=:owner
            WHERE p.bot_id=:bot AND p.id=:id AND p.active AND v.balance_gb>=p.gb
            ON CONFLICT(checkout_key) DO UPDATE SET checkout_key=excluded.checkout_key RETURNING *""",
            customer=q.from_user.id,owner=owner,account=account,id=int(q.data.split(":")[-1]),key=f"{bot_id}:{q.from_user.id}:{q.message.message_id}:{q.data}")
        if not rows:
            await q.answer("موجودی این بسته کافی نیست یا فروش متوقف شده است.",show_alert=True)
            return
        await q.answer()
        r=rows[0]
        await q.message.answer(f"سفارش {r['id']} · {r['name']}\n{r['gb']} گیگ، {r['days']} روز\nمبلغ: {r['price']:,} تومان\nمقصد واریز: {r['payment_destination']}\nعکس رسید را با شماره سفارش {r['id']} در کپشن ارسال کنید.")

    @router.message(F.photo)
    async def receipt(m):
        caption=(m.caption or "").strip()
        if not caption.isdecimal() or len(caption)>18:
            await m.answer("شماره سفارش را در کپشن عکس رسید بنویسید.")
            return
        rows=await records("UPDATE agency_retail_orders SET receipt=:file,status='review' WHERE id=:id AND bot_id=:bot AND customer=:customer AND status='open' RETURNING id",file=m.photo[-1].file_id,id=int(caption),customer=m.from_user.id)
        if not rows:
            await m.answer("سفارش قابل ثبت رسید نیست.")
            return
        await m.answer("رسید برای بررسی ثبت شد.")
        try:
            await m.bot.send_message(owner,f"رسید جدید سفارش {caption}",reply_markup=keyboard([("بررسی رسید",f"rs:show:{int(caption)}")]))
        except TelegramAPIError:
            pass

    @router.callback_query(F.data.regexp(r"^rs:show:[0-9]+$"))
    async def show(q):
        rows=await records("SELECT * FROM agency_retail_orders WHERE bot_id=:bot AND id=:id AND (customer=:viewer OR :viewer=:owner)",id=int(q.data.split(":")[-1]),viewer=q.from_user.id,owner=owner)
        if not rows:
            await q.answer("سفارش پیدا نشد.")
            return
        await q.answer()
        r=rows[0]; oid=r["id"]
        detail=f"سفارش {oid} · {r['name']} · {r['gb']} گیگ · {r['days']} روز · {r['price']:,} تومان"
        if q.from_user.id==owner and r["status"]=="review":
            await q.message.answer_photo(r["receipt"],caption=detail,reply_markup=keyboard([("تأیید و تحویل",f"rs:accept:{oid}"),("رد رسید",f"rs:reject:{oid}")]))
        elif r["status"]=="open":
            await q.message.answer(detail+f"\nمقصد واریز: {r['payment_destination']}\nعکس رسید را با شماره {oid} در کپشن ارسال کنید.")
        elif r["status"] in ("paid","done"):
            await q.message.answer(detail,reply_markup=keyboard([("دریافت مجدد برای مشتری",f"rs:send:{oid}")]))
        else:
            await q.message.answer(detail)

    @router.callback_query(F.data.regexp(r"^rs:(accept|reject|send):[0-9]+$"))
    async def settle(q):
        _,action,raw=q.data.split(":")
        oid=int(raw)
        if action!="send" and q.from_user.id!=owner:
            await q.answer("دسترسی غیرمجاز")
            return
        if action=="send":
            rows=await records("SELECT * FROM agency_retail_orders WHERE id=:id AND bot_id=:bot AND status IN ('paid','done') AND (customer=:viewer OR :viewer=:owner)",id=oid,viewer=q.from_user.id,owner=owner)
        else:
            rows=await records("UPDATE agency_retail_orders SET status=:status WHERE id=:id AND bot_id=:bot AND status='review' RETURNING *",id=oid,status="paid" if action=="accept" else "rejected")
        if not rows:
            await q.answer("وضعیت سفارش تغییر کرده است.")
            return
        await q.answer()
        r=rows[0]
        if action=="reject":
            await q.bot.send_message(r["customer"],f"رسید سفارش {oid} رد شد.")
            return
        ref=f"retail:{bot_id}:{oid}"
        try:
            service=await reserve(ref,bot_id,owner,r["customer"],r["gb"],int(read_setting("agency_inbound","0")),r["days"])
            base=read_setting(f"agency_subscription:{service['inbound_id']}")
            if not base:
                raise ValueError
            await provision(service)
            await q.bot.send_message(r["customer"],f"اشتراک سفارش {oid}\n{base.rstrip('/')}/{service['subscription']}")
        except Exception:
            await q.message.answer("پرداخت ثبت شده است. پس از بررسی حجم، اتصال پنل و دسترسی مشتری، تحویل را دوباره انجام دهید.",reply_markup=keyboard([("تلاش مجدد",f"rs:send:{oid}")]))
            return
        changed=await records("UPDATE agency_retail_orders SET status='done' WHERE bot_id=:bot AND id=:id AND status='paid' RETURNING id",id=oid)
        if changed:
            with closing(connection()) as db:
                dest=db.execute("SELECT chat_id FROM agency_tokens WHERE owner=? AND bot_id=?",(owner,bot_id)).fetchone()
            if dest:
                try:
                    await q.bot.send_message(dest[0],f"فروش سفارش {oid} · {r['price']:,} تومان · {r['gb']} گیگ · تحویل شد.")
                except TelegramAPIError:
                    await q.message.answer("تحویل انجام شد. ارسال گزارش به چت ثبت‌شده ناموفق بود.")
