from core.admin_settings import representative_db
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.models import Category, Product
from database.models.product_group import ProductGroup
from database.session import async_session
from modules.admin.operations import buttons
from modules.checkout.admin_review import is_admin

router = Router(name="admin_catalog")
router.callback_query.filter(F.from_user.id.func(is_admin))
router.message.filter(F.from_user.id.func(is_admin))
MODELS = {"categories": Category, "groups": ProductGroup, "products": Product}
TITLES = {"categories": "دسته‌ها", "groups": "گروه‌ها", "products": "محصولات"}


class Form(StatesGroup):
    catalog = State()
    representative = State()


def records(kind, *, archived=False):
    model = MODELS[kind]
    query = select(model)
    if model is not Category:
        query = query.join(Category, model.category_id == Category.id)
    if kind=="products":
        query=query.where(Product.archived_at.is_not(None) if archived else Product.archived_at.is_(None))
    return query.where(Category.section == "ai")


@router.callback_query(F.data.in_({f"admin:ai:{kind}" for kind in MODELS}))
@router.callback_query(F.data.startswith("cat:list:"))
async def listing(callback, state):
    await state.clear()
    parts = callback.data.split(":")
    kind = parts[2]
    page = int(parts[3]) if len(parts) == 4 else 0
    async with async_session() as session:
        rows = (await session.scalars(records(kind).order_by(MODELS[kind].id).offset(page * 12).limit(13))).all()
    entries = [(f"{'🟢' if x.is_active else '⚪'} {x.id} · {x.name[:45]}", f"cat:edit:{kind}:{x.id}") for x in rows[:12]]
    if page:
        entries.append(("قبلی", f"cat:list:{kind}:{page-1}"))
    if len(rows) > 12:
        entries.append(("بعدی", f"cat:list:{kind}:{page+1}"))
    entries.append(("افزودن", f"cat:edit:{kind}:0"))
    if kind=="products":
        entries.append(("آرشیو محصولات","cat:archive:0"))
    entries.append(("بازگشت","admin:section:ai"))
    await callback.answer()
    title=TITLES[kind] + (" · برای ویرایش یک مورد را انتخاب کنید." if rows else " · هنوز موردی ثبت نشده است.")
    await callback.message.edit_text(title, reply_markup=buttons(entries))


@router.callback_query(F.data.regexp(r"^cat:archive:[0-9]{1,8}$"))
async def archive_list(callback,state):
    await state.clear()
    page=int(callback.data.rsplit(":",1)[1])
    async with async_session() as session:
        rows=(await session.scalars(records("products",archived=True).order_by(Product.id)
            .offset(page*12).limit(13))).all()
    entries=[(f"بازگردانی · {item.name[:55]}",f"cat:restore:{item.id}") for item in rows[:12]]
    if page:
        entries.append(("قبلی",f"cat:archive:{page-1}"))
    if len(rows)>12:
        entries.append(("بعدی",f"cat:archive:{page+1}"))
    entries.append(("بازگشت به محصولات","admin:ai:products"))
    await callback.answer()
    await callback.message.edit_text("آرشیو محصولات AI" if rows else "آرشیو خالی است.",reply_markup=buttons(entries))


@router.callback_query(F.data.regexp(r"^cat:restore:[0-9]{1,10}$"))
async def restore_product(callback,state):
    await state.clear()
    product_id=int(callback.data.rsplit(":",1)[1])
    if product_id>2**31-1:
        await callback.answer("محصول پیدا نشد.",show_alert=True)
        return
    async with async_session.begin() as session:
        product=await session.scalar(records("products",archived=True).where(Product.id==product_id).with_for_update(of=Product))
        if product is None:
            await callback.answer("محصول آرشیوشده پیدا نشد.",show_alert=True)
            return
        product.archived_at=None
    await callback.answer("محصول در حالت غیرفعال به فهرست برگشت.")
    await callback.message.edit_text("محصول به فهرست برگشت. برای فروش دوباره، وضعیتش را از همان فهرست فعال کن.",
        reply_markup=buttons([("محصولات","admin:ai:products"),("آرشیو","cat:archive:0")]))



FIELDS = {
    "categories": ["نام", "وضعیت (۱ فعال، ۰ غیرفعال)"],
    "groups": ["شناسه دسته", "نام", "وضعیت (۱ یا ۰)"],
    "products": ["شناسه دسته", "شناسه گروه (۰ برای بدون گروه)", "نام", "قیمت به تومان", "نوع حساب (shared یا dedicated)", "وضعیت (۱ یا ۰)"],
}


@router.callback_query(F.data.startswith("cat:edit:"))
async def start(callback, state):
    _, _, kind, raw_id = callback.data.split(":")
    item_id = int(raw_id)
    values = []
    if item_id:
        async with async_session() as session:
            item = await session.scalar(records(kind).where(MODELS[kind].id == item_id))
        if item is None:
            await callback.answer("مورد پیدا نشد.", show_alert=True)
            return
        if kind != "categories":
            values.append(item.category_id)
        if kind == "products":
            values.append(item.group_id or 0)
        values.append(item.name)
        if kind == "products":
            values.extend([item.price, item.account_type])
        values.append(int(item.is_active))
    await state.set_state(Form.catalog)
    await state.update_data(kind=kind, item_id=item_id)
    prompt = "هر مقدار را در یک خط بفرستید، به ترتیب زیر. برای لغو /cancel را بفرستید.\n" + "\n".join(FIELDS[kind])
    if values:
        prompt += "\n\nمقادیر فعلی\n<pre>" + escape("\n".join(map(str, values))) + "</pre>"
    await callback.answer()
    await callback.message.answer(prompt)


def number(value, maximum):
    if not value.isdecimal() or len(value) > 19 or int(value) > maximum:
        raise ValueError("مقدار عددی نامعتبر است.")
    return int(value)


def parse(kind, text):
    parts = [line.strip() for line in text.strip().splitlines()]
    if len(parts) != len(FIELDS[kind]):
        raise ValueError("تعداد خط‌ها با فرم مطابقت ندارد.")
    result = {"is_active": bool(number(parts.pop(), 1))}
    if kind != "categories":
        result["category_id"] = number(parts.pop(0), 2**31-1)
    if kind == "products":
        result["group_id"] = number(parts.pop(0), 2**31-1) or None
        result["account_type"] = parts.pop()
        if result["account_type"] not in {"shared", "dedicated"}:
            raise ValueError("نوع حساب نامعتبر است.")
        result["price"] = number(parts.pop(), 2**63-1)
    name = parts.pop()
    if not name or len(name) > MODELS[kind].name.type.length:
        raise ValueError("طول نام معتبر نیست.")
    result["name"] = name
    return result


@router.message(Form.catalog, Command("cancel"))
@router.message(Form.representative, Command("cancel"))
async def cancel(message, state):
    await state.clear()
    await message.answer("لغو شد.", reply_markup=buttons([("داشبورد", "admin:dashboard")]))


@router.message(Form.catalog, F.text, ~F.text.startswith("/"))
async def save_catalog(message, state):
    data = await state.get_data()
    kind, item_id = data["kind"], data["item_id"]
    model = MODELS[kind]
    try:
        fields = parse(kind, message.text)
        async with async_session.begin() as session:
            if kind != "categories" and not await session.scalar(records("categories").where(Category.id == fields["category_id"])):
                raise ValueError("شناسه دسته AI پیدا نشد.")
            if fields.get("group_id") and not await session.scalar(select(ProductGroup.id).where(ProductGroup.id == fields["group_id"], ProductGroup.category_id == fields["category_id"])):
                raise ValueError("گروه به این دسته تعلق ندارد.")
            if item_id:
                item = await session.scalar(records(kind).where(model.id == item_id).with_for_update())
                if item is None:
                    raise ValueError("مورد پیدا نشد.")
                if kind == "groups" and item.category_id != fields["category_id"] and await session.scalar(select(Product.id).where(Product.group_id == item.id).limit(1)):
                    raise ValueError("ابتدا محصولات گروه را منتقل کنید.")
                for key, value in fields.items():
                    setattr(item, key, value)
            else:
                if kind == "categories":
                    fields["section"] = "ai"
                session.add(model(**fields))
    except ValueError as exc:
        await message.answer(str(exc))
        return
    except IntegrityError:
        await message.answer("نام تکراری است یا اطلاعات وابسته تغییر کرده است.")
        return
    await state.clear()
    await message.answer("ذخیره شد.", reply_markup=buttons([("بازگشت به فهرست", f"admin:ai:{kind}")]))

@router.callback_query(F.data == "admin:section:representatives")
@router.callback_query(F.data.startswith("rep:list:"))
async def representatives(callback, state):
    from contextlib import closing
    from core.admin_settings import read_setting
    await state.clear()
    page = int(callback.data.split(":")[-1]) if callback.data.startswith("rep:") else 0
    with closing(representative_db()) as db:
        rows = db.execute("SELECT telegram_id,name,active FROM representatives ORDER BY telegram_id LIMIT 13 OFFSET ?", (12*page,)).fetchall()
    entries = [(f"{'🟢' if active else '⚪'} {name}", f"rep:edit:{uid}") for uid,name,active in rows[:12]]
    if page:
        entries.append(("قبلی", f"rep:list:{page-1}"))
    if len(rows)>12:
        entries.append(("بعدی", f"rep:list:{page+1}"))
    entries.extend([("ثبت نماینده", "rep:edit:0"), ("داشبورد", "admin:dashboard")])
    legacy = read_setting("section:representatives","")
    await callback.answer()
    await callback.message.edit_text("مدیریت نمایندگان" + ("\n\nیادداشت قبلی\n"+escape(legacy) if legacy else ""),reply_markup=buttons(entries))


@router.callback_query(F.data.startswith("rep:edit:"))
async def rep_edit(callback,state):
    from contextlib import closing
    uid = int(callback.data.split(":")[-1])
    with closing(representative_db()) as db:
        row = db.execute("SELECT telegram_id,name,bot,active FROM representatives WHERE telegram_id=?", (uid,)).fetchone()
    await state.set_state(Form.representative)
    await state.update_data(rep_id=uid)
    await callback.answer()
    prompt = "در چهار خط بفرستید\nشناسه تلگرام نماینده\nنام نماینده\nنام کاربری ربات نمایندگی یا -\nوضعیت (۱ فعال، ۰ غیرفعال)\nلغو با /cancel"
    if row:
        prompt += "\n<pre>"+escape("\n".join(map(str,row)))+"</pre>"
    await callback.message.answer(prompt)


@router.message(Form.representative, F.text, ~F.text.startswith("/"))
async def rep_save(message,state):
    from contextlib import closing
    from sqlite3 import IntegrityError as Duplicate
    import re
    parts = [s.strip() for s in message.text.strip().splitlines()]
    original = (await state.get_data())["rep_id"]
    try:
        if len(parts)!=4:
            raise ValueError("چهار خط لازم است.")
        uid = number(parts[0],2**63-1)
        active = number(parts[3],1)
        if not uid or original and uid!=original:
            raise ValueError("شناسه معتبر نیست یا تغییر کرده است.")
        if not 0<len(parts[1])<=80 or parts[2]!="-" and not re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{1,27}bot",parts[2], re.I):
            raise ValueError("نام نماینده یا شناسه ربات معتبر نیست.")
        with closing(representative_db()) as db, db:
            if original:
                db.execute("UPDATE representatives SET name=?,bot=?,active=? WHERE telegram_id=?", (parts[1],parts[2],active,uid))
            else:
                db.execute("INSERT INTO representatives VALUES (?,?,?,?)",(uid,parts[1],parts[2],active))
    except ValueError as exc:
        await message.answer(str(exc))
        return
    except Duplicate:
        await message.answer("نماینده قبلاً ثبت شده است. از فهرست ویرایش کنید.")
        return
    await state.clear()
    await message.answer("نماینده ذخیره شد.",reply_markup=buttons([("نمایندگان","admin:section:representatives")]))
