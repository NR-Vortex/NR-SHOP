from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Coupon(Base):
    __tablename__ = "coupons"

    __table_args__ = (
        CheckConstraint(
            """
            (discount_type = 'percent' AND discount_value BETWEEN 1 AND 100)
            OR
            (discount_type = 'fixed' AND discount_value > 0)
            """,
            name="valid_discount",
        ),
        CheckConstraint("min_order_amount >= 0", name="minimum_order_non_negative"),
        CheckConstraint(
            "max_discount_amount IS NULL OR max_discount_amount > 0",
            name="max_discount_positive",
        ),
        CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="usage_limit_positive",
        ),
        CheckConstraint("per_user_limit > 0", name="per_user_limit_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    discount_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    min_order_amount: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )
    max_discount_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_user_limit: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    usages = relationship("CouponUsage", back_populates="coupon", passive_deletes=True)


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    __table_args__ = (
        UniqueConstraint("order_id", name="uq_coupon_usages_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coupon_id: Mapped[int] = mapped_column(
        ForeignKey("coupons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    coupon = relationship("Coupon", back_populates="usages")
