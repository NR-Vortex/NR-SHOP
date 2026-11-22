import json
import logging
import secrets
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from urllib.parse import quote

from sqlalchemy import select

from core.admin_settings import read_setting
from database.models import Order, Product, ProductVPNInbound, VPNInbound, VPNOrderDetails, VPNPanel
from modules.vpn.panel.client import ThreeXUIClient

logger=logging.getLogger(__name__)
SUPPORTED_PROTOCOLS=("vless","vmess")


class ProvisioningError(Exception):
    pass


async def linked_inbound(session,product_id):
    return await session.scalar(
        select(VPNInbound).join(ProductVPNInbound,ProductVPNInbound.inbound_id==VPNInbound.id)
        .join(VPNPanel,VPNPanel.id==VPNInbound.panel_id)
        .where(ProductVPNInbound.product_id==product_id,VPNInbound.enabled,VPNPanel.is_active,
               VPNInbound.protocol.in_(SUPPORTED_PROTOCOLS))
        .order_by(VPNInbound.id).limit(1)
    )


async def configured_inbound(session,inbound_id):
    row=(await session.execute(select(VPNPanel,VPNInbound).join(VPNInbound)
        .where(VPNInbound.id==inbound_id,VPNInbound.enabled,VPNPanel.is_active,
               VPNInbound.protocol.in_(SUPPORTED_PROTOCOLS)))).first()
    if not row:
        raise ProvisioningError("No active VPN inbound")
    return row


async def deliver_subscription(panel,inbound,client_id,subscription_id,email,volume_gb,expires_at):
    async with ThreeXUIClient(panel.base_url,panel.username,panel.encrypted_password) as api:
        remote=next((item for item in await api.list_inbounds() if item["id"]==inbound.remote_inbound_id
                     and item.get("enable") and item.get("protocol") in SUPPORTED_PROTOCOLS),None)
        if remote is None:
            raise ProvisioningError("Inbound is disabled or missing from panel")
        base=read_setting(f"agency_subscription:{inbound.id}") or await api.subscription_base()
        settings=remote["settings"]
        clients=(json.loads(settings) if isinstance(settings,str) else settings).get("clients",[])
        existing=next((item for item in clients if item.get("id")==client_id),None)
        fields={"id":client_id,"email":email,"subId":subscription_id,"enable":True,
                "totalGB":volume_gb*1024**3,"expiryTime":int(expires_at.timestamp()*1000)}
        if existing:
            if existing.get("email")!=email:
                raise ProvisioningError("Existing client has a different identity")
            if not existing.get("subId"):
                await api.update_client(inbound.remote_inbound_id,{**existing,**fields})
            else:
                subscription_id=existing["subId"]
        else:
            await api.add_client(inbound.remote_inbound_id,fields)
    return f"{base.rstrip('/')}/{quote(subscription_id,safe='')}"


async def provision_vpn_order(session,order_id):
    query=select(VPNOrderDetails).where(VPNOrderDetails.order_id==order_id).with_for_update()
    detail=await session.scalar(query)
    if detail is None or detail.subscription_url and detail.provisioning_status=="delivered":
        return detail
    order=await session.get(Order,order_id)
    product=await session.get(Product,order.product_id) if order.product_id else None
    try:
        if order.status not in {"paid","provisioning"}:
            raise ProvisioningError("Order is not paid")
        inbound_id=detail.inbound_id
        if not inbound_id:
            linked=await linked_inbound(session,order.product_id)
            inbound_id=linked.id if linked else None
        _,inbound=await configured_inbound(session,inbound_id)
        frozen=detail.volume.split(" ",1)[0]
        volume=int(frozen) if frozen.isdecimal() else product.vpn_volume_gb if product else None
        if not volume or not order.duration_days:
            raise ProvisioningError("Product volume or duration is missing")
        detail.inbound_id=inbound.id
        detail.server_name=(inbound.remark or f"Inbound {inbound.remote_inbound_id}")[:100]
        detail.volume=f"{volume} گیگابایت"
        detail.panel_client_id=detail.panel_client_id or str(uuid4())
        detail.subscription_id=detail.subscription_id or secrets.token_hex(12)
        detail.expires_at=detail.expires_at or datetime.now(timezone.utc)+timedelta(days=order.duration_days)
        detail.provisioning_status="provisioning"
        await session.commit()

        detail=await session.scalar(query.execution_options(populate_existing=True))
        if detail.provisioning_status=="delivered" and detail.subscription_url:
            return detail
        panel,inbound=await configured_inbound(session,detail.inbound_id)
        detail.subscription_url=await deliver_subscription(panel,inbound,detail.panel_client_id,detail.subscription_id,
            detail.username,volume,detail.expires_at)
        detail.provisioning_status="delivered"
        detail.provisioned_at=datetime.now(timezone.utc)
        detail.provisioning_error=None
        await session.commit()
        return detail
    except Exception as error:
        await session.rollback()
        failed=await session.scalar(query.execution_options(populate_existing=True))
        if failed and not failed.subscription_url:
            failed.provisioning_status="failed"
            failed.provisioning_error=type(error).__name__
            await session.commit()
        logger.warning("VPN provisioning failed for order %s (%s)",order_id,type(error).__name__)
        raise ProvisioningError("VPN provisioning failed") from error
