from core.admin_settings import content_prefix
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from core.features import is_feature_enabled

from modules.shop.keyboards import (
    main_menu_keyboard,
    back_to_shop_keyboard,
    ai_menu_keyboard,
    back_to_ai_keyboard,
    ai_services_keyboard,
    orders_keyboard,
    order_detail_keyboard,
    ai_tutorials_keyboard,
    ai_tutorial_detail_keyboard,
    ai_wallet_keyboard,
    ai_shared_account_keyboard,
    ai_services_keyboard,
    ai_service_detail_keyboard,
)
from database.session import async_session
from modules.catalog.categories.service import get_categories
from modules.catalog.categories.keyboards import categories_keyboard

from modules.start.content import build_welcome_message
from modules.catalog.keyboards import products_keyboard
from modules.catalog.service import get_products
from database.models import AICodeRequest, AIAccountDelivery, Category, Order, Product, ProductGroup, VPNOrderDetails
from modules.vpn.panel.client import decrypt_password
from modules.checkout.admin_review import get_admin_ids
from modules.wallet.service import get_wallet, get_transactions
from modules.checkout.states import CheckoutStates
import re
from html import escape


router = Router(name="shop")


# اطلاعات دسته بندی ها
CATEGORY_INFO = {

    "ai": {
        "title": "🧠 فروشگاه هوش مصنوعی",
        "description": """
🧠 <b>بخش هوش مصنوعی NR SHOP</b>

به بخش خدمات هوش مصنوعی خوش آمدید.

در این دسته هنوز محصولی برای خرید موجود نیست.
"""
    },

    "vpn": {
        "title": "🌐 فروشگاه VPN",
        "description": """
🌐 <b>بخش سرویس VPN</b>

در این قسمت سرویس‌های VPN ارائه خواهند شد.

در این دسته هنوز محصولی برای خرید موجود نیست.
"""
    },

    "telegram": {
        "title": "✈️ امکانات تلگرام",
        "description": """
✈️ <b>بخش امکانات تلگرام</b>

به بخش خدمات تلگرام خوش آمدید.

در این دسته هنوز محصولی برای خرید موجود نیست.
"""
    },

    "vps": {
        "title": "🖥 فروشگاه سرور مجازی",
        "description": """
🖥 <b>بخش سرور مجازی</b>

در این قسمت انواع سرورهای مجازی ارائه خواهند شد.

در این دسته هنوز محصولی برای خرید موجود نیست.
"""
    }

}


# صفحه اصلی فروشگاه
@router.callback_query(F.data == "shop:home")
async def shop_home(callback: CallbackQuery):

    await callback.answer()

    if isinstance(callback.message, Message):

        await callback.message.edit_text(
            build_welcome_message(callback.from_user.full_name),
            reply_markup=main_menu_keyboard()
        )


@router.callback_query(F.data.in_({"agency:panel", "agency:bot"}))
async def agency_preparation_handler(callback: CallbackQuery):
    if not is_feature_enabled("vps"):
        await callback.answer("بخش نمایندگی غیرفعال است.", show_alert=True)
        return
    key = "section:agency_" + callback.data.split(":")[1]
    info = content_prefix(key).strip()
    await callback.answer()
    from contextlib import closing
    from html import escape
    from core.admin_settings import representative_db
    with closing(representative_db()) as db:
        rep = db.execute("SELECT name,bot FROM representatives WHERE telegram_id=? AND active=1", (callback.from_user.id,)).fetchone()
    lines = [info] if info else []
    if rep:
        lines.append("نماینده فعال: " + escape(rep[0]))
        if rep[1] != "-":
            lines.append("ربات نمایندگی: " + escape(rep[1]))
    keyboard = None
    if rep and rep[1] == "-" and callback.data == "agency:bot":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        manager = await callback.bot.me()
        if manager.can_manage_bots:
            link = f"https://t.me/newbot/{manager.username}/NR_{callback.from_user.id}_bot"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ساخت ربات نمایندگی", url=link)]])
        else:
            lines.append("برای ساخت ربات، مدیر باید قابلیت مدیریت ربات‌ها را در BotFather فعال کند.")
    await callback.message.answer("\n".join(lines) or "اطلاعات نمایندگی هنوز ثبت نشده است.", reply_markup=keyboard)


# ورود به دسته بندی ها
@router.callback_query(F.data.startswith("shop:category:"))
async def category_handler(callback: CallbackQuery):

    category = callback.data.split(":")[-1]

    # بررسی وجود دسته بندی
    if category not in CATEGORY_INFO:

        await callback.answer(
            "❌ دسته بندی نامعتبر است.",
            show_alert=True
        )

        return

    # بررسی فعال بودن دسته بندی
    if not is_feature_enabled(category):

        await callback.answer(
            "🔴 این بخش در حال حاضر غیرفعال است.",
            show_alert=True
        )

        if isinstance(callback.message, Message):

            await callback.message.edit_reply_markup(
                reply_markup=main_menu_keyboard()
            )

        return

    if category == "ai":
        await callback.answer()
        welcome = content_prefix("texts:ai_menu") + build_welcome_message(callback.from_user.full_name)
        text = (
            welcome
            + "\n\n"
            + "🧠 <b>خدمات هوش مصنوعی NR SHOP</b>\n"
            + "لطفاً یکی از گزینه‌های زیر را انتخاب کنید."
        )
        if isinstance(callback.message, Message):
            await callback.message.edit_text(text, reply_markup=ai_menu_keyboard())
        return

    info = CATEGORY_INFO[category]
    products = get_products(category)

    if not products:
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                f"""
{info['description']}

━━━━━━━━━━━━━━

📦 در حال حاضر محصولی در این دسته‌بندی ثبت نشده است.
""",
                reply_markup=back_to_shop_keyboard(),
            )
        return

    await callback.answer()

    if isinstance(callback.message, Message):

        await callback.message.edit_text(
            f"""
<b>{info['title']}</b>

📦 محصولات موجود در این دسته‌بندی:
""",
            reply_markup=products_keyboard(category, products),
        )


@router.callback_query(F.data == "ai:buy")
async def ai_buy_handler(callback: CallbackQuery):
    if not is_feature_enabled("ai"):
        await callback.answer("🔴 بخش هوش مصنوعی غیرفعال است.", show_alert=True)
        return

    async with async_session() as session:
        categories = await get_categories(
            session=session,
            active_only=True,
            section="ai",
        )

    await callback.answer()
    if not categories:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                "🧠 <b>خرید اشتراک هوش مصنوعی</b>\n\n"
                "در حال حاضر دسته‌بندی فعالی ثبت نشده است.",
                reply_markup=categories_keyboard([]),
            )
        return

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "💠 کدام سرویس را می‌خواهید؟",
            reply_markup=categories_keyboard(categories),
        )


@router.callback_query(F.data == "ai:home")
async def ai_home_handler(callback: CallbackQuery):
    if not is_feature_enabled("ai"):
        await callback.answer("🔴 این بخش غیرفعال است.", show_alert=True)
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            content_prefix("texts:ai_menu") + build_welcome_message(callback.from_user.full_name)
            + "\n\n🧠 <b>خدمات هوش مصنوعی NR SHOP</b>",
            reply_markup=ai_menu_keyboard(),
        )


@router.callback_query(F.data == "ai:help")
async def ai_tutorials_handler(callback: CallbackQuery):
    if not is_feature_enabled("ai"):
        await callback.answer("🔴 این بخش غیرفعال است.", show_alert=True)
        return
    async with async_session() as session:
        result = await session.execute(
            select(Product)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(ProductGroup, ProductGroup.id == Product.group_id)
            .where(
                Category.section == "ai",
                Category.is_active.is_(True),
                Product.is_active.is_(True),
                (ProductGroup.id.is_(None) | ProductGroup.is_active.is_(True)),
            )
            .order_by(ProductGroup.sort_order, ProductGroup.id, Product.id)
        )
        products = result.scalars().all()
    await callback.answer()
    if isinstance(callback.message, Message):
        text = (
            "📚 <b>راهنمای استفاده از هوش مصنوعی</b>\n\n"
            "💡 آموزش فعال‌سازی و استفاده از اشتراک‌های خریداری‌شده."
        )
        if not products:
            text += "\n\n📭 در حال حاضر آموزشی برای محصولات فعال ثبت نشده است."
        await callback.message.edit_text(content_prefix("guides:ai") + text, reply_markup=ai_tutorials_keyboard(products))


@router.callback_query(F.data.startswith("ai:tutorial:"))
async def ai_tutorial_detail_handler(callback: CallbackQuery):
    try:
        product_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("محصول نامعتبر است.", show_alert=True)
        return
    async with async_session() as session:
        result = await session.execute(
            select(Product)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(ProductGroup, ProductGroup.id == Product.group_id)
            .where(
                Product.id == product_id,
                Product.is_active.is_(True),
                Category.section == "ai",
                Category.is_active.is_(True),
                (ProductGroup.id.is_(None) | ProductGroup.is_active.is_(True)),
            )
        )
        product = result.scalar_one_or_none()
    if not product:
        await callback.answer("این آموزش در دسترس نیست.", show_alert=True)
        return
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"📚 <b>آموزش {product.name}</b>\n\n"
            "📭 آموزش این محصول هنوز در فروشگاه ثبت نشده است.\n\n"
            "پس از ثبت محتوای رسمی، متن، تصویر یا ویدئوی آموزشی در همین صفحه نمایش داده می‌شود.",
            reply_markup=ai_tutorial_detail_keyboard(),
        )


@router.callback_query(F.data == "ai:services")
async def ai_services_handler(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Order, AIAccountDelivery)
            .join(Product, Product.id == Order.product_id)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(AIAccountDelivery, AIAccountDelivery.order_id == Order.id)
            .outerjoin(VPNOrderDetails, VPNOrderDetails.order_id == Order.id)
            .where(
                Order.telegram_user_id == callback.from_user.id,
                Category.section == "ai",
                Order.status.not_in(["cancelled", "rejected"]),
                VPNOrderDetails.id.is_(None),
            )
            .order_by(Order.created_at.desc(), Order.id.desc())
        )
        services = result.all()
    await callback.answer()
    if isinstance(callback.message, Message):
        text = "👨🏻‍💻 <b>سرویس‌های هوش مصنوعی من</b>\n\n💎 اشتراک‌های خریداری‌شده شما:"
        if not services: text += "\n\n📭 هنوز سرویس AI فعالی ندارید."
        await callback.message.edit_text(text, reply_markup=ai_services_keyboard(services))


@router.callback_query(F.data.startswith("ai:service:"))
async def ai_service_detail_handler(callback: CallbackQuery):
    try: order_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError: await callback.answer("سرویس نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        row = (await session.execute(select(Order, AIAccountDelivery).join(Product, Product.id == Order.product_id).join(Category, Category.id == Product.category_id).outerjoin(AIAccountDelivery, AIAccountDelivery.order_id == Order.id).outerjoin(VPNOrderDetails, VPNOrderDetails.order_id == Order.id).where(Order.id == order_id, Order.telegram_user_id == callback.from_user.id, Category.section == "ai", VPNOrderDetails.id.is_(None)))).first()
    if not row: await callback.answer("سرویس پیدا نشد.", show_alert=True); return
    order, delivery = row
    kind = "Dedicated" if delivery and delivery.account_type == "dedicated" else "Shared"
    status = {"provisioning": "🔵 در حال آماده‌سازی", "paid": "🟢 فعال", "rejected": "🔴 غیرفعال", "cancelled": "⚫ منقضی‌شده"}.get(order.status, "🟡 در انتظار فعال‌سازی")
    purchased = order.created_at.strftime("%Y-%m-%d") if order.created_at else "ثبت نشده"
    expiry = "ثبت نشده"
    if order.created_at and order.duration_days:
        from datetime import timedelta
        expiry = (order.created_at + timedelta(days=order.duration_days)).strftime("%Y-%m-%d")
    email = f"\n\n📧 ایمیل: {delivery.email}" if delivery and delivery.account_type == "dedicated" else ""
    await callback.answer()
    if isinstance(callback.message, Message): await callback.message.edit_text(
        f"💎 <b>اطلاعات اشتراک شما</b>\n\n📦 محصول: {order.product_name}\n👤 نوع اکانت: {kind}\n🧾 شماره سفارش: <code>{order.order_number}</code>{email}\n\n📅 تاریخ خرید: {purchased}\n📆 تاریخ انقضا: {expiry}\n\n{status}",
        reply_markup=ai_service_detail_keyboard(order.id))


@router.callback_query(F.data.in_({"ai:2fa", "ai:referral"}))
async def ai_preparation_handler(callback: CallbackQuery):
    await callback.answer("🚧 این بخش در حال آماده‌سازی است.", show_alert=True)


@router.callback_query(F.data == "ai:wallet")
async def ai_wallet_handler(callback: CallbackQuery):
    async with async_session() as session:
        wallet = await get_wallet(session, callback.from_user.id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🪙 <b>کیف پول NR SHOP</b>\n\n"
            "👤 کاربر عزیز\n\n"
            f"💰 موجودی فعلی شما: <b>{wallet.balance:,} تومان</b>\n\n"
            "━━━━━━━━━━━━━━\n\n"
            "از کیف پول مشترک برای خرید محصولات هوش مصنوعی و VPN استفاده کنید.",
            reply_markup=ai_wallet_keyboard(),
        )


@router.callback_query(F.data.in_({"ai:wallet:topup", "ai:wallet:history"}))
async def ai_wallet_preparation_handler(callback: CallbackQuery):
    if callback.data == "ai:wallet:history":
        async with async_session() as session:
            transactions = await get_transactions(session, callback.from_user.id)
        lines = ["📜 <b>تاریخچه تراکنش‌های کیف پول</b>", ""]
        lines.extend(f"{'➕' if tx.kind == 'credit' else '➖'} {tx.amount:,} تومان | {tx.description or tx.kind}" for tx in transactions)
        await callback.answer()
        if isinstance(callback.message, Message): await callback.message.edit_text("\n".join(lines) if transactions else "📜 <b>تاریخچه تراکنش‌ها</b>\n\nهنوز تراکنشی ثبت نشده است.", reply_markup=ai_wallet_keyboard())
        return
    await callback.answer("🚧 شارژ کیف پول در مرحله پرداخت کارت‌به‌کارت تکمیل می‌شود.", show_alert=True)


ORDER_SECTION_NAMES = {"ai": "هوش مصنوعی", "vpn": "VPN", "telegram": "تلگرام", "vps": "سرور مجازی"}
ORDER_PAGE_SIZE = 12


def customer_orders(user_id):
    return (
        select(Order, VPNOrderDetails.id.label("vpn_id"), Category.section)
        .outerjoin(VPNOrderDetails, VPNOrderDetails.order_id == Order.id)
        .outerjoin(Product, Product.id == Order.product_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(Order.telegram_user_id == user_id)
    )


def order_section(section, vpn_id):
    if vpn_id is not None:
        return "vpn"
    return section


@router.callback_query(F.data == "shop:orders")
@router.callback_query(F.data.regexp(r"^shop:orders:[0-9]{1,8}$"))
async def orders_handler(callback: CallbackQuery):
    if not is_feature_enabled("orders"):
        await callback.answer("بخش سفارش‌ها غیرفعال است.", show_alert=True)
        return
    page = int(callback.data.split(":")[2]) if callback.data.count(":") == 2 else 0
    async with async_session() as session:
        query = customer_orders(callback.from_user.id).order_by(Order.created_at.desc(), Order.id.desc())
        rows = (await session.execute(query.offset(page * ORDER_PAGE_SIZE).limit(ORDER_PAGE_SIZE+1))).all()
    orders = [(order, ORDER_SECTION_NAMES.get(order_section(section,vpn_id),"سفارش")) for order,vpn_id,section in rows[:ORDER_PAGE_SIZE]]
    await callback.answer()
    if isinstance(callback.message, Message):
        message = "از فهرست همهٔ بخش‌ها، سفارش موردنظرت رو انتخاب کن." if orders else "سفارشی برای نمایش در این صفحه وجود نداره."
        await callback.message.edit_text(
            f"📦 <b>محصولات من</b>\n\n{message}",
            reply_markup=orders_keyboard(orders,page,len(rows)>ORDER_PAGE_SIZE),
        )


@router.callback_query(F.data.regexp(r"^shop:order:[0-9]{1,18}:[0-9]{1,8}$"))
@router.callback_query(F.data.regexp(r"^ai:order:[0-9]{1,18}$"))
async def order_detail(callback: CallbackQuery):
    parts = callback.data.split(":")
    page = int(parts[3]) if len(parts) == 4 else 0
    async with async_session() as session:
        row = (await session.execute(customer_orders(callback.from_user.id).where(Order.id==int(parts[2])))).first()
        if not row:
            await callback.answer("سفارش پیدا نشد.", show_alert=True)
            return
        order,vpn_id,category = row
        section=order_section(category,vpn_id)
        if section is None and await session.scalar(select(AIAccountDelivery.id).where(AIAccountDelivery.order_id==order.id)):
            section="ai"
    labels = {
        "awaiting_payment": "🟡 در انتظار پرداخت",
        "awaiting_discount": "🟡 در انتظار پرداخت",
        "under_review": "🔵 در انتظار بررسی مدیر",
        "provisioning": "🟠 در حال آماده‌سازی",
        "paid": "🟢 پرداخت تأیید شده",
        "rejected": "🔴 ردشده",
        "cancelled": "⚫ لغوشده",
    }
    created = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "ثبت نشده"
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "<b>جزئیات سفارش</b>\n\n"
            f"شماره سفارش <code>{escape(order.order_number)}</code>\n"
            f"بخش {ORDER_SECTION_NAMES.get(section,'فروشگاه')}\n"
            f"محصول {escape(order.product_name)}\n"
            f"مبلغ سفارش {order.final_amount:,} تومان\n"
            f"تاریخ ثبت {created}\n"
            f"وضعیت {labels.get(order.status,'نامشخص')}",
            reply_markup=order_detail_keyboard(order,section,page,is_vpn=vpn_id is not None),
        )


@router.callback_query(F.data.startswith("ai:account:"))
async def ai_account_delivery_handler(callback: CallbackQuery):
    try:
        order_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("سفارش نامعتبر است.", show_alert=True)
        return
    async with async_session() as session:
        result = await session.execute(
            select(Order, AIAccountDelivery)
            .join(Product, Product.id == Order.product_id)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(AIAccountDelivery, AIAccountDelivery.order_id == Order.id)
            .outerjoin(VPNOrderDetails, VPNOrderDetails.order_id == Order.id)
            .where(
                Order.id == order_id,
                Order.telegram_user_id == callback.from_user.id,
                Category.section == "ai",
                VPNOrderDetails.id.is_(None),
            )
        )


        row = result.first()
    if not row:
        await callback.answer("اطلاعات این سفارش در دسترس نیست.", show_alert=True)
        return
    order, delivery = row
    await callback.answer()
    if isinstance(callback.message, Message):
        if delivery is None:
            text = ("🎁 <b>تحویل اکانت هوش مصنوعی</b>\n\n"
                    f"📦 محصول: {order.product_name}\n\n"
                    "⏳ اطلاعات حساب شما هنوز آماده نشده است.\n"
                    "پس از ثبت اطلاعات واقعی توسط مدیر، همین‌جا نمایش داده می‌شود.")
            keyboard = ai_account_delivery_keyboard(order.id)
        else:
            password = decrypt_password(delivery.encrypted_password) if delivery.encrypted_password else None
            text = ("🎉 <b>اکانت شما با موفقیت آماده شد!</b>\n\n"
                    "💎 اطلاعات اشتراک شما:\n\n"
                    f"📦 محصول: {order.product_name}\n\n"
                    f"📧 ایمیل: <code>{delivery.email}</code>\n"
                    f"🔑 رمز عبور: <code>{password or 'ثبت نشده'}</code>")
            keyboard = ai_shared_account_keyboard(order.id) if delivery.account_type == "shared" else ai_account_delivery_keyboard(order.id)
        await callback.message.edit_text(
            text + "\n\n━━━━━━━━━━━━━━━━━━\n\n❤️ از خرید شما سپاسگزاریم.\nNR SHOP",
            reply_markup=keyboard,
        )


@router.callback_query(F.data.startswith("ai:email:"))
async def ai_email_start(callback: CallbackQuery, state):
    try: order_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError: await callback.answer("سفارش نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        row = (await session.execute(select(Order, Product).join(Product, Product.id == Order.product_id).join(Category, Category.id == Product.category_id).where(Order.id == order_id, Order.telegram_user_id == callback.from_user.id, Category.section == "ai", Product.account_type == "dedicated"))).first()
    if not row: await callback.answer("این سفارش برای ثبت ایمیل در دسترس نیست.", show_alert=True); return
    await state.update_data(ai_email_order_id=order_id); await state.set_state(CheckoutStates.waiting_ai_email); await callback.answer()
    if isinstance(callback.message, Message): await callback.message.answer("ایمیلی رو بفرست که می‌خوای اشتراک روی اون فعال بشه.")


@router.message(CheckoutStates.waiting_ai_email)
async def ai_email_message(message: Message, state):
    email = (message.text or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): await message.answer("این آدرس معتبر نیست. ایمیل رو به شکل name@example.com بفرست."); return
    order_id = (await state.get_data()).get("ai_email_order_id")
    async with async_session() as session:
        row = (await session.execute(select(Order, Product).join(Product, Product.id == Order.product_id).join(Category, Category.id == Product.category_id).where(Order.id == order_id, Order.telegram_user_id == message.from_user.id, Category.section == "ai", Product.account_type == "dedicated"))).first()
        if not row: await state.clear(); await message.answer("سفارش پیدا نشد."); return
        order, product = row
        existing = (await session.execute(select(AIAccountDelivery).where(AIAccountDelivery.order_id == order.id))).scalar_one_or_none()
        if existing: await state.clear(); await message.answer("ایمیل این سفارش قبلاً ثبت شده است."); return
        session.add(AIAccountDelivery(order_id=order.id, account_type="dedicated", email=email)); await session.commit()
    await state.clear()
    report = f"📧 <b>ایمیل فعال‌سازی حساب اختصاصی</b>\n\n👤 مشتری: {message.from_user.full_name}\n🆔 شناسه: <code>{message.from_user.id}</code>\n📦 محصول: {product.name}\n📧 ایمیل: <code>{email}</code>\n🧾 سفارش: <code>{order.order_number}</code>"
    for admin_id in get_admin_ids():
        try: await message.bot.send_message(admin_id, report, parse_mode="HTML")
        except Exception: pass
    await message.answer("✅ ایمیل شما ثبت و برای فعال‌سازی حساب اختصاصی برای مدیر ارسال شد.")


@router.callback_query(F.data.startswith("ai:code:"))
async def ai_code_request_handler(callback: CallbackQuery):
    try: order_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError: await callback.answer("سفارش نامعتبر است.", show_alert=True); return
    async with async_session() as session:
        row = (await session.execute(select(Order, AIAccountDelivery).join(AIAccountDelivery, AIAccountDelivery.order_id == Order.id).join(Product, Product.id == Order.product_id).join(Category, Category.id == Product.category_id).where(Order.id == order_id, Order.telegram_user_id == callback.from_user.id, Category.section == "ai", AIAccountDelivery.account_type == "shared"))).first()
        if not row: await callback.answer("این حساب اشتراکی پیدا نشد.", show_alert=True); return
        order, delivery = row
        existing = (await session.execute(select(AICodeRequest).where(AICodeRequest.order_id == order.id, AICodeRequest.status == "pending"))).scalar_one_or_none()
        if existing:
            await callback.answer("درخواست شما قبلاً برای مدیر ارسال شده است.", show_alert=True); return
        session.add(AICodeRequest(order_id=order.id, telegram_user_id=callback.from_user.id)); await session.commit()
    await callback.answer("درخواست شما ثبت شد.", show_alert=True)
    for admin_id in get_admin_ids():
        try:
            await callback.bot.send_message(admin_id, f"🔔 <b>درخواست کد ورود اکانت اشتراکی</b>\n\n👤 مشتری: {callback.from_user.full_name}\n🆔 شناسه: <code>{callback.from_user.id}</code>\n📦 محصول: {order.product_name}\n📧 ایمیل اکانت: <code>{delivery.email}</code>\n🧾 شماره سفارش: <code>{order.order_number}</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔐 ارسال کد به مشتری", callback_data=f"admin:ai_code:{order.id}")]]))
        except Exception:
            pass
    if isinstance(callback.message, Message): await callback.message.edit_text("📨 <b>درخواست دریافت کد ورود شما ثبت شد.</b>\n\n⏳ درخواست برای مدیر ارسال شد.\n\nلطفاً منتظر بمانید تا کد ورود برای شما ارسال شود.", reply_markup=ai_shared_account_keyboard(order.id))


# پشتیبانی
@router.callback_query(F.data == "shop:support")
async def support_handler(callback: CallbackQuery):

    if not is_feature_enabled("support"):

        await callback.answer(
            "🔴 بخش پشتیبانی غیرفعال است.",
            show_alert=True
        )

        return

    await callback.answer()

    if isinstance(callback.message, Message):

        from modules.support.keyboards import support_menu_keyboard

        await callback.message.edit_text(
            "🎧 <b>پشتیبانی هوش مصنوعی</b>\n\n"
            "برای راهنمایی دربارهٔ خرید یا فعال‌سازی، تیکت جدید باز کن. پاسخ رو در «تیکت‌های من» می‌بینی.",
            reply_markup=support_menu_keyboard("ai"),
        )
