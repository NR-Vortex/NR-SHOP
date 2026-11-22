from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class VPNPanel(Base):
    __tablename__ = "vpn_panels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    connection_status: Mapped[str] = mapped_column(String(30), default="unknown", server_default="unknown", nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    inbounds = relationship("VPNInbound", back_populates="panel", passive_deletes=True)


class VPNInbound(Base):
    __tablename__ = "vpn_inbounds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("vpn_panels.id", ondelete="CASCADE"), nullable=False, index=True)
    remote_inbound_id: Mapped[int] = mapped_column(Integer, nullable=False)
    remark: Mapped[str] = mapped_column(String(200), default="", server_default="", nullable=False)
    protocol: Mapped[str] = mapped_column(String(50), default="", server_default="", nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    raw_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    panel = relationship("VPNPanel", back_populates="inbounds")
    products = relationship("ProductVPNInbound", back_populates="inbound", passive_deletes=True)
    __table_args__ = (UniqueConstraint("panel_id", "remote_inbound_id", name="uq_vpn_inbound_panel_remote"),)


class ProductVPNInbound(Base):
    __tablename__ = "product_vpn_inbounds"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    inbound_id: Mapped[int] = mapped_column(ForeignKey("vpn_inbounds.id", ondelete="RESTRICT"), primary_key=True)
    product = relationship("Product", back_populates="vpn_inbounds")
    inbound = relationship("VPNInbound", back_populates="products")
