import json
import os
from urllib.parse import urljoin, urlsplit

import httpx
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


class VPNPanelError(Exception): pass
class VPNPanelConfigurationError(VPNPanelError): pass
class VPNPanelAuthenticationError(VPNPanelError): pass


def _fernet():
    key = os.getenv("VPN_PANEL_ENCRYPTION_KEY", "").strip()
    if not key: raise VPNPanelConfigurationError("VPN_PANEL_ENCRYPTION_KEY is not configured")
    try: return Fernet(key.encode())
    except Exception as exc: raise VPNPanelConfigurationError("VPN_PANEL_ENCRYPTION_KEY is invalid") from exc


def encrypt_password(password: str) -> str:
    return _fernet().encrypt(password.encode()).decode()


def decrypt_password(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


class ThreeXUIClient:
    def __init__(self, base_url: str, username: str, encrypted_password: str, timeout: float = 15.0, verify: bool = True):
        self.base_url = base_url.rstrip("/") + "/"
        self.username = username
        self.password = decrypt_password(encrypted_password)
        self.client = httpx.AsyncClient(timeout=timeout, verify=verify, follow_redirects=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    async def login(self):
        response = await self.client.post(urljoin(self.base_url, "login"), data={"username": self.username, "password": self.password})
        if response.status_code >= 400: raise VPNPanelAuthenticationError("3X-UI login failed")
        try: payload = response.json()
        except ValueError: payload = {}
        if payload.get("success") is False: raise VPNPanelAuthenticationError("3X-UI rejected credentials")
        return True

    async def list_inbounds(self):
        await self.login()
        response = await self.client.get(urljoin(self.base_url, "panel/api/inbounds/list"))
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is False: raise VPNPanelError("3X-UI returned an error")
        return payload.get("obj") or []

    async def subscription_base(self):
        for path in ("panel/api/setting/defaultSettings","panel/setting/defaultSettings"):
            response=await self.client.post(urljoin(self.base_url,path))
            if response.status_code==404:
                continue
            response.raise_for_status()
            payload=response.json().get("obj") or {}
            url=payload.get("subURI")
            if payload.get("subEnable") is False or not isinstance(url,str):
                continue
            parsed=urlsplit(url)
            if parsed.scheme in {"https","http"} and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment:
                return url.rstrip("/")
        raise VPNPanelConfigurationError("Subscription service has no usable URL")

    async def add_client(self, inbound_id: int, client: dict):
        """Create one client through the 3X-UI inbound API."""
        await self.login()
        response = await self.client.post(
            urljoin(self.base_url, "panel/api/inbounds/addClient"),
            json={"id": inbound_id, "settings": json.dumps({"clients": [client]})},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is not True: raise VPNPanelError("3X-UI rejected client creation")
        return payload

    async def update_client(self,inbound_id,client):
        await self.login()
        response=await self.client.post(urljoin(self.base_url,f"panel/api/inbounds/updateClient/{client['id']}"),
            json={"id":inbound_id,"settings":json.dumps({"clients":[client]})})
        response.raise_for_status()
        if response.json().get("success") is not True:
            raise VPNPanelError("3X-UI rejected client update")


def sanitize_inbound(raw: dict) -> dict:
    settings = raw.get("settings")
    stream = raw.get("streamSettings")
    if isinstance(settings, str):
        try: settings = json.loads(settings)
        except ValueError: settings = {}
    if isinstance(stream, str):
        try: stream = json.loads(stream)
        except ValueError: stream = {}
    def mask(value):
        if isinstance(value, dict):
            return {key: ("***" if key.lower() in {"password", "passwd", "secret", "privatekey", "private_key"} else mask(item)) for key, item in value.items()}
        if isinstance(value, list): return [mask(item) for item in value]
        return value

    return {
        "id": int(raw.get("id")), "remark": str(raw.get("remark") or ""),
        "protocol": str(raw.get("protocol") or ""), "port": raw.get("port"),
        "enable": bool(raw.get("enable", True)),
        "metadata": json.dumps({"settings": mask(settings or {}), "streamSettings": mask(stream or {})}, ensure_ascii=False),
    }
