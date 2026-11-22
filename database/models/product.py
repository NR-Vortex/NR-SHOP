from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from database.base import Base


class Product(Base):

    __tablename__ = "products"

    __table_args__ = (

        CheckConstraint(
            "price >= 0",
            name="price_non_negative"
        ),

        CheckConstraint(
            "duration_days IS NULL OR duration_days > 0",
            name="duration_days_positive"
        ),

        UniqueConstraint(
            "category_id",
            "name",
            name="category_product_name"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    group_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_groups.id",
            ondelete="RESTRICT"
        ),
        nullable=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    # مدت اعتبار محصول به روز
    duration_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # نوع سرویس
    service_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # روش تحویل یا فعال سازی
    delivery_method: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # AI delivery mode: shared or dedicated
    account_type: Mapped[str] = mapped_column(
        String(16), default="shared", server_default="shared", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    category = relationship(
        "Category",
        back_populates="products"
    )

    group = relationship(
        "ProductGroup",
        back_populates="products"
    )

    vpn_inbounds = relationship("ProductVPNInbound", back_populates="product", passive_deletes=True)
