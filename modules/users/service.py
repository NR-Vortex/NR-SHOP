from datetime import datetime, timezone
from sqlalchemy import select
from database.models import User, UserAuditLog

async def upsert_user(session, telegram_user):
    user = (await session.execute(select(User).where(User.telegram_id == telegram_user.id))).scalar_one_or_none()
    if user is None: user = User(telegram_id=telegram_user.id); session.add(user)
    user.full_name = telegram_user.full_name or ""
    user.username = telegram_user.username
    await session.commit(); return user

async def set_blocked(session, telegram_id, admin_id, blocked, reason=None):
    user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if user is None: user = User(telegram_id=telegram_id); session.add(user)
    user.is_blocked = blocked; user.blocked_by = admin_id if blocked else None; user.blocked_reason = reason if blocked else None; user.blocked_at = datetime.now(timezone.utc) if blocked else None
    session.add(UserAuditLog(user_id=telegram_id, admin_id=admin_id, action="block" if blocked else "unblock", details=reason)); await session.commit(); return user
