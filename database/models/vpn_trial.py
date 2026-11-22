from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class VPNTrialSettings(Base):
    __tablename__ = "vpn_trial_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    panel_id: Mapped[int | None] = mapped_column(ForeignKey("vpn_panels.id", ondelete="SET NULL"), nullable=True)
    inbound_id: Mapped[int | None] = mapped_column(ForeignKey("vpn_inbounds.id", ondelete="SET NULL"), nullable=True)
    volume_gb: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class VPNTrialClaim(Base):
    __tablename__ = "vpn_trial_claims"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    panel_id: Mapped[int | None] = mapped_column(ForeignKey("vpn_panels.id", ondelete="SET NULL"), nullable=True)
    inbound_id: Mapped[int | None] = mapped_column(ForeignKey("vpn_inbounds.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
