import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, VPNInbound, VPNOrderDetails, VPNPanel
from modules.vpn.panel.client import ThreeXUIClient


class ProvisioningError(Exception): pass


async def provision_vpn_order(session: AsyncSession, order_id: int):
    result = await session.execute(select(VPNOrderDetails).where(
        VPNOrderDetails.order_id == order_id
    ).with_for_update())
    detail = result.scalar_one_or_none()
    if not detail: return None
    if detail.provisioning_status == "delivered": return detail
    if detail.inbound_id is None:
        detail.provisioning_status = "failed"; detail.provisioning_error = "No inbound selected"; await session.commit(); raise ProvisioningError("No inbound selected")
    inbound = (await session.execute(select(VPNInbound).where(VPNInbound.id == detail.inbound_id))).scalar_one_or_none()
    if not inbound or not inbound.enabled: raise ProvisioningError("Inbound unavailable")
    panel = (await session.execute(select(VPNPanel).where(VPNPanel.id == inbound.panel_id, VPNPanel.is_active.is_(True)))).scalar_one_or_none()
    if not panel: raise ProvisioningError("Panel unavailable")
    detail.provisioning_status = "provisioning"; await session.commit()
    client_uuid = str(uuid.uuid4())
    try:
        async with ThreeXUIClient(panel.base_url, panel.username, panel.encrypted_password) as api:
            await api.add_client(inbound.remote_inbound_id, {"id": client_uuid, "email": detail.username, "enable": True})
        detail.panel_client_id = client_uuid
        detail.provisioning_status = "delivered"
        detail.provisioned_at = datetime.now(timezone.utc)
        detail.provisioning_error = None
        await session.commit(); await session.refresh(detail)
        return detail
    except Exception as exc:
        detail.provisioning_status = "failed"
        detail.provisioning_error = str(exc)[:500]
        await session.commit()
        raise ProvisioningError("VPN provisioning failed") from exc
