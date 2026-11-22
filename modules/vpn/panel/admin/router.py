from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import delete, select
from html import escape

from database.models import Category, Product, ProductVPNInbound, VPNInbound, VPNPanel, VPNTrialSettings
from database.session import async_session
from modules.checkout.admin_review import get_admin_ids, is_admin
from modules.vpn.panel.client import VPNPanelError
from modules.vpn.panel.service import save_panel, sync_panel_inbounds
from modules.vpn.panel.admin.keyboards import panel_admin_keyboard
from modules.vpn.panel.admin.states import VPNPanelStates
from modules.vpn.provisioning import SUPPORTED_PROTOCOLS
from modules.vpn.trial import get_trial_settings, trial_statistics
from modules.vpn.trial_keyboards import trial_admin_keyboard


router = Router(name="vpn_panel_admin")


def _trial_settings_text(settings):
    return ("🕹️ <b>مدیریت اکانت تست</b>\n\n"
            f"وضعیت: {'🟢 فعال' if settings.is_enabled else '🔴 غیرفعال'}\n"
            f"پنل: {settings.panel_id or 'انتخاب نشده'}\n"
            f"Inbound: {settings.inbound_id or 'انتخاب نشده'}\n"
            f"حجم: {settings.volume_gb} GB\n"
            f"مدت: {settings.duration_hours} ساعت")


@router.callback_query(F.data == "vpnadmin:trial")
async def trial_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session: settings = await get_trial_settings(session)
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(_trial_settings_text(settings), reply_markup=trial_admin_keyboard())


@router.callback_query(F.data == "vpnadmin:trial:settings")
async def trial_settings_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await state.set_state(VPNPanelStates.trial_volume); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("📦 حجم تست را بر حسب GB ارسال کنید (عدد مثبت):")


@router.message(VPNPanelStates.trial_volume)
async def trial_volume(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    try: volume = int(message.text.strip())
    except (AttributeError, ValueError): await message.answer("لطفاً یک عدد صحیح معتبر ارسال کنید."); return
    if volume <= 0: await message.answer("حجم باید بزرگ‌تر از صفر باشد."); return
    await state.update_data(trial_volume=volume); await state.set_state(VPNPanelStates.trial_duration)
    await message.answer("📅 مدت اعتبار تست را بر حسب ساعت ارسال کنید (مثلاً 24):")


@router.message(VPNPanelStates.trial_duration)
async def trial_duration(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    try: duration = int(message.text.strip())
    except (AttributeError, ValueError): await message.answer("لطفاً یک عدد صحیح معتبر ارسال کنید."); return
    if duration <= 0: await message.answer("مدت باید بزرگ‌تر از صفر باشد."); return
    data = await state.get_data()
    async with async_session() as session:
        settings = await get_trial_settings(session)
        settings.volume_gb = data["trial_volume"]; settings.duration_hours = duration
        if settings.id == 1 and settings not in session: session.add(settings)
        await session.commit()
    await state.clear(); await message.answer("✅ حجم و مدت اکانت تست ذخیره شد.")


@router.callback_query(F.data == "vpnadmin:trial:toggle")
async def trial_toggle(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session:
        settings = await get_trial_settings(session); settings.is_enabled = not settings.is_enabled
        if settings.id == 1 and settings not in session: session.add(settings)
        await session.commit()
    await callback.answer("وضعیت اکانت تست تغییر کرد.")
    await trial_menu(callback)


@router.callback_query(F.data == "vpnadmin:trial:panel")
async def trial_panel_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session:
        panels = (await session.execute(select(VPNPanel).where(VPNPanel.is_active.is_(True)).order_by(VPNPanel.id))).scalars().all()
    buttons = [[InlineKeyboardButton(text=p.name, callback_data=f"vpnadmin:trial:setpanel:{p.id}")] for p in panels]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="vpnadmin:trial")])
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("🌐 پنل اکانت تست را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("vpnadmin:trial:setpanel:"))
async def trial_set_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    try: panel_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError: await callback.answer("پنل نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        settings = await get_trial_settings(session)
        panel = await session.get(VPNPanel, panel_id)
        if not panel: await callback.answer("پنل پیدا نشد.", show_alert=True); return
        settings.panel_id = panel.id; settings.inbound_id = None
        if settings.id == 1 and settings not in session: session.add(settings)
        await session.commit()
    await callback.answer("پنل انتخاب شد.")
    await trial_menu(callback)


@router.callback_query(F.data == "vpnadmin:trial:inbound")
async def trial_inbound_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session:
        settings = await get_trial_settings(session)
        if not settings.panel_id:
            await callback.answer("ابتدا یک پنل انتخاب کنید.", show_alert=True); return
        inbounds = (await session.execute(select(VPNInbound).where(VPNInbound.panel_id == settings.panel_id, VPNInbound.enabled.is_(True)).order_by(VPNInbound.id))).scalars().all()
    buttons = [[InlineKeyboardButton(text=f"{i.remark or i.protocol} | {i.port or '-'}", callback_data=f"vpnadmin:trial:setinbound:{i.id}")] for i in inbounds]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="vpnadmin:trial")])
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("📡 Inbound اکانت تست را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("vpnadmin:trial:setinbound:"))
async def trial_set_inbound(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    try: inbound_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError: await callback.answer("Inbound نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        settings = await get_trial_settings(session); inbound = await session.get(VPNInbound, inbound_id)
        if not inbound or not inbound.enabled or inbound.panel_id != settings.panel_id:
            await callback.answer("Inbound نامعتبر است.", show_alert=True); return
        settings.inbound_id = inbound.id
        if settings.id == 1 and settings not in session: session.add(settings)
        await session.commit()
    await callback.answer("Inbound انتخاب شد.")
    await trial_menu(callback)


@router.callback_query(F.data == "vpnadmin:trial:stats")
async def trial_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session: stats = await trial_statistics(session)
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(
        "📊 <b>آمار اکانت تست</b>\n\n"
        f"تعداد کل دریافت‌کنندگان: {stats['total']}\n"
        f"اکانت‌های فعال: {stats['active']}\n"
        f"اکانت‌های منقضی‌شده: {stats['expired']}", reply_markup=trial_admin_keyboard())


@router.callback_query(F.data.in_({"vpnadmin:menu", "admin:vpn"}))
async def menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("⚙️ <b>مدیریت سرویس‌های VPN</b>", reply_markup=panel_admin_keyboard())


@router.callback_query(F.data == "vpnadmin:add")
async def add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    await state.set_state(VPNPanelStates.name); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("نام پنل را ارسال کنید یا /cancel بزنید.")


@router.message(VPNPanelStates.name)
async def get_name(message: Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); return
    await state.update_data(name=message.text.strip()); await state.set_state(VPNPanelStates.url); await message.answer("آدرس کامل پنل را ارسال کنید (مثال https://host:2053/).")


@router.message(VPNPanelStates.url)
async def get_url(message: Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); return
    if not message.text.startswith(("http://", "https://")): await message.answer("آدرس باید با http:// یا https:// شروع شود."); return
    await state.update_data(base_url=message.text.strip()); await state.set_state(VPNPanelStates.username); await message.answer("نام کاربری پنل را ارسال کنید.")


@router.message(VPNPanelStates.username)
async def get_username(message: Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); return
    await state.update_data(username=message.text.strip()); await state.set_state(VPNPanelStates.password); await message.answer("رمز پنل را ارسال کنید.")


@router.message(VPNPanelStates.password)
async def get_password(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): await state.clear(); return
    if not message.text or message.text == "/cancel": await state.clear(); await message.answer("اتصال پنل لغو شد."); return
    data = await state.get_data()
    try:
        async with async_session() as session:
            panel = await save_panel(session, data["name"], data["base_url"], data["username"], message.text)
            await sync_panel_inbounds(session, panel)
    except VPNPanelError:
        await state.clear(); await message.answer("❌ اتصال یا احراز هویت پنل ناموفق بود؛ اطلاعات ذخیره نشد."); return
    except Exception:
        await state.clear(); await message.answer("❌ اتصال پنل ناموفق بود؛ اطلاعات ذخیره نشد."); return
    await state.clear(); await message.answer("✅ پنل با موفقیت متصل و Inboundها همگام‌سازی شدند.")


@router.callback_query(F.data == "vpnadmin:list")
async def panel_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session: panels = (await session.execute(select(VPNPanel).order_by(VPNPanel.id))).scalars().all()
    text = "📡 <b>پنل‌های متصل</b>\n\n" + ("\n".join(f"• {p.name} — {p.connection_status}" for p in panels) or "پنلی ثبت نشده است.")
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(text, reply_markup=panel_admin_keyboard())


@router.callback_query(F.data == "vpnadmin:product_links")
async def product_links(callback: CallbackQuery,state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی غیرمجاز",show_alert=True)
        return
    async with async_session() as session:
        products=(await session.scalars(select(Product).join(Category)
            .where(Category.section=="vpn").order_by(Product.id).limit(30))).all()
        inbounds=(await session.scalars(select(VPNInbound).join(VPNPanel)
            .where(VPNInbound.enabled,VPNPanel.is_active,VPNInbound.protocol.in_(SUPPORTED_PROTOCOLS))
            .order_by(VPNInbound.id).limit(30))).all()
    await callback.answer()
    if not isinstance(callback.message,Message):
        return
    if not products or not inbounds:
        await callback.message.answer("برای تنظیم تحویل، باید بستهٔ VPN و ورودی فعال روی پنل داشته باشی.")
        return
    await state.set_state(VPNPanelStates.product_link)
    package_rows="\n".join(f"{p.id} · {escape(p.name[:60])}" for p in products)
    inbound_rows="\n".join(f"{i.id} · {escape(i.remark[:40] or i.protocol)}" for i in inbounds)
    await callback.message.answer(
        "شناسهٔ بسته، شناسهٔ ورودی و حجم به گیگابایت را با فاصله بفرست. "
        "مثال <code>12 3 20</code>. لغو با /cancel.\n\n"
        f"<b>بسته‌ها</b>\n{package_rows}\n\n<b>ورودی‌ها</b>\n{inbound_rows}"
    )


@router.message(VPNPanelStates.product_link)
async def set_product_link(message: Message,state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    text=(message.text or "").strip()
    if text=="/cancel":
        await state.clear()
        await message.answer("تنظیم تحویل لغو شد.")
        return
    parts=text.split()
    if len(parts)!=3 or not all(x.isdecimal() and 1<=len(x)<=9 for x in parts):
        await message.answer("شناسهٔ بسته، شناسهٔ ورودی و حجم را به صورت سه عدد بفرست.")
        return
    product_id,inbound_id,volume=map(int,parts)
    if not 0<volume<=999999:
        await message.answer("حجم باید عددی بین ۱ تا ۹۹۹۹۹۹ گیگابایت باشد.")
        return
    async with async_session.begin() as session:
        product=await session.scalar(select(Product).join(Category)
            .where(Product.id==product_id,Category.section=="vpn").with_for_update(of=Product))
        inbound=await session.scalar(select(VPNInbound).join(VPNPanel)
            .where(VPNInbound.id==inbound_id,VPNInbound.enabled,VPNPanel.is_active,
                   VPNInbound.protocol.in_(SUPPORTED_PROTOCOLS)))
        if not product or not inbound or not product.duration_days:
            await message.answer("بسته، مدت اعتبار آن یا ورودی فعال معتبر نیست.")
            return
        product.vpn_volume_gb=volume
        await session.execute(delete(ProductVPNInbound).where(ProductVPNInbound.product_id==product.id))
        session.add(ProductVPNInbound(product_id=product.id,inbound_id=inbound.id))
    await state.clear()
    await message.answer(f"بسته {product_id} به ورودی {inbound_id} وصل شد. حجم بسته {volume} گیگابایت است.",reply_markup=panel_admin_keyboard())


@router.callback_query(F.data == "vpnadmin:inbounds")
async def inbound_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی غیرمجاز", show_alert=True); return
    async with async_session() as session: inbounds = (await session.execute(select(VPNInbound).order_by(VPNInbound.panel_id, VPNInbound.id))).scalars().all()
    text = "🌐 <b>Inbound ها</b>\n\n" + ("\n".join(f"{'🟢' if x.enabled else '🔴'} {x.remark} | {x.protocol} | {x.port or '-'}" for x in inbounds) or "Inboundی ثبت نشده است.")
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(text, reply_markup=panel_admin_keyboard())
