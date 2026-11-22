from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class VPNOrderDetails(Base):
    __tablename__ = "vpn_order_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    inbound_id: Mapped[int | None] = mapped_column(ForeignKey("vpn_inbounds.id", ondelete="SET NULL"), nullable=True, index=True)
    provisioning_status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending", nullable=False, index=True)
    panel_client_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subscription_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    provisioning_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    server_name: Mapped[str] = mapped_column(String(100), default="در انتظار تخصیص", server_default="در انتظار تخصیص", nullable=False)
    volume: Mapped[str] = mapped_column(String(50), default="نامشخص", server_default="نامشخص", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    order = relationship("Order")
