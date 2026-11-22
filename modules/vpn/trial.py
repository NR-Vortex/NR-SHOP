from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database.models import VPNTrialClaim, VPNTrialSettings


async def get_trial_settings(session):
    settings = (await session.execute(select(VPNTrialSettings).where(VPNTrialSettings.id == 1))).scalar_one_or_none()
    return settings or VPNTrialSettings(id=1)


async def claim_trial(session, user_id: int):
    settings = await get_trial_settings(session)
    if not settings.is_enabled: return None, "disabled"
    existing = (await session.execute(select(VPNTrialClaim).where(VPNTrialClaim.telegram_user_id == user_id))).scalar_one_or_none()
    if existing: return existing, "claimed"
    claim = VPNTrialClaim(telegram_user_id=user_id, panel_id=settings.panel_id, inbound_id=settings.inbound_id)
    session.add(claim)
    try: await session.commit(); await session.refresh(claim)
    except IntegrityError:
        await session.rollback(); return None, "claimed"
    return claim, "created"


async def trial_statistics(session):
    total = (await session.execute(select(func.count(VPNTrialClaim.id)))).scalar_one()
    return {"total": total, "active": 0, "expired": 0}
