from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Coupon, CouponUsage, Order


class CouponNotFoundError(Exception): pass
class CouponInactiveError(Exception): pass
class CouponExpiredError(Exception): pass
class CouponNotStartedError(Exception): pass
class CouponMinimumAmountError(Exception): pass
class CouponUsageLimitError(Exception): pass
class CouponUserLimitError(Exception): pass
class CouponOrderStatusError(Exception): pass
class CouponAlreadyUsedError(Exception): pass


async def create_coupon(
    session: AsyncSession, code: str, discount_type: str, discount_value: int,
    min_order_amount: int = 0, max_discount_amount: int | None = None,
    usage_limit: int | None = None, per_user_limit: int = 1,
    starts_at=None, expires_at=None,
):
    code = code.strip().upper()
    if not code: raise ValueError("Coupon code cannot be empty")
    if discount_type not in ("percent", "fixed"): raise ValueError("Invalid discount type")
    if discount_value <= 0 or (discount_type == "percent" and discount_value > 100):
        raise ValueError("Invalid discount value")
    if min_order_amount < 0: raise ValueError("Invalid minimum amount")
    if max_discount_amount is not None and max_discount_amount <= 0: raise ValueError("Invalid maximum discount")
    if usage_limit is not None and usage_limit <= 0: raise ValueError("Invalid usage limit")
    if per_user_limit <= 0: raise ValueError("Invalid user limit")
    if starts_at and expires_at and starts_at >= expires_at: raise ValueError("Invalid coupon date range")

    coupon = Coupon(
        code=code, discount_type=discount_type, discount_value=discount_value,
        min_order_amount=min_order_amount, max_discount_amount=max_discount_amount,
        usage_limit=usage_limit, per_user_limit=per_user_limit,
        starts_at=starts_at, expires_at=expires_at, is_active=True,
    )
    session.add(coupon)
    try:
        await session.commit(); await session.refresh(coupon)
    except IntegrityError:
        await session.rollback(); raise ValueError("Coupon code already exists")
    return coupon


async def get_coupon(session: AsyncSession, code: str, lock: bool = False):
    query = select(Coupon).where(Coupon.code == code.strip().upper())
    if lock: query = query.with_for_update()
    coupon = (await session.execute(query)).scalar_one_or_none()
    if not coupon: raise CouponNotFoundError()
    return coupon


async def get_coupon_usage_count(session: AsyncSession, coupon_id: int):
    return (await session.execute(select(func.count(CouponUsage.id)).where(CouponUsage.coupon_id == coupon_id))).scalar_one()


async def get_user_coupon_usage_count(session: AsyncSession, coupon_id: int, telegram_user_id: int):
    return (await session.execute(select(func.count(CouponUsage.id)).where(
        CouponUsage.coupon_id == coupon_id,
        CouponUsage.telegram_user_id == telegram_user_id,
    ))).scalar_one()


async def validate_coupon(session: AsyncSession, coupon: Coupon, order: Order, telegram_user_id: int):
    now = datetime.now(timezone.utc)
    if not coupon.is_active: raise CouponInactiveError()
    if coupon.starts_at and coupon.starts_at > now: raise CouponNotStartedError()
    if coupon.expires_at and coupon.expires_at <= now: raise CouponExpiredError()
    if order.product_price < coupon.min_order_amount: raise CouponMinimumAmountError()
    if coupon.usage_limit is not None and await get_coupon_usage_count(session, coupon.id) >= coupon.usage_limit:
        raise CouponUsageLimitError()
    if await get_user_coupon_usage_count(session, coupon.id, telegram_user_id) >= coupon.per_user_limit:
        raise CouponUserLimitError()
    return True


def calculate_discount(coupon: Coupon, product_price: int):
    discount = product_price * coupon.discount_value // 100 if coupon.discount_type == "percent" else coupon.discount_value
    if coupon.max_discount_amount is not None: discount = min(discount, coupon.max_discount_amount)
    return min(discount, product_price)


async def apply_coupon_to_order(session: AsyncSession, order_number: str, telegram_user_id: int, code: str):
    order = (await session.execute(select(Order).where(
        Order.order_number == order_number,
        Order.telegram_user_id == telegram_user_id,
    ).with_for_update())).scalar_one_or_none()
    if not order: raise ValueError("Order not found")
    if order.status != "awaiting_discount": raise CouponOrderStatusError()
    coupon = await get_coupon(session, code, lock=True)
    await validate_coupon(session, coupon, order, telegram_user_id)
    discount = calculate_discount(coupon, order.product_price)
    if discount <= 0: raise ValueError("Invalid discount amount")
    order.discount_code = coupon.code
    order.discount_amount = discount
    order.final_amount = order.product_price - discount
    order.status = "awaiting_payment"
    await session.commit(); await session.refresh(order)
    return order


async def record_coupon_usage(session: AsyncSession, order: Order):
    if not order.discount_code: return None
    existing = (await session.execute(select(CouponUsage).where(CouponUsage.order_id == order.id))).scalar_one_or_none()
    if existing: return existing
    coupon = await get_coupon(session, order.discount_code, lock=True)
    if coupon.usage_limit is not None and await get_coupon_usage_count(session, coupon.id) >= coupon.usage_limit:
        raise CouponUsageLimitError()
    if await get_user_coupon_usage_count(session, coupon.id, order.telegram_user_id) >= coupon.per_user_limit:
        raise CouponUserLimitError()
    usage = CouponUsage(coupon_id=coupon.id, order_id=order.id, telegram_user_id=order.telegram_user_id)
    session.add(usage)
    return usage
