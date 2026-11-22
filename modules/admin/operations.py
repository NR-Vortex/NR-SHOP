import sqlite3
import zipfile
from contextlib import closing
import asyncio
import os
import re
import secrets
import tempfile
from html import escape
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from core.admin_settings import read_setting, write_setting
from database.models import Category, Order, Product
from database.models.ai_delivery import AICodeRequest
from database.models.coupon import Coupon
from database.models.product_group import ProductGroup
from database.session import DATABASE_URL, async_session
from modules.checkout.admin_review import admin_order_keyboard, is_admin

router = Router(name="admin_operations")
router.message.filter(F.from_user.id.func(is_admin))
router.callback_query.filter(F.from_user.id.func(is_admin))


class Edit(StatesGroup):
    value = State()


def buttons(entries):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=action)] for label, action in entries
    ])


@router.callback_query(F.data.in_({"admin:guides:add", "admin:ai:tutorials"}))
async def choose_guide(callback):
    await callback.answer()
    await callback.message.edit_text("راهنمای کدام بخش را ویرایش می‌کنید؟", reply_markup=buttons([
        ("هوش مصنوعی", "admin:guides:ai"), ("VPN", "admin:guides:vpn"), ("بازگشت", "admin:dashboard")
    ]))


@router.callback_query(F.data.startswith("admin:texts:"))
@router.callback_query(F.data.in_({"admin:guides:ai", "admin:guides:vpn", "admin:ads:channels", "admin:gifts:gift", "admin:section:agency_panel", "admin:section:agency_bot", "admin:section:representatives"}))
async def edit_start(callback, state):
    key = callback.data.removeprefix("admin:")
    prompt = "متن جدید را بفرستید."
    if key.startswith("section:agency_"):
        prompt = "متن معرفی و روش دسترسی نمایندگی را برای نمایش به مشتری وارد کنید."
    elif key == "section:representatives":
        prompt = "فهرست داخلی نمایندگان را وارد کنید."
    elif key == "ads:channels":
        prompt = "شناسه عمومی کانال‌ها را با فاصله بفرستید، مانند @Nrshopi."
    elif key == "gifts:gift":
        prompt = "مبلغ کد هدیه یک‌بارمصرف خرید را به تومان بفرستید."
    await state.set_state(Edit.value)
    await state.update_data(setting_key=key)
    await callback.answer()
    current = read_setting(key, "@Nrshopi" if key == "ads:channels" else "")
    await callback.message.answer(f"{escape(current)}\n{prompt}\nبرای لغو /cancel را بفرستید.")


@router.message(Edit.value, Command("cancel"))
async def cancel(message, state):
    await state.clear()
    await message.answer("لغو شد.")


@router.message(Edit.value, ~F.text.startswith("/"))
async def save(message, state):
    key = (await state.get_data())["setting_key"]
    value = (message.text or "").strip()
    if not value or len(escape(value)) > 1200:
        await message.answer("متن کوتاه و غیرخالی بفرستید.")
        return
    if key == "ads:channels" and not all(re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{4,31}", item) for item in value.split()):
        await message.answer("شناسه عمومی کانال معتبر نیست.")
        return
    if key == "gifts:gift":
        if not value.isdecimal() or len(value) > 18 or int(value) == 0:
            await message.answer("مبلغ مثبت و معتبر بفرستید.")
            return
        code = "GIFT-" + secrets.token_hex(8).upper()
        async with async_session.begin() as session:
            session.add(Coupon(code=code, discount_type="fixed", discount_value=int(value), usage_limit=1))
        result = f"کد هدیه خرید ساخته شد: <code>{code}</code>"
    else:
        write_setting(key, value)
        result = "ذخیره شد."
    await state.clear()
    await message.answer(result, reply_markup=buttons([("داشبورد", "admin:dashboard")]))


@router.callback_query(F.data == "admin:ads:force_join")
async def toggle_join(callback):
    enabled = read_setting("join_enabled", "1") != "1"
    write_setting("join_enabled", str(int(enabled)))
    await callback.answer("عضویت اجباری فعال شد." if enabled else "عضویت اجباری غیرفعال شد.", show_alert=True)


@router.callback_query(F.data == "admin:finance:payments")
@router.callback_query(F.data.regexp(r"^admin:finance:payments:[0-9]{1,8}$"))
async def payments(callback):
    page = int(callback.data.split(":")[3]) if callback.data.count(":") == 3 else 0
    async with async_session() as session:
        orders = (await session.scalars(select(Order).where(Order.status == "under_review").order_by(Order.id).offset(page * 30).limit(31))).all()
    await callback.answer()
    entries = [(f"{order.order_number} | {order.final_amount:,} تومان", f"admin:receipt:{order.id}") for order in orders[:30]]
    if page:
        entries.append(("قبلی", f"admin:finance:payments:{page-1}"))
    if len(orders) > 30:
        entries.append(("بعدی", f"admin:finance:payments:{page+1}"))
    await callback.message.edit_text("رسیدهای در انتظار بررسی" if orders else "رسیدی در انتظار بررسی نیست.", reply_markup=buttons(entries + [("بازگشت", "admin:section:finance")]))


@router.callback_query(F.data.startswith("admin:receipt:"))
async def receipt(callback):
    async with async_session() as session:
        order = await session.get(Order, int(callback.data.rsplit(":", 1)[1]))
    if not order or order.status != "under_review" or not order.receipt_file_id:
        await callback.answer("رسید قابل بررسی نیست.", show_alert=True)
        return
    await callback.answer()
    send = callback.message.answer_photo if order.receipt_type == "photo" else callback.message.answer_document
    await send(order.receipt_file_id, caption=f"{escape(order.order_number)} | {order.final_amount:,} تومان", reply_markup=admin_order_keyboard(order.id))


@router.callback_query(F.data.startswith("admin:ai:"))
async def ai_records(callback):
    key = callback.data.rsplit(":", 1)[1]
    queries = {
        "categories": select(Category.name).where(Category.section == "ai"),
        "groups": select(ProductGroup.name).join(Category).where(Category.section == "ai"),
        "products": select(Product.name, Product.price).join(Category).where(Category.section == "ai"),
        "orders": select(Order.order_number, Order.status).join(Product).join(Category).where(Category.section == "ai"),
        "accounts": select(AICodeRequest.order_id, AICodeRequest.status).where(AICodeRequest.status == "pending"),
    }
    async with async_session() as session:
        rows = (await session.execute(queries[key].order_by(1).limit(25))).all()
    entries = [(f"پاسخ به سفارش {row[0]}", f"admin:ai_code:{row[0]}") for row in rows] if key == "accounts" else []
    lines = [" | ".join(escape(str(field))[:100] for field in row) for row in rows]
    await callback.answer()
    await callback.message.edit_text("\n".join(lines) or "موردی ثبت نشده است.", reply_markup=buttons(entries + [("بازگشت", "admin:section:ai")]))


def package_backup(dump):
    from core.admin_settings import STORE
    target = dump.with_suffix(".zip")
    with tempfile.TemporaryDirectory(dir=dump.parent) as staging:
        archive = Path(staging) / "backup.zip"
        snapshot = Path(staging) / "admin_settings.sqlite3"
        with closing(sqlite3.connect(snapshot)) as destination:
            if STORE.exists():
                with closing(sqlite3.connect(STORE)) as source:
                    source.backup(destination)
            else:
                destination.execute("VACUUM")
        with zipfile.ZipFile(archive, "w") as output:
            output.write(dump, "postgres.dump")
            output.write(snapshot, snapshot.name)
        archive.replace(target)
    return target


@router.callback_query(F.data == "admin:database:backup")
async def backup(callback):
    await callback.answer("در حال تهیه بکاپ…")
    from core.admin_settings import DATA_DIR
    directory = DATA_DIR / "backups"
    directory.mkdir(mode=0o700, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=directory, suffix=".partial")
    os.close(fd)
    path = Path(name)
    try:
        proc = await asyncio.create_subprocess_exec(
            "pg_dump", "-Fc", "-w", "-h", DATABASE_URL.host, "-p", str(DATABASE_URL.port),
            "-U", DATABASE_URL.username, "-d", DATABASE_URL.database, "-f", name,
            env={**os.environ, "PGPASSWORD": DATABASE_URL.password}, stderr=asyncio.subprocess.DEVNULL)
        if await proc.wait() or not path.stat().st_size:
            raise OSError
        target = await asyncio.to_thread(package_backup, path)
    except (OSError, sqlite3.Error):
        await callback.message.answer("ساخت بکاپ ناموفق بود. نصب pg_dump، اتصال دیتابیس و دسترسی پوشه backups را بررسی کنید.")
    else:
        await callback.message.answer(f"بکاپ روی سرور ذخیره شد: <code>backups/{target.name}</code>")
    finally:
        path.unlink(missing_ok=True)
