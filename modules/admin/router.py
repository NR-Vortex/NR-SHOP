from uuid import uuid4
from html import escape
from modules.admin.keyboards import admin_finance_keyboard
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import func, or_, select
from database.models import Category, Order, Product, Referral, Wallet
from database.session import async_session
from modules.checkout.admin_review import is_admin
from modules.admin.keyboards import admin_dashboard_keyboard, admin_users_keyboard
from modules.admin.keyboards import admin_reports_keyboard
from datetime import datetime, timedelta, timezone
from modules.wallet.service import credit_wallet, debit_wallet
from modules.users.service import set_blocked

router = Router(name="admin_dashboard")

@router.message(Command("admin"))
async def open_admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("دسترسی غیرمجاز")
        return

    await message.answer(
        "⚙️ <b>داشبورد مدیریت NR SHOP</b>\n\nبخش موردنظر را انتخاب کنید.",
        reply_markup=admin_dashboard_keyboard()
    )


class AdminUserStates(StatesGroup):
    search = State()
    amount = State()
    reason = State()
    block_reason = State()
    finance_confirm = State()
    broadcast_text = State()

@router.callback_query(F.data.in_({"admin:dashboard", "admin:menu"}))
async def dashboard(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await state.clear()
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("⚙️ <b>داشبورد مدیریت NR SHOP</b>\n\nلطفاً بخش موردنظر را انتخاب کنید:", reply_markup=admin_dashboard_keyboard())

@router.callback_query(F.data == "admin:section:users")
async def users_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("👥 <b>مدیریت کاربران</b>", reply_markup=admin_users_keyboard())

@router.callback_query(F.data == "admin:users:search")
async def user_search_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await state.set_state(AdminUserStates.search); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("🔎 Telegram ID، username، نام یا شماره تلفن کاربر را ارسال کنید:")

@router.message(AdminUserStates.search)
async def user_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    query = (message.text or "").strip()
    if not query or (query.isdecimal() and (len(query) > 19 or int(query) >= 2**63)):
        await message.answer("نام یا شناسه معتبر ارسال کنید.")
        return
    async with async_session() as session:
        from database.models import User
        if query.isdecimal(): stmt = select(User).where(User.telegram_id == int(query))
        elif query.startswith("@"): stmt = select(User).where(User.username.ilike(query[1:]))
        else: stmt = select(User).where(or_(User.full_name.ilike(f"%{query}%"), User.phone.ilike(f"%{query}%"), User.username.ilike(f"%{query}%")))
        user = (await session.execute(stmt)).scalars().first()
        user_id = user.telegram_id if user else None
        wallet = (await session.execute(select(Wallet).where(Wallet.telegram_user_id == user_id))).scalar_one_or_none() if user_id else None
        orders = (await session.execute(select(func.count(Order.id)).where(Order.telegram_user_id == user_id))).scalar_one()
        referrals = (await session.execute(select(func.count(Referral.id)).where(Referral.referrer_user_id == user_id))).scalar_one()
    await state.clear()
    if not user_id: await message.answer("کاربر پیدا نشد."); return
    status = "🚫 مسدود" if user and user.is_blocked else "🟢 فعال"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 شارژ", callback_data=f"admin:user:credit:{user_id}"), InlineKeyboardButton(text="➖ کسر", callback_data=f"admin:user:debit:{user_id}")], [InlineKeyboardButton(text="📦 سفارش‌ها", callback_data=f"admin:user:orders:{user_id}"), InlineKeyboardButton(text="👥 زیرمجموعه‌ها", callback_data=f"admin:user:referrals:{user_id}")], [InlineKeyboardButton(text="📜 تراکنش‌ها", callback_data=f"admin:user:transactions:{user_id}")], [InlineKeyboardButton(text="🚫 مسدود کردن" if not user or not user.is_blocked else "🟢 آزاد کردن", callback_data=f"admin:user:block:{user_id}" if not user or not user.is_blocked else f"admin:user:unblock:{user_id}")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:section:users")]])
    await message.answer(f"👤 <b>اطلاعات کاربر</b>\n\n🆔 شناسه: <code>{user_id}</code>\n👤 نام: {escape(user.full_name or '') if user else 'ثبت نشده'}\n📱 آیدی: @{user.username if user and user.username else 'ثبت نشده'}\n💰 موجودی: {(wallet.balance if wallet else 0):,} تومان\n📦 سفارش‌ها: {orders}\n👥 دعوت‌شدگان: {referrals}\n\nوضعیت: {status}", reply_markup=kb)

@router.callback_query(F.data.startswith("admin:user:credit:"))
@router.callback_query(F.data.startswith("admin:user:debit:"))
async def wallet_operation_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    kind, user_id = callback.data.split(":")[-2:]
    await state.update_data(operation_id=uuid4().hex, wallet_kind=kind, wallet_user_id=int(user_id)); await state.set_state(AdminUserStates.amount); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("مبلغ را به تومان ارسال کنید:")

@router.message(AdminUserStates.amount)
async def wallet_amount(message: Message, state: FSMContext):
    try: amount = int((message.text or "").replace(",", "").strip())
    except ValueError: await message.answer("مبلغ معتبر نیست."); return
    if not 0 < amount < 2**63: await message.answer("مبلغ باید مثبت باشد."); return
    await state.update_data(amount=amount); await state.set_state(AdminUserStates.reason); await message.answer("علت عملیات را ارسال کنید:")

@router.message(AdminUserStates.reason)
async def wallet_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(finance_reason=(message.text or "").strip()); await state.set_state(AdminUserStates.finance_confirm)
    await message.answer(f"⚠️ تأیید نهایی؟\n\nعملیات: {'شارژ' if data['wallet_kind']=='credit' else 'کسر'}\nمبلغ: {data['amount']:,} تومان\nعلت: {escape(message.text or '')}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ تأیید", callback_data=f"admin:finance:confirm:{data['operation_id']}"), InlineKeyboardButton(text="❌ لغو", callback_data="admin:finance:cancel")]]))

@router.callback_query(F.data.startswith("admin:finance:confirm:"))
async def wallet_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    data = await state.get_data()
    if data.get("operation_id") != callback.data.rsplit(":", 1)[-1] or await state.get_state() != AdminUserStates.finance_confirm.state:
        await callback.answer("این درخواست منقضی شده است.", show_alert=True)
        return
    async with async_session() as session:
        try:
            fn = credit_wallet if data["wallet_kind"] == "credit" else debit_wallet
            tx, created = await fn(session, data["wallet_user_id"], data["amount"], f"admin:{data['operation_id']}", data['finance_reason'])
        except ValueError as exc: await callback.answer(str(exc), show_alert=True); return
    await state.clear()
    await callback.answer("✅ عملیات ثبت شد." if created else "⚠️ قبلاً ثبت شده است.", show_alert=True)

@router.callback_query(F.data == "admin:finance:cancel")
async def wallet_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear(); await callback.answer("لغو شد.", show_alert=True)

@router.callback_query(F.data.startswith("admin:user:orders:"))
async def user_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    uid = int(callback.data.rsplit(":", 1)[-1])
    async with async_session() as session: rows = (await session.execute(select(Order).where(Order.telegram_user_id == uid).order_by(Order.id.desc()).limit(20))).scalars().all()
    await callback.answer(); text = "📦 <b>سفارش‌های کاربر</b>\n\n" + ("\n".join(f"{o.order_number} | {o.product_name} | {o.status}" for o in rows) or "سفارشی وجود ندارد.")
    if isinstance(callback.message, Message): await callback.message.edit_text(text, reply_markup=admin_users_keyboard())

@router.callback_query(F.data.startswith("admin:user:referrals:"))
async def user_referrals(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    uid = int(callback.data.rsplit(":", 1)[-1])
    async with async_session() as session: rows = (await session.execute(select(Referral.referred_user_id).where(Referral.referrer_user_id == uid))).scalars().all()
    await callback.answer(); text = "👥 <b>زیرمجموعه‌ها</b>\n\n" + ("\n".join(f"• <code>{x}</code>" for x in rows) or "موردی وجود ندارد.")
    if isinstance(callback.message, Message): await callback.message.edit_text(text, reply_markup=admin_users_keyboard())

@router.callback_query(F.data.startswith("admin:user:transactions:"))
async def user_transactions(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    uid = int(callback.data.rsplit(":", 1)[-1])
    from database.models import WalletTransaction
    async with async_session() as session:
        rows = (await session.execute(select(WalletTransaction).join(Wallet).where(Wallet.telegram_user_id == uid).order_by(WalletTransaction.id.desc()).limit(30))).scalars().all()
    await callback.answer(); text = "📜 <b>تراکنش‌های کاربر</b>\n\n" + ("\n".join(f"{'➕' if x.kind == 'credit' else '➖'} {x.amount:,} | {x.description or '-'}" for x in rows) or "تراکنشی وجود ندارد.")
    if isinstance(callback.message, Message): await callback.message.edit_text(text, reply_markup=admin_users_keyboard())

@router.callback_query(F.data.startswith("admin:user:block:"))
async def block_user_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await state.update_data(block_user_id=int(callback.data.rsplit(":", 1)[-1])); await state.set_state(AdminUserStates.block_reason); await callback.answer(); await callback.message.answer("دلیل مسدودسازی را ارسال کنید:")

@router.message(AdminUserStates.block_reason)
async def block_user_reason(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    reason = (message.text or "").strip()
    if not reason:
        await message.answer("دلیل مسدودسازی را به صورت متن بفرستید.")
        return
    data = await state.get_data()
    async with async_session() as session:
        await set_blocked(session, data["block_user_id"], message.from_user.id, True, reason)
    await state.clear()
    await message.answer("🚫 کاربر مسدود شد.")

@router.callback_query(F.data.startswith("admin:user:unblock:"))
async def unblock_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session: await set_blocked(session, int(callback.data.rsplit(":", 1)[-1]), callback.from_user.id, False)
    await callback.answer("کاربر آزاد شد.", show_alert=True)

@router.callback_query(F.data == "admin:users:stats")
async def users_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session:
        wallets = (await session.execute(select(func.count(Wallet.id)))).scalar_one(); orders = (await session.execute(select(func.count(Order.id)))).scalar_one(); referrals = (await session.execute(select(func.count(Referral.id)))).scalar_one()
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"📊 <b>آمار کاربران</b>\n\n👤 کاربران دارای کیف پول: {wallets}\n📦 سفارش‌ها: {orders}\n👥 دعوت‌ها: {referrals}", reply_markup=admin_users_keyboard())

@router.callback_query(F.data == "admin:users:list")
@router.callback_query(F.data.regexp(r"^admin:users:list:[0-9]{1,8}$"))
async def users_list(callback: CallbackQuery):
    from database.models import User
    from modules.admin.operations import buttons
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی غیرمجاز", show_alert=True)
        return
    page = int(callback.data.split(":")[3]) if callback.data.count(":") == 3 else 0
    known = select(User.telegram_id).union(select(Wallet.telegram_user_id), select(Order.telegram_user_id)).subquery()
    async with async_session() as session:
        ids = (await session.scalars(select(known.c.telegram_id).order_by(known.c.telegram_id.desc()).offset(page * 25).limit(26))).all()
    entries = []
    if page:
        entries.append(("قبلی", f"admin:users:list:{page-1}"))
    if len(ids) > 25:
        entries.append(("بعدی", f"admin:users:list:{page+1}"))
    entries.append(("بازگشت", "admin:section:users"))
    await callback.answer()
    await callback.message.edit_text(f"کاربران · صفحه {page+1}\n" + ("\n".join(map(str, ids[:25])) or "کاربری ثبت نشده است."), reply_markup=buttons(entries))

@router.callback_query(F.data == "admin:section:reports")
async def reports_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📊 <b>گزارش‌های NR SHOP</b>", reply_markup=admin_reports_keyboard())

@router.callback_query(F.data == "admin:reports:sales")
async def sales_report(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    now = datetime.now(timezone.utc); day = now - timedelta(days=1); week = now - timedelta(days=7); month = now - timedelta(days=30)
    async with async_session() as session:
        paid = Order.status.in_(["paid", "provisioning"])
        total = (await session.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.final_amount), 0)).where(paid))).one()
        undated = await session.scalar(select(func.count(Order.id)).where(paid, Order.paid_at.is_(None)))
        daily = (await session.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.final_amount), 0)).where(paid, Order.paid_at >= day))).one()
        weekly = (await session.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.final_amount), 0)).where(paid, Order.paid_at >= week))).one()
        monthly = (await session.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.final_amount), 0)).where(paid, Order.paid_at >= month))).one()
        ai = (await session.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).join(Product, Product.id == Order.product_id).join(Category, Category.id == Product.category_id).where(paid, Category.section == "ai"))).scalar_one()
        vpn = (await session.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).join(Product, Product.id == Order.product_id).join(Category, Category.id == Product.category_id).where(paid, Category.section == "vpn"))).scalar_one()
    await callback.answer()
    text = f"💰 <b>گزارش فروش</b>\n\nکل سفارش‌های موفق: {total[0]}\nکل درآمد: {total[1]:,} تومان\n\n📅 ۲۴ ساعت اخیر: {daily[0]} سفارش | {daily[1]:,} تومان\n📅 ۷ روز اخیر: {weekly[0]} سفارش | {weekly[1]:,} تومان\n📅 ۳۰ روز اخیر: {monthly[0]} سفارش | {monthly[1]:,} تومان\n\n🤖 فروش AI: {ai:,} تومان\n🌐 فروش VPN: {vpn:,} تومان"
    if undated:
        text += f"\n{undated} سفارش قدیمی زمان پرداخت ثبت‌شده ندارند و فقط در جمع کل لحاظ شده‌اند."
    if isinstance(callback.message, Message): await callback.message.edit_text(text, reply_markup=admin_reports_keyboard())

@router.callback_query(F.data == "admin:reports:users")
async def users_report(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    now = datetime.now(timezone.utc)
    from database.models import User
    async with async_session() as session:
        total = (await session.execute(select(func.count(User.id)))).scalar_one(); blocked = (await session.execute(select(func.count(User.id)).where(User.is_blocked.is_(True)))).scalar_one(); today = (await session.execute(select(func.count(User.id)).where(User.created_at >= now - timedelta(days=1)))).scalar_one(); week = (await session.execute(select(func.count(User.id)).where(User.created_at >= now - timedelta(days=7)))).scalar_one(); month = (await session.execute(select(func.count(User.id)).where(User.created_at >= now - timedelta(days=30)))).scalar_one()
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"👥 <b>گزارش کاربران</b>\n\nکل کاربران: {total}\nکاربران مسدود: {blocked}\nکاربران جدید امروز: {today}\nهفته اخیر: {week}\nماه اخیر: {month}", reply_markup=admin_reports_keyboard())

@router.callback_query(F.data == "admin:section:ai")
async def ai_admin_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_ai_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("🤖 <b>مدیریت بخش هوش مصنوعی</b>", reply_markup=admin_ai_keyboard())

@router.callback_query(F.data == "admin:section:finance")
async def finance_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_finance_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("💰 <b>مدیریت مالی NR SHOP</b>", reply_markup=admin_finance_keyboard())

@router.callback_query(F.data == "admin:section:gifts")
async def gifts_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_gifts_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("🎁 <b>هدایا، تخفیف و Referral</b>", reply_markup=admin_gifts_keyboard())

@router.callback_query(F.data == "admin:gifts:coupons")
async def coupons_report(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from database.models import Coupon, CouponUsage
    async with async_session() as session:
        total = (await session.execute(select(func.count(Coupon.id)))).scalar_one(); active = (await session.execute(select(func.count(Coupon.id)).where(Coupon.is_active.is_(True)))).scalar_one(); used = (await session.execute(select(func.count(CouponUsage.id)))).scalar_one()
    from modules.admin.keyboards import admin_gifts_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"🎟 <b>گزارش کدهای تخفیف</b>\n\nکل کدها: {total}\nکدهای فعال: {active}\nتعداد مصرف: {used}", reply_markup=admin_gifts_keyboard())

@router.callback_query(F.data == "admin:gifts:referral")
async def referral_report(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session: total = (await session.execute(select(func.count(Referral.id)))).scalar_one()
    from modules.admin.keyboards import admin_gifts_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"👥 <b>آمار Referral</b>\n\nکل دعوت‌های ثبت‌شده: {total}\n\nاین آمار مشترک بین AI و VPN است.", reply_markup=admin_gifts_keyboard())

@router.callback_query(F.data == "admin:section:database")
async def database_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_database_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("🗄 <b>مدیریت دیتابیس</b>", reply_markup=admin_database_keyboard())

@router.callback_query(F.data == "admin:database:health")
async def database_health(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from sqlalchemy import text
    from modules.admin.keyboards import admin_database_keyboard
    try:
        async with async_session() as session: await session.execute(text("SELECT 1"))
        status = "🟢 اتصال دیتابیس سالم است."
    except Exception: status = "🔴 اتصال دیتابیس برقرار نیست."
    await callback.answer();
    if isinstance(callback.message, Message): await callback.message.edit_text(status, reply_markup=admin_database_keyboard())

@router.callback_query(F.data == "admin:database:stats")
async def database_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_database_keyboard
    async with async_session() as session:
        users = (await session.execute(select(func.count(Wallet.id)))).scalar_one(); orders = (await session.execute(select(func.count(Order.id)))).scalar_one(); wallets = (await session.execute(select(func.count(Wallet.id)))).scalar_one()
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"📊 <b>آمار دیتابیس</b>\n\nکاربران دارای کیف پول: {users}\nسفارش‌ها: {orders}\nکیف پول‌ها: {wallets}", reply_markup=admin_database_keyboard())

@router.callback_query(F.data == "admin:section:settings")
async def settings_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_settings_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("⚙️ <b>تنظیمات ربات</b>\n\nوضعیت بخش‌ها:", reply_markup=admin_settings_keyboard())

@router.callback_query(F.data == "admin:section:broadcast")
async def broadcast_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_broadcast_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📢 <b>پیام همگانی</b>", reply_markup=admin_broadcast_keyboard())

@router.callback_query(F.data == "admin:section:guides")
async def guides_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_guides_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📚 <b>مدیریت راهنما</b>\n\nمحتوای آموزشی فقط پس از ثبت واقعی نمایش داده می‌شود.", reply_markup=admin_guides_keyboard())

@router.callback_query(F.data == "admin:section:texts")
async def texts_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_texts_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📝 <b>مدیریت متن‌های ربات</b>", reply_markup=admin_texts_keyboard())

@router.callback_query(F.data == "admin:section:ads")
async def ads_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from modules.admin.keyboards import admin_ads_keyboard
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📣 <b>تبلیغات و عضویت اجباری</b>", reply_markup=admin_ads_keyboard())

@router.callback_query(F.data.in_({"admin:broadcast:text", "admin:ads:campaigns"}))
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await state.set_state(AdminUserStates.broadcast_text); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("متن پیام همگانی را ارسال کنید یا /cancel بزنید:")

@router.message(AdminUserStates.broadcast_text)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    if message.text == "/cancel": await state.clear(); await message.answer("ارسال لغو شد."); return
    from database.models import User
    async with async_session() as session: users = (await session.execute(select(User.telegram_id).where(User.is_blocked.is_(False)))).scalars().all()
    sent = failed = 0
    for user_id in users:
        try: await message.bot.send_message(user_id, message.text); sent += 1
        except Exception: failed += 1
    await state.clear(); await message.answer(f"✅ پیام همگانی پایان یافت.\n\nارسال موفق: {sent}\nناموفق: {failed}")

@router.callback_query(F.data.startswith("admin:settings:feature:"))
async def feature_toggle(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from core.features import FEATURES, set_feature
    feature = callback.data.rsplit(":", 1)[-1]
    if feature not in FEATURES: await callback.answer("قابلیت نامعتبر است.", show_alert=True); return
    set_feature(feature, not FEATURES[feature])
    await callback.answer("فعال شد." if FEATURES[feature] else "غیرفعال شد.", show_alert=True)
    from modules.admin.keyboards import admin_settings_keyboard
    await callback.message.edit_reply_markup(reply_markup=admin_settings_keyboard())

@router.callback_query(F.data == "admin:finance:wallets")
async def finance_wallets(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session:
        wallets = (await session.execute(select(func.count(Wallet.id), func.coalesce(func.sum(Wallet.balance), 0)))).one()
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"🪙 <b>کیف پول‌ها</b>\n\nتعداد کیف پول: {wallets[0]}\nمجموع موجودی: {wallets[1]:,} تومان", reply_markup=admin_finance_keyboard())

@router.callback_query(F.data == "admin:finance:transactions")
async def finance_transactions(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    from database.models import WalletTransaction
    async with async_session() as session:
        rows = (await session.execute(select(func.count(WalletTransaction.id), func.coalesce(func.sum(WalletTransaction.amount), 0)))).one()
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"📜 <b>تراکنش‌های کیف پول</b>\n\nتعداد تراکنش‌ها: {rows[0]}\nمجموع گردش ثبت‌شده: {rows[1]:,} تومان", reply_markup=admin_finance_keyboard())

@router.callback_query(F.data.startswith("admin:section:"))
async def section_placeholder(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await callback.answer("🚧 این بخش به‌زودی راه‌اندازی خواهد شد.", show_alert=True)
