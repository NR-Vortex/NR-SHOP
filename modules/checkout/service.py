from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Order,
    Product,
    Category,
    ProductGroup
)


# ==============================
# ORDER STATUSES
# ==============================

AWAITING_DISCOUNT = "awaiting_discount"
AWAITING_PAYMENT = "awaiting_payment"
UNDER_REVIEW = "under_review"
PAID = "paid"
REJECTED = "rejected"
CANCELLED = "cancelled"


# ==============================
# EXCEPTIONS
# ==============================

class OrderNotFoundError(Exception):
    pass


class ProductUnavailableError(Exception):
    pass


class OrderStatusError(Exception):
    pass


class InvalidDiscountError(Exception):
    pass


# ==============================
# CREATE ORDER
# ==============================

async def create_order(
    session: AsyncSession,
    telegram_user_id: int,
    product_id: int
):

    # دریافت محصول
    result = await session.execute(
        select(Product).where(
            Product.id == product_id
        )
    )

    product = result.scalar_one_or_none()

    if not product:
        raise ProductUnavailableError(
            "Product does not exist"
        )

    if not product.is_active:
        raise ProductUnavailableError(
            "Product is disabled"
        )

    # بررسی دسته بندی
    result = await session.execute(
        select(Category).where(
            Category.id == product.category_id
        )
    )

    category = result.scalar_one_or_none()

    if not category or not category.is_active:
        raise ProductUnavailableError(
            "Category is unavailable"
        )

    # بررسی گروه
    if product.group_id is not None:

        result = await session.execute(
            select(ProductGroup).where(
                ProductGroup.id == product.group_id
            )
        )

        group = result.scalar_one_or_none()

        if not group or not group.is_active:
            raise ProductUnavailableError(
                "Product group is unavailable"
            )

    # ایجاد سفارش با اطلاعات ثابت محصول
    order = Order(

        telegram_user_id=telegram_user_id,

        product_id=product.id,

        product_name=product.name,

        product_price=product.price,

        duration_days=product.duration_days,

        service_type=product.service_type,

        delivery_method=product.delivery_method,

        discount_amount=0,

        final_amount=product.price,

        currency="TOMAN",

        status=AWAITING_DISCOUNT
    )

    session.add(order)

    await session.commit()

    await session.refresh(order)

    return order


# ==============================
# GET ORDER
# ==============================

async def get_order(
    session: AsyncSession,
    order_id: int
):

    result = await session.execute(
        select(Order).where(
            Order.id == order_id
        )
    )

    order = result.scalar_one_or_none()

    if not order:
        raise OrderNotFoundError()

    return order


# ==============================
# GET USER ORDER
# ==============================

async def get_user_order(
    session: AsyncSession,
    order_number: str,
    telegram_user_id: int
):

    result = await session.execute(
        select(Order).where(
            Order.order_number == order_number,
            Order.telegram_user_id == telegram_user_id
        )
    )

    order = result.scalar_one_or_none()

    if not order:
        raise OrderNotFoundError()

    return order


# ==============================
# APPLY DISCOUNT
# ==============================

async def apply_order_discount(
    session: AsyncSession,
    order_id: int,
    discount_code: str,
    discount_amount: int
):

    order = await get_order(
        session,
        order_id
    )

    if order.status != AWAITING_DISCOUNT:
        raise OrderStatusError()

    if discount_amount < 0:
        raise InvalidDiscountError()

    if discount_amount > order.product_price:
        raise InvalidDiscountError()

    order.discount_code = discount_code.strip().upper()

    order.discount_amount = discount_amount

    order.final_amount = (
        order.product_price - discount_amount
    )

    order.status = AWAITING_PAYMENT

    await session.commit()

    await session.refresh(order)

    return order


# ==============================
# CONTINUE WITHOUT DISCOUNT
# ==============================

async def continue_without_discount(
    session: AsyncSession,
    order_id: int
):

    order = await get_order(
        session,
        order_id
    )

    if order.status != AWAITING_DISCOUNT:
        raise OrderStatusError()

    order.discount_amount = 0

    order.final_amount = order.product_price

    order.status = AWAITING_PAYMENT

    await session.commit()

    await session.refresh(order)

    return order


# ==============================
# SUBMIT PAYMENT RECEIPT
# ==============================

async def submit_receipt(
    session: AsyncSession,
    order_number: str,
    telegram_user_id: int,
    receipt_file_id: str,
    receipt_type: str = "document"
):

    order = await get_user_order(
        session,
        order_number,
        telegram_user_id
    )

    if order.status != AWAITING_PAYMENT:
        raise OrderStatusError()

    if not receipt_file_id:
        raise ValueError("Receipt file is required")

    if receipt_type not in ("photo", "document"):
        raise ValueError("Invalid receipt type")

    order.receipt_file_id = receipt_file_id
    order.receipt_type = receipt_type

    order.status = UNDER_REVIEW

    await session.commit()

    await session.refresh(order)

    return order


# ==============================
# ADMIN APPROVE ORDER
# ==============================

async def approve_order(
    session: AsyncSession,
    order_id: int,
    admin_note: str | None = None
):

    result = await session.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()

    if not order:
        raise OrderNotFoundError()

    if order.status != UNDER_REVIEW:
        raise OrderStatusError()

    if order.discount_code:
        from modules.checkout.coupon import record_coupon_usage
        await record_coupon_usage(session, order)

    order.paid_at = func.now()
    order.status = PAID

    order.admin_note = admin_note

    await session.commit()

    await session.refresh(order)

    return order


# ==============================
# ADMIN REJECT ORDER
# ==============================

async def reject_order(
    session: AsyncSession,
    order_id: int,
    admin_note: str
):

    order = await get_order(
        session,
        order_id
    )

    if order.status != UNDER_REVIEW:
        raise OrderStatusError()

    if not admin_note.strip():
        raise ValueError("Rejection reason is required")

    order.status = REJECTED

    order.admin_note = admin_note

    await session.commit()

    await session.refresh(order)

    return order


# ==============================
# CANCEL ORDER
# ==============================

async def cancel_order(
    session: AsyncSession,
    order_number: str,
    telegram_user_id: int
):

    order = await get_user_order(
        session,
        order_number,
        telegram_user_id
    )

    if order.status not in (
        AWAITING_DISCOUNT,
        AWAITING_PAYMENT
    ):
        raise OrderStatusError()

    order.status = CANCELLED

    await session.commit()

    return order
