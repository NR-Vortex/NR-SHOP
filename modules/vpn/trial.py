import logging
import secrets
from datetime import datetime,timedelta,timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from database.models import VPNTrialClaim, VPNTrialSettings
from modules.vpn.provisioning import configured_inbound,deliver_subscription,ProvisioningError

logger=logging.getLogger(__name__)


async def get_trial_settings(session):
    settings=await session.get(VPNTrialSettings,1)
    return settings or VPNTrialSettings(id=1)


def trial_available(settings):
    return bool(settings.is_enabled and settings.panel_id and settings.inbound_id
                and settings.volume_gb and 0<settings.volume_gb<=999999
                and settings.duration_hours and 0<settings.duration_hours<=8760)


def claim_query(user_id):
    return select(VPNTrialClaim).where(VPNTrialClaim.telegram_user_id==user_id)


async def claim_trial(session,user_id):
    query=claim_query(user_id)
    claim=await session.scalar(query)
    if claim and claim.subscription_url:
        return claim,"ready"
    settings=await get_trial_settings(session)
    if not trial_available(settings):
        return None,"disabled"
    try:
        _,inbound=await configured_inbound(session,settings.inbound_id)
        if inbound.panel_id!=settings.panel_id:
            raise ProvisioningError("Trial inbound belongs to a different panel")
        await session.execute(insert(VPNTrialClaim).values(telegram_user_id=user_id,panel_id=settings.panel_id,inbound_id=settings.inbound_id)
                              .on_conflict_do_nothing(index_elements=[VPNTrialClaim.telegram_user_id]))
        claim=await session.scalar(query.with_for_update().execution_options(populate_existing=True))
        if claim.subscription_url:
            return claim,"ready"
        if not claim.client_id:
            claim.panel_id=settings.panel_id
            claim.inbound_id=settings.inbound_id
            claim.client_id=str(uuid4())
            claim.subscription_id=secrets.token_hex(12)
            claim.expires_at=datetime.now(timezone.utc)+timedelta(hours=settings.duration_hours)
            claim.volume_gb=settings.volume_gb
        await session.commit()

        claim=await session.scalar(query.with_for_update().execution_options(populate_existing=True))
        if not claim.subscription_url:
            if claim.expires_at<=datetime.now(timezone.utc):
                return claim,"expired"
            panel,inbound=await configured_inbound(session,claim.inbound_id)
            claim.subscription_url=await deliver_subscription(panel,inbound,claim.client_id,claim.subscription_id,
                f"nr-trial-{claim.id}",claim.volume_gb,claim.expires_at)
            await session.commit()
        return claim,"ready"
    except Exception as error:
        await session.rollback()
        logger.warning("VPN trial provisioning failed (%s)",type(error).__name__)
        return None,"failed"


async def trial_statistics(session):
    total,active,expired=(await session.execute(select(
        func.count(VPNTrialClaim.id).filter(VPNTrialClaim.subscription_url.is_not(None)),
        func.count(VPNTrialClaim.id).filter(VPNTrialClaim.subscription_url.is_not(None),VPNTrialClaim.expires_at>func.now()),
        func.count(VPNTrialClaim.id).filter(VPNTrialClaim.subscription_url.is_not(None),VPNTrialClaim.expires_at<=func.now())
    ))).one()
    return {"total":total,"active":active,"expired":expired}
