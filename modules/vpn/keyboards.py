from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def vpn_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="خرید اشتراک VPN", callback_data="vpn:buy")],
        [InlineKeyboardButton(text="اشتراک آزمایشی", callback_data="vpn:trial")],
        [InlineKeyboardButton(text="کیف پول", callback_data="vpn:wallet"), InlineKeyboardButton(text="👨🏻‍💻 سرویس‌های من", callback_data="vpn:services")],
        [InlineKeyboardButton(text="💡 آموزش استفاده", callback_data="vpn:tutorial"), InlineKeyboardButton(text="📢 معرفی به دوستان", callback_data="vpn:referral")],
        [InlineKeyboardButton(text="🧑🏻‍🚀 تماس با پشتیبانی", callback_data="support:menu:vpn")],
        [InlineKeyboardButton(text="👑 درخواست همکاری", callback_data="vpn:partnership")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="shop:home")],
    ])


def vpn_categories_keyboard(categories):
    buttons = [[InlineKeyboardButton(text=category.name, callback_data=f"vpn:category:{category.id}")] for category in categories]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="vpn:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vpn_products_keyboard(products, category_id):
    buttons = [[
        InlineKeyboardButton(text="🛍️ محصول", callback_data="vpn:noop"),
        InlineKeyboardButton(text="💲 مبلغ", callback_data="vpn:noop"),
    ]]
    for product in products:
        duration = product.duration_days or 0
        marker = "🟦" if duration < 90 else "🟩"
        callback = f"vpn:product:{product.id}"
        buttons.append([
            InlineKeyboardButton(
                text=f"{marker} {product.name}",
                callback_data=callback,
            ),
            InlineKeyboardButton(
                text=f"{product.price:,} تومان",
                callback_data=callback,
            ),
        ])
    buttons.append([InlineKeyboardButton(text="🏠 بازگشت به لیست سرورها", callback_data="vpn:buy")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vpn_grouped_products_keyboard(groups, products_by_group, category_id):
    buttons = [[
        InlineKeyboardButton(text="🛍️ محصول", callback_data="vpn:noop"),
        InlineKeyboardButton(text="💲 مبلغ", callback_data="vpn:noop"),
    ]]
    for group in groups:
        products = products_by_group.get(group.id, [])
        if not products:
            continue
        buttons.append([InlineKeyboardButton(
            text=f"━━━━ {group.name} ━━━━",
            callback_data=f"vpn:group:{group.id}",
        )])
        for product in products:
            callback = f"vpn:product:{product.id}"
            buttons.append([
                InlineKeyboardButton(text=product.name, callback_data=callback),
                InlineKeyboardButton(text=f"{product.price:,} تومان", callback_data=callback),
            ])
    buttons.append([InlineKeyboardButton(
        text="🏠 بازگشت به لیست سرورها", callback_data="vpn:buy"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vpn_username_keyboard(category_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 خودکار انتخاب کن", callback_data="vpn:username:auto")
    ], [InlineKeyboardButton(text="✏️ وارد کردن نام", callback_data="vpn:username:manual")], [
        InlineKeyboardButton(text="🔙 بازگشت به محصولات", callback_data=f"vpn:category:{category_id}")
    ]])


def vpn_invoice_keyboard(order_number: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 کد تخفیف", callback_data=f"checkout:coupon:{order_number}")],
        [InlineKeyboardButton(text="💳 کارت‌به‌کارت", callback_data=f"checkout:skip:{order_number}")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="vpn:home")],
    ])


def vpn_services_keyboard(services):
    buttons = []
    for order, detail in services:
        status = "🟢" if detail.provisioning_status == "delivered" and order.status == "paid" else "🟡" if detail.provisioning_status in {"pending", "provisioning"} else "⚠️"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {detail.username} | {order.product_name}",
            callback_data=f"vpn:service:{order.id}",
        )])
    buttons.append([InlineKeyboardButton(text="🏠 بازگشت به منوی VPN", callback_data="vpn:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vpn_service_detail_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 دریافت لینک اشتراک", callback_data=f"vpn:link:order:{order_id}")],
        [InlineKeyboardButton(text="📷 دریافت QR Code", callback_data=f"vpn:qr:order:{order_id}")],
        [InlineKeyboardButton(text="🔄 تمدید سرویس", callback_data=f"vpn:renew:{order_id}")],
        [InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="support:menu:vpn")],
        [InlineKeyboardButton(text="🔙 بازگشت به سرویس‌های من", callback_data="vpn:services")],
    ])


def vpn_tutorial_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 آموزش اندروید", callback_data="vpn:tutorial:android")],
        [InlineKeyboardButton(text="🍎 آموزش آیفون (iOS)", callback_data="vpn:tutorial:ios")],
        [InlineKeyboardButton(text="💻 آموزش ویندوز", callback_data="vpn:tutorial:windows")],
        [InlineKeyboardButton(text="🖥 آموزش مک (MacOS)", callback_data="vpn:tutorial:macos")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی VPN", callback_data="vpn:home")],
    ])


def vpn_tutorial_detail_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="support:menu:vpn")],
        [InlineKeyboardButton(text="🔙 بازگشت به آموزش‌ها", callback_data="vpn:tutorial")],
    ])


def vpn_wallet_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 افزایش اعتبار", callback_data="vpn:wallet:topup")],
        [InlineKeyboardButton(text="📜 تاریخچه تراکنش‌ها", callback_data="vpn:wallet:history")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی VPN", callback_data="vpn:home")],
    ])


def vpn_partnership_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 ثبت درخواست همکاری", callback_data="vpn:partnership:new")],
        [InlineKeyboardButton(text="🎧 ارتباط با پشتیبانی", callback_data="support:menu:vpn")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی VPN", callback_data="vpn:home")],
    ])


def vpn_referral_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 اشتراک‌گذاری لینک دعوت", callback_data="vpn:referral:share")],
        [InlineKeyboardButton(text="👥 دوستان دعوت‌شده", callback_data="vpn:referral:friends")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی VPN", callback_data="vpn:home")],
    ])
