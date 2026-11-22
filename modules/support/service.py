from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, SupportMessage, SupportTicket


class TicketNotFoundError(Exception): pass
class TicketClosedError(Exception): pass
class TicketAccessError(Exception): pass
class InvalidMessageError(Exception): pass


async def create_ticket(session: AsyncSession, telegram_user_id: int, initial_text: str,
                        subject: str = "درخواست پشتیبانی", source_section: str = "general",
                        order_id: int | None = None):
    if not initial_text or not initial_text.strip(): raise InvalidMessageError()
    if order_id is not None:
        result = await session.execute(select(Order.id).where(
            Order.id == order_id, Order.telegram_user_id == telegram_user_id
        ))
        if result.scalar_one_or_none() is None: raise TicketAccessError()
    ticket = SupportTicket(
        telegram_user_id=telegram_user_id, order_id=order_id,
        subject=subject, source_section=source_section, status="waiting_admin",
    )
    session.add(ticket); await session.flush()
    session.add(SupportMessage(
        ticket_id=ticket.id, sender_id=telegram_user_id, sender_type="customer",
        message_type="text", text=initial_text.strip(),
    ))
    await session.commit(); await session.refresh(ticket)
    return ticket


async def get_ticket(session: AsyncSession, ticket_number: str):
    ticket = (await session.execute(select(SupportTicket).where(
        SupportTicket.ticket_number == ticket_number
    ))).scalar_one_or_none()
    if not ticket: raise TicketNotFoundError()
    return ticket


async def get_customer_ticket(session: AsyncSession, ticket_number: str, telegram_user_id: int):
    ticket = (await session.execute(select(SupportTicket).where(
        SupportTicket.ticket_number == ticket_number,
        SupportTicket.telegram_user_id == telegram_user_id,
    ))).scalar_one_or_none()
    if not ticket: raise TicketNotFoundError()
    return ticket


async def add_message(session: AsyncSession, ticket_number: str, sender_id: int,
                      sender_type: str, text: str | None = None,
                      message_type: str = "text", file_id: str | None = None,
                      file_name: str | None = None, mime_type: str | None = None):
    if sender_type not in ("customer", "admin", "system") or (not text and not file_id):
        raise InvalidMessageError()
    ticket = (await session.execute(select(SupportTicket).where(
        SupportTicket.ticket_number == ticket_number
    ).with_for_update())).scalar_one_or_none()
    if not ticket: raise TicketNotFoundError()
    if ticket.status == "closed": raise TicketClosedError()
    if sender_type == "customer" and ticket.telegram_user_id != sender_id:
        raise TicketAccessError()
    message = SupportMessage(
        ticket_id=ticket.id, sender_id=sender_id, sender_type=sender_type,
        message_type=message_type, text=text, file_id=file_id,
        file_name=file_name, mime_type=mime_type,
    )
    session.add(message)
    if sender_type == "customer": ticket.status = "waiting_admin"
    elif sender_type == "admin":
        ticket.status = "waiting_user"; ticket.assigned_admin_id = sender_id
    await session.commit(); await session.refresh(message)
    return message


async def get_ticket_messages(session: AsyncSession, ticket_number: str):
    ticket = await get_ticket(session, ticket_number)
    result = await session.execute(select(SupportMessage).where(
        SupportMessage.ticket_id == ticket.id
    ).order_by(SupportMessage.created_at.asc()))
    return result.scalars().all()


async def get_customer_tickets(session: AsyncSession, telegram_user_id: int, limit: int = 20):
    result = await session.execute(select(SupportTicket).where(
        SupportTicket.telegram_user_id == telegram_user_id
    ).order_by(SupportTicket.created_at.desc()).limit(limit))
    return result.scalars().all()


async def get_admin_tickets(session: AsyncSession, limit: int = 50):
    result = await session.execute(select(SupportTicket).where(
        SupportTicket.status.in_(["open", "waiting_admin", "waiting_user"])
    ).order_by(SupportTicket.created_at.asc()).limit(limit))
    return result.scalars().all()


async def close_ticket(session: AsyncSession, ticket_number: str):
    ticket = await get_ticket(session, ticket_number)
    if ticket.status == "closed": raise TicketClosedError()
    ticket.status = "closed"; ticket.closed_at = datetime.now(timezone.utc)
    await session.commit(); await session.refresh(ticket)
    return ticket


async def reopen_ticket(session: AsyncSession, ticket_number: str):
    ticket = await get_ticket(session, ticket_number)
    if ticket.status != "closed": raise ValueError("Ticket is not closed")
    ticket.status = "waiting_admin"; ticket.closed_at = None
    await session.commit(); await session.refresh(ticket)
    return ticket
