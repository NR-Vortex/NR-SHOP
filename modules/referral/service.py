import re

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Referral
from database.models.referral import PendingReferral

REFERRAL_COMMAND = re.compile(r"^/start(?:@[A-Za-z0-9_]+)?\s+ref_([0-9]{1,19})\s*$")


def parse_start_referrer(text):
    match = REFERRAL_COMMAND.fullmatch(text or "")
    if not match:
        return None
    referrer = int(match[1])
    return referrer if 0 < referrer < 2**63 else None


async def remember_referral(session: AsyncSession, referrer_id: int, referred_id: int):
    if referrer_id == referred_id:
        return
    await session.execute(
        insert(PendingReferral)
        .values(referrer_user_id=referrer_id,referred_user_id=referred_id)
        .on_conflict_do_nothing(index_elements=[PendingReferral.referred_user_id])
    )
    await session.commit()


async def complete_referral(session: AsyncSession, referred_id: int):
    referrer = await session.scalar(
        delete(PendingReferral)
        .where(PendingReferral.referred_user_id==referred_id)
        .returning(PendingReferral.referrer_user_id)
    )
    if referrer is None:
        return False
    result = await session.execute(
        insert(Referral)
        .values(referrer_user_id=referrer,referred_user_id=referred_id)
        .on_conflict_do_nothing(index_elements=[Referral.referred_user_id])
        .returning(Referral.id)
    )
    created = result.scalar_one_or_none() is not None
    await session.commit()
    return created


async def referral_summary(session: AsyncSession, user_id: int):
    query=select(Referral.referred_user_id,Referral.created_at).where(Referral.referrer_user_id==user_id)
    rows=(await session.execute(query.order_by(Referral.id.desc()).limit(25))).all()
    count=await session.scalar(select(func.count(Referral.id)).where(Referral.referrer_user_id==user_id))
    return count,rows
