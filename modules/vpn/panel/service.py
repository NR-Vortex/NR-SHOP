from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import VPNInbound, VPNPanel
from modules.vpn.panel.client import ThreeXUIClient, encrypt_password, sanitize_inbound


async def save_panel(session: AsyncSession, name: str, base_url: str, username: str, password: str):
    panel = VPNPanel(name=name.strip(), base_url=base_url.strip().rstrip("/"), username=username.strip(), encrypted_password=encrypt_password(password), connection_status="unknown")
    session.add(panel); await session.flush(); await session.refresh(panel)
    return panel


async def sync_panel_inbounds(session: AsyncSession, panel: VPNPanel):
    async with ThreeXUIClient(panel.base_url, panel.username, panel.encrypted_password) as client:
        raw_inbounds = await client.list_inbounds()
    existing = {x.remote_inbound_id: x for x in (await session.execute(select(VPNInbound).where(VPNInbound.panel_id == panel.id))).scalars().all()}
    seen = set()
    for raw in raw_inbounds:
        data = sanitize_inbound(raw); seen.add(data["id"])
        inbound = existing.get(data["id"])
        if inbound is None: inbound = VPNInbound(panel_id=panel.id, remote_inbound_id=data["id"]); session.add(inbound)
        inbound.remark = data["remark"]; inbound.protocol = data["protocol"]; inbound.port = data["port"]; inbound.enabled = data["enable"]; inbound.raw_metadata = data["metadata"]
    for inbound in existing.values():
        if inbound.remote_inbound_id not in seen: inbound.enabled = False
    panel.connection_status = "connected"; panel.last_checked_at = datetime.now(timezone.utc)
    await session.commit()
