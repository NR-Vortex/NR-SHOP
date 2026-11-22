from datetime import datetime
from typing import List

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from database.base import Base


class Category(Base):

    __tablename__ = "categories"

    __table_args__ = (
        UniqueConstraint(
            "section",
            "name",
            name="uq_categories_section_name"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # بخش اصلی فروشگاه
    section: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="ai",
        index=True
    )

    # نام دسته بندی
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
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

    products: Mapped[List["Product"]] = relationship(
        back_populates="category",
        passive_deletes=True
    )

    groups: Mapped[List["ProductGroup"]] = relationship(
        back_populates="category",
        passive_deletes=True
    )
