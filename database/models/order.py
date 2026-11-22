from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from database.base import Base


def generate_order_number():
    return f"NR{uuid4().hex[:12].upper()}"


class Order(Base):

    __tablename__ = "orders"

    __table_args__ = (

        CheckConstraint(
            "product_price >= 0",
            name="product_price_non_negative"
        ),

        CheckConstraint(
            "discount_amount >= 0",
            name="discount_non_negative"
        ),

        CheckConstraint(
            "final_amount >= 0",
            name="final_amount_non_negative"
        ),

        CheckConstraint(
            "discount_amount <= product_price",
            name="discount_not_exceed_price"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    order_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        default=generate_order_number
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )

    product_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    product_price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    duration_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    service_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    delivery_method: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    discount_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True
    )

    discount_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default="0",
        nullable=False
    )

    final_amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(12),
        default="TOMAN",
        server_default="TOMAN",
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="awaiting_payment",
        server_default="awaiting_payment",
        nullable=False,
        index=True
    )

    receipt_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    receipt_type: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True
    )

    admin_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
