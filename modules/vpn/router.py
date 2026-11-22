from core.admin_settings import content_prefix
from html import escape
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from core.features import is_feature_enabled
from database.models import Category, Order, Product, ProductGroup, VPNOrderDetails, VPNTrialClaim
from database.session import async_session
from modules.checkout.service import ProductUnavailableError, create_order
from modules.checkout.keyboards import order_summary_keyboard
from modules.vpn.keyboards import vpn_categories_keyboard, vpn_grouped_products_keyboard, vpn_invoice_keyboard, vpn_menu_keyboard, vpn_partnership_keyboard, vpn_service_detail_keyboard, vpn_services_keyboard, vpn_tutorial_detail_keyboard, vpn_tutorial_keyboard, vpn_username_keyboard, vpn_wallet_keyboard
from modules.vpn.partnership import PartnershipStates
from modules.checkout.admin_review import get_admin_ids
from modules.vpn.states import VPNStates
from modules.vpn.username import automatic_username, is_valid_username
from modules.referral.service import referral_stats
from modules.vpn.keyboards import vpn_referral_keyboard
from urllib.parse import quote
from modules.vpn.trial import claim_query, claim_trial, get_trial_settings, trial_available
from modules.vpn.provisioning import linked_inbound, provision_vpn_order, ProvisioningError
from modules.vpn.trial_keyboards import trial_customer_keyboard


router = Router(name="vpn")


def trial_message(claim):
    if claim.expires_at<=datetime.now(timezone.utc):
        return "مدت سرویس آزمایشی‌ات تمام شده. برای ادامه می‌تونی اشتراک بخری."
    return (f"<b>اشتراک آزمایشی آماده است</b>\n\nحجم {claim.volume_gb} گیگابایت\n"
            f"اعتبار تا {claim.expires_at:%Y-%m-%d %H:%M} UTC\n\n"
            f"<code>{escape(claim.subscription_url)}</code>")


@router.callback_query(F.data == "vpn:trial")
async def vpn_trial(callback: CallbackQuery):
    async with async_session() as session:
        settings=await get_trial_settings(session)
        claim=await session.scalar(claim_query(callback.from_user.id))
    ready=bool(claim and claim.subscription_url)
    enabled=is_feature_enabled("vpn") and trial_available(settings)
    if ready:
        text=trial_message(claim)
    elif enabled:
        text=(f"<b>اشتراک آزمایشی</b>\n\n{settings.volume_gb} گیگابایت برای {settings.duration_hours} ساعت. "
              "برای ساخت یا ادامهٔ همان درخواست، دکمهٔ دریافت را بزن.")
    else:
        text="اشتراک آزمایشی فعلاً برای دریافت آماده نیست."
    await callback.answer()
    if isinstance(callback.message,Message):
        await callback.message.edit_text(text,reply_markup=trial_customer_keyboard(enabled,ready))


@router.callback_query(F.data == "vpn:trial:claim")
async def vpn_trial_claim(callback: CallbackQuery):
    if not is_feature_enabled("vpn"):
        await callback.answer("فروشگاه VPN غیرفعال است.",show_alert=True)
        return
    await callback.answer("در حال آماده‌سازی اشتراک…")
    async with async_session() as session:
        claim,status=await claim_trial(session,callback.from_user.id)
    text=trial_message(claim) if status=="ready" else {
        "expired":"مدت درخواست آزمایشی قبلی تمام شده.",
        "disabled":"تنظیمات اشتراک آزمایشی هنوز کامل نیست.",
        "failed":"پنل لینک را تحویل نداد. دوباره تلاش کن. تلاش دوباره سهمیهٔ جدیدی مصرف نمی‌کند.",
    }[status]
    if isinstance(callback.message,Message):
        await callback.message.edit_text(text,reply_markup=trial_customer_keyboard(status=="failed",status=="ready"))


def vpn_text(name):
    return content_prefix("texts:vpn_menu") + (
        f"<b>اشتراک VPN</b>\n\n{escape(name)}، بسته‌ها رو بر اساس حجم و مدت مقایسه کن. "
        "اگر اشتراک داری، لینک و جزئیاتش در «سرویس‌های من» هست."
    )


@router.callback_query(F.data == "shop:category:vpn")
async def vpn_home(callback: CallbackQuery):
    if not is_feature_enabled("vpn"): await callback.answer("🔴 بخش VPN غیرفعال است.", show_alert=True); return
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(vpn_text(callback.from_user.full_name), reply_markup=vpn_menu_keyboard())


@router.callback_query(F.data == "vpn:home")
async def vpn_home_back(callback: CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(vpn_text(callback.from_user.full_name), reply_markup=vpn_menu_keyboard())


@router.callback_query(F.data == "vpn:buy")
async def vpn_buy(callback: CallbackQuery):
    async with async_session() as session:
        categories = (await session.execute(select(Category).where(Category.section == "vpn", Category.is_active.is_(True)).order_by(Category.sort_order, Category.id))).scalars().all()
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text("🏅 <b>خرید اشتراک اختصاصی VIP</b>\n\nلطفاً دسته‌بندی سرویس را انتخاب کنید:", reply_markup=vpn_categories_keyboard(categories))


@router.callback_query(F.data.startswith("vpn:category:"))
async def vpn_category(callback: CallbackQuery):
    try: category_id = int(callback.data.split(":")[-1])
    except ValueError: await callback.answer("دسته‌بندی نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        groups = (await session.execute(select(ProductGroup).where(
            ProductGroup.category_id == category_id,
            ProductGroup.is_active.is_(True),
        ).order_by(ProductGroup.sort_order, ProductGroup.id))).scalars().all()
        products = (await session.execute(select(Product).where(
            Product.category_id == category_id,
            Product.is_active.is_(True),
            Product.group_id.is_not(None),
        ).order_by(Product.id))).scalars().all()
    products_by_group = {}
    for product in products:
        products_by_group.setdefault(product.group_id, []).append(product)
    visible_groups = [group for group in groups if products_by_group.get(group.id)]
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🛍 <b>محصولات VPN</b>\n\nمحصول موردنظر را انتخاب کنید:",
            reply_markup=vpn_grouped_products_keyboard(
                visible_groups, products_by_group, category_id
            ),
        )


@router.callback_query(F.data.startswith("vpn:product:"))
async def vpn_product(callback: CallbackQuery, state: FSMContext):
    try: product_id = int(callback.data.split(":")[-1])
    except ValueError: await callback.answer("محصول نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        product = (await session.execute(select(Product).where(Product.id == product_id, Product.is_active.is_(True)))).scalar_one_or_none()
    if not product: await callback.answer("این محصول در دسترس نیست.", show_alert=True); return
    await state.update_data(product_id=product.id, category_id=product.category_id)
    await state.set_state(VPNStates.waiting_username)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🛒 <b>سرویس مورد نظر انتخاب شد ✅</b>\n\n"
            "📌 لطفاً یک نام کاربری با حروف لاتین به طول حداکثر ۲۰ کاراکتر وارد کنید 📱\n\n"
            "⚜️ یا از گزینه زیر (خودکار انتخاب کن 🌐) استفاده کنید.",
            reply_markup=vpn_username_keyboard(product.category_id),
        )


async def create_vpn_order(callback_or_message, state: FSMContext, username: str):
    if not is_valid_username(username): return False
    data = await state.get_data(); product_id = data.get("product_id")
    async with async_session() as session:
        duplicate = (await session.execute(select(VPNOrderDetails.id).join(Order).where(VPNOrderDetails.username == username, Order.status.not_in(["cancelled", "rejected"])).limit(1))).scalar_one_or_none()
        if duplicate: return None
        product=await session.get(Product,product_id) if product_id else None
        inbound=await linked_inbound(session,product_id) if product else None
        if not product or not product.vpn_volume_gb or not product.duration_days or inbound is None:
            return False
        try: order = await create_order(session, callback_or_message.from_user.id, product_id)
        except ProductUnavailableError: return False
        detail = VPNOrderDetails(order_id=order.id,username=username,inbound_id=inbound.id,
            server_name=(inbound.remark or f"Inbound {inbound.remote_inbound_id}")[:100],
            volume=f"{product.vpn_volume_gb} گیگابایت")
        session.add(detail); await session.commit(); await session.refresh(order)
    await state.clear()
    return order, detail


def invoice(order, detail):
    return content_prefix("texts:invoice") + f"📌 پیش فاکتور شماره = <code>{order.order_number}</code>\n\n👤 نام کاربری: {escape(detail.username)}\n🌐 سرور: {escape(detail.server_name)}\n🔒 نوع سرویس: {escape(order.service_type or 'VPN')} 😎\n📆 مدت اعتبار: {order.duration_days or 'ثبت نشده'} روز\n⌛ حجم بسته: {escape(detail.volume)}\n\n━━━━━━━━━━━━━━━━━━\n\n✅ مبلغ قابل پرداخت: {order.final_amount:,} تومان\n\n💫 سفارش شما آماده پرداخت هست 💰"


@router.callback_query(F.data == "vpn:username:auto")
async def vpn_auto_username(callback: CallbackQuery, state: FSMContext):
    username = automatic_username(callback.from_user.id); result = await create_vpn_order(callback, state, username)
    if result is None: await callback.answer("این نام کاربری قبلاً استفاده شده است.", show_alert=True); return
    if not result: await callback.answer("امکان ایجاد سفارش وجود ندارد.", show_alert=True); return
    order, detail = result
    await callback.answer(); await callback.message.edit_text(invoice(order, detail), reply_markup=vpn_invoice_keyboard(order.order_number))


@router.callback_query(F.data == "vpn:username:manual")
async def vpn_manual_username(callback: CallbackQuery, state: FSMContext):
    await callback.answer();
    if isinstance(callback.message, Message): await callback.message.answer("✏️ نام کاربری لاتین خود را ارسال کنید یا /cancel بزنید.")


@router.message(VPNStates.waiting_username)
async def vpn_username_message(message: Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); await message.answer("انتخاب نام کاربری لغو شد."); return
    if not message.text or not is_valid_username(message.text): await message.answer("❌ نام کاربری نامعتبر است. فقط حروف لاتین، عدد و underscore و حداکثر ۲۰ کاراکتر."); return
    result = await create_vpn_order(message, state, message.text.strip())
    if result is None: await message.answer("❌ این نام کاربری قبلاً در سفارش فعال استفاده شده است."); return
    if not result: await message.answer("❌ امکان ایجاد سفارش وجود ندارد."); return
    order, detail = result
    await message.answer(invoice(order, detail), reply_markup=vpn_invoice_keyboard(order.order_number))


@router.callback_query(F.data == "vpn:referral")
async def vpn_referral(callback: CallbackQuery):
    me = await callback.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    async with async_session() as session: rows = await referral_stats(session, callback.from_user.id)
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(
        "📢 <b>دوستانت را به NR SHOP دعوت کن!</b>\n\n"
        "💎 با لینک اختصاصی خودت دوستانت را به خانواده NR SHOP دعوت کن.\n\n"
        f"🔗 لینک دعوت اختصاصی:\n<code>{link}</code>\n\n"
        f"👥 تعداد دوستان دعوت‌شده: {len(rows)}\n\n❤️ ممنون از همراهی شما!",
        reply_markup=vpn_referral_keyboard())


@router.callback_query(F.data == "vpn:referral:share")
async def vpn_referral_share(callback: CallbackQuery):
    me = await callback.bot.get_me(); link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_reply_markup(reply_markup=vpn_referral_keyboard())
    await callback.message.answer(f"📤 لینک دعوت خود را برای دوستانت ارسال کن:\n{link}")


@router.callback_query(F.data == "vpn:referral:friends")
async def vpn_referral_friends(callback: CallbackQuery):
    async with async_session() as session: rows = await referral_stats(session, callback.from_user.id)
    names = "\n".join(f"• کاربر دعوت‌شده <code>{user_id}</code>" for user_id, _ in rows) or "هنوز دوستی دعوت نشده است."
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(f"👥 <b>دوستان دعوت‌شده</b>\n\nتعداد: {len(rows)}\n\n{names}", reply_markup=vpn_referral_keyboard())


@router.callback_query(F.data == "vpn:partnership")
async def vpn_partnership(callback: CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "👑 <b>درخواست همکاری با NR SHOP</b>\n\n"
            "💎 از علاقه شما به همکاری با مجموعه NR SHOP سپاسگزاریم.\n\n"
            "اگر تمایل به همکاری، نمایندگی فروش یا فعالیت در زمینه فروش سرویس‌های VPN دارید، می‌توانید درخواست خود را برای ما ارسال کنید.\n\n"
            "🤝 منتظر پیشنهاد همکاری شما هستیم.",
            reply_markup=vpn_partnership_keyboard(),
        )


@router.callback_query(F.data == "vpn:partnership:new")
async def partnership_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PartnershipStates.full_name); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("👤 نام و نام خانوادگی خود را ارسال کنید.\nبرای لغو /cancel")


async def partnership_next(message: Message, state: FSMContext, field: str, next_state, prompt: str):
    if message.text == "/cancel": await state.clear(); await message.answer("درخواست همکاری لغو شد."); return
    if not message.text or not message.text.strip(): await message.answer("لطفاً پاسخ خود را به‌صورت متن ارسال کنید."); return
    await state.update_data(**{field: message.text.strip()}); await state.set_state(next_state); await message.answer(prompt)


@router.message(PartnershipStates.full_name)
async def partnership_name(message: Message, state: FSMContext):
    await partnership_next(message, state, "full_name", PartnershipStates.contact, "📱 آیدی تلگرام یا شماره تماس خود را ارسال کنید.")


@router.message(PartnershipStates.contact)
async def partnership_contact(message: Message, state: FSMContext):
    await partnership_next(message, state, "contact", PartnershipStates.field, "🤝 زمینه همکاری خود را بنویسید.")


@router.message(PartnershipStates.field)
async def partnership_field(message: Message, state: FSMContext):
    await partnership_next(message, state, "field", PartnershipStates.description, "📝 توضیحات درخواست همکاری خود را ارسال کنید.")


@router.message(PartnershipStates.description)
async def partnership_description(message: Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); await message.answer("درخواست همکاری لغو شد."); return
    if not message.text or not message.text.strip(): await message.answer("لطفاً توضیحات درخواست را ارسال کنید."); return
    data = await state.get_data(); data["description"] = message.text.strip(); await state.clear()
    report = ("👑 <b>درخواست همکاری جدید NR SHOP</b>\n\n"
              f"👤 نام: {escape(data['full_name'])}\n📱 تماس: {escape(data['contact'])}\n"
              f"🤝 زمینه: {escape(data['field'])}\n📝 توضیحات: {escape(data['description'])}\n"
              f"🆔 کاربر: <code>{message.from_user.id}</code>")
    sent = 0
    for admin_id in get_admin_ids():
        try: await message.bot.send_message(admin_id, report, parse_mode="HTML"); sent += 1
        except Exception: pass
    await message.answer("✅ درخواست همکاری شما ثبت و برای بررسی مدیر ارسال شد." if sent else "✅ درخواست شما ثبت شد؛ ارسال برای مدیر پس از فعال‌شدن دسترسی مدیر انجام می‌شود.")


@router.callback_query(F.data == "vpn:wallet")
async def vpn_wallet(callback: CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🪙 <b>کیف پول NR SHOP</b>\n\n"
            "👤 کاربر عزیز، سیستم کیف پول هنوز در NR SHOP فعال نشده است.\n\n"
            "💰 موجودی فعلی در حال حاضر قابل نمایش نیست.\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "پس از راه‌اندازی کیف پول مشترک، موجودی و تاریخچه تراکنش‌ها در این صفحه نمایش داده می‌شود.",
            reply_markup=vpn_wallet_keyboard(),
        )


@router.callback_query(F.data.in_({"vpn:wallet:topup", "vpn:wallet:history"}))
async def vpn_wallet_preparation(callback: CallbackQuery):
    await callback.answer("🚧 این قابلیت در حال آماده‌سازی است.", show_alert=True)


@router.callback_query(F.data == "vpn:tutorial")
async def vpn_tutorial(callback: CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            content_prefix("guides:vpn") + "💡 <b>آموزش استفاده از سرویس VPN</b>\n\n"
            "📱 لطفاً سیستم‌عامل دستگاه خود را انتخاب کنید.",
            reply_markup=vpn_tutorial_keyboard(),
        )


@router.callback_query(F.data.startswith("vpn:tutorial:"))
async def vpn_tutorial_platform(callback: CallbackQuery):
    platform = callback.data.split(":")[-1]
    titles = {
        "android": "🤖 آموزش اندروید",
        "ios": "🍎 آموزش آیفون (iOS)",
        "windows": "💻 آموزش ویندوز",
        "macos": "🖥 آموزش مک (MacOS)",
    }
    title = titles.get(platform)
    if not title:
        await callback.answer("سیستم‌عامل نامعتبر است.", show_alert=True); return
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"💡 <b>{title}</b>\n\n"
            "📚 محتوای این آموزش هنوز در فروشگاه ثبت نشده است.\n\n"
            "پس از آماده‌سازی، مراحل اتصال و فایل آموزشی در همین صفحه نمایش داده می‌شود.",
            reply_markup=vpn_tutorial_detail_keyboard(),
        )


@router.callback_query(F.data == "vpn:services")
async def vpn_services(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Order, VPNOrderDetails).join(
            VPNOrderDetails, VPNOrderDetails.order_id == Order.id
        ).where(Order.telegram_user_id == callback.from_user.id).order_by(Order.id.desc()))
        services = result.all()
    await callback.answer()
    if isinstance(callback.message, Message):
        if not services:
            await callback.message.edit_text(
                "👨🏻‍💻 <b>سرویس‌های VPN من</b>\n\n📭 شما هنوز سرویس VPN خریداری نکرده‌اید.",
                reply_markup=vpn_menu_keyboard(),
            )
        else:
            await callback.message.edit_text(
                "👤 <b>سرویس‌های شما</b>",
                reply_markup=vpn_services_keyboard(services),
            )


@router.callback_query(F.data.startswith("vpn:service:"))
async def vpn_service_details(callback: CallbackQuery):
    try: order_id = int(callback.data.split(":")[-1])
    except ValueError: await callback.answer("سرویس نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        result = await session.execute(select(Order, VPNOrderDetails).join(
            VPNOrderDetails, VPNOrderDetails.order_id == Order.id
        ).where(Order.id == order_id, Order.telegram_user_id == callback.from_user.id))
        row = result.first()
    if not row: await callback.answer("سرویس پیدا نشد.", show_alert=True); return
    order, detail = row
    status = "فعال" if detail.provisioning_status == "delivered" and order.status == "paid" else "در حال آماده‌سازی" if detail.provisioning_status in {"pending", "provisioning"} else "دارای خطا"
    purchased = order.created_at.strftime("%Y-%m-%d") if order.created_at else "ثبت نشده"
    expires = "ثبت نشده"
    if order.created_at and order.duration_days: expires = (order.created_at + __import__("datetime").timedelta(days=order.duration_days)).strftime("%Y-%m-%d")
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"💎 <b>اطلاعات سرویس شما</b>\n\n👤 نام کاربری: {escape(detail.username)}\n\n📦 محصول: {escape(order.product_name)}\n\n🌐 سرور: {escape(detail.server_name)}\n\n🔒 نوع اتصال: {escape(order.service_type or 'VPN')}\n\n📅 تاریخ خرید: {purchased}\n\n📆 تاریخ انقضا: {expires}\n\n⌛ حجم بسته: {escape(detail.volume)}\n\n{'🟢' if status == 'فعال' else '🟡' if status == 'در حال آماده‌سازی' else '⚠️'} وضعیت: {status}",
            reply_markup=vpn_service_detail_keyboard(order.id),
        )


@router.callback_query(F.data.startswith("vpn:renew:"))
async def vpn_renew(callback: CallbackQuery):
    await callback.answer("🚧 تمدید سرویس در مرحله بعد فعال می‌شود.", show_alert=True)


@router.callback_query(F.data.startswith("vpn:link:"))
async def vpn_subscription_link(callback: CallbackQuery):
    parts = callback.data.split(":")
    order_number = parts[-1]
    async with async_session() as session:
        query = select(Order, VPNOrderDetails).join(VPNOrderDetails, VPNOrderDetails.order_id == Order.id).where(Order.telegram_user_id == callback.from_user.id)
        query = query.where(Order.id == int(order_number)) if len(parts) > 3 and parts[-2] == "order" else query.where(Order.order_number == order_number)
        result = await session.execute(query)
        row = result.first()
        if not row or row[0].status not in {"paid","provisioning"}:
            await callback.answer("سرویس قابل دریافت نیست.",show_alert=True)
            return
        detail=row[1]
        if not detail.subscription_url:
            await callback.answer("در حال دریافت سرویس…")
            try:
                detail=await provision_vpn_order(session,row[0].id)
            except ProvisioningError:
                if isinstance(callback.message,Message):
                    await callback.message.answer("لینک هنوز آماده نیست. تنظیمات بسته یا وضعیت پنل را با پشتیبانی بررسی کن.")
                return
        else:
            await callback.answer()
        if isinstance(callback.message,Message):
            await callback.message.answer(f"لینک اشتراک شما\n<code>{escape(detail.subscription_url)}</code>")


@router.callback_query(F.data.startswith("vpn:qr:"))
async def vpn_qr_code(callback: CallbackQuery):
    parts = callback.data.split(":")
    order_number = parts[-1]
    async with async_session() as session:
        query = select(Order, VPNOrderDetails).join(VPNOrderDetails, VPNOrderDetails.order_id == Order.id).where(Order.telegram_user_id == callback.from_user.id)
        query = query.where(Order.id == int(order_number)) if len(parts) > 3 and parts[-2] == "order" else query.where(Order.order_number == order_number)
        result = await session.execute(query)
        row = result.first()
    if not row or not row[1].subscription_url:
        await callback.answer("QR Code سرویس هنوز آماده نیست.", show_alert=True); return
    await callback.answer("تولید QR Code در مرحله تحویل سرویس فعال می‌شود.", show_alert=True)


@router.callback_query(F.data == "vpn:noop")
async def vpn_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("vpn:group:"))
async def vpn_group_heading(callback: CallbackQuery):
    await callback.answer()
