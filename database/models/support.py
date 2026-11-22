from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


def generate_ticket_number():
    return f"NR-T{uuid4().hex[:10].upper()}"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'waiting_admin', 'waiting_user', 'closed')",
            name="valid_ticket_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, default=generate_ticket_number
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_section: Mapped[str] = mapped_column(
        String(50), default="general", server_default="general", nullable=False
    )
    subject: Mapped[str] = mapped_column(
        String(150), default="درخواست پشتیبانی", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="open", server_default="open", nullable=False, index=True
    )
    assigned_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages = relationship(
        "SupportMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SupportMessage.created_at",
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('customer', 'admin', 'system')",
            name="valid_sender_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(20), default="text", server_default="text", nullable=False
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket = relationship("SupportTicket", back_populates="messages")
