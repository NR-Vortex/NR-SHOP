from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Referral

async def register_referral(session: AsyncSession, referrer_id: int, referred_id: int):
    if referrer_id == referred_id: return False
    exists = (await session.execute(select(Referral.id).where(Referral.referred_user_id == referred_id))).scalar_one_or_none()
    if exists: return False
    session.add(Referral(referrer_user_id=referrer_id, referred_user_id=referred_id))
    try: await session.commit(); return True
    except Exception:
        await session.rollback(); return False

async def referral_stats(session: AsyncSession, user_id: int):
    rows = (await session.execute(select(Referral.referred_user_id, Referral.created_at).where(Referral.referrer_user_id == user_id).order_by(Referral.id.desc()))).all()
    return rows
