from __future__ import annotations

import json
import secrets
import time
import uuid
from typing import Any
from urllib.parse import quote

import httpx

from ..config import ServerConfig
from ..models import ClientCreate


class XUIError(RuntimeError):
    pass


class XUIClient:
    def __init__(self, server: ServerConfig):
        self.server = server
        self.base_url = server.panel_url.rstrip("/")
        headers = {"Accept": "application/json"}
        if server.panel_api_token is not None:
            headers["Authorization"] = f"Bearer {server.panel_api_token.get_secret_value()}"
        self.client = httpx.AsyncClient(
            base_url=self.base_url + "/",
            verify=server.panel_verify_tls,
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=headers,
            trust_env=False,
            max_redirects=3,
        )
        self.logged_in = False

    async def __aenter__(self) -> "XUIClient":
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.client.aclose()

    async def login(self) -> None:
        if self.logged_in:
            return
        if self.server.panel_api_token is not None:
            self.logged_in = True
            return
        if not self.server.panel_username or self.server.panel_password is None:
            raise XUIError("3x-ui authentication is not configured")
        credentials = {
            "username": self.server.panel_username,
            "password": self.server.panel_password.get_secret_value(),
        }
        self.client.headers["X-Requested-With"] = "XMLHttpRequest"

        csrf_response = await self.client.get("csrf-token")
        if csrf_response.status_code != 404:
            if csrf_response.is_error:
                raise XUIError(
                    f"3x-ui CSRF token request failed: HTTP {csrf_response.status_code}"
                )
            csrf_payload = _safe_json(csrf_response)
            csrf_token = csrf_payload.get("obj") if isinstance(csrf_payload, dict) else None
            if isinstance(csrf_token, str) and csrf_token:
                self.client.headers["X-CSRF-Token"] = csrf_token

        response = await self.client.post("login", data=credentials)
        if response.status_code in (400, 401, 403, 415):
            response = await self.client.post("login", json=credentials)
        if response.is_error:
            raise XUIError(f"3x-ui login failed: HTTP {response.status_code}")
        payload = _safe_json(response)
        if isinstance(payload, dict) and payload.get("success") is False:
            raise XUIError(str(payload.get("msg") or "3x-ui login failed"))
        self.logged_in = True

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        await self.login()
        response = await self.client.request(method, path.lstrip("/"), **kwargs)
        if response.status_code in (401, 403) and self.server.panel_api_token is None:
            self.logged_in = False
            await self.login()
            response = await self.client.request(method, path.lstrip("/"), **kwargs)
        if response.is_error:
            detail = _response_error_detail(response)
            suffix = f": {detail}" if detail else ""
            raise XUIError(f"3x-ui API error HTTP {response.status_code}{suffix}")
        payload = _safe_json(response)
        if isinstance(payload, dict) and payload.get("success") is False:
            raise XUIError(str(payload.get("msg") or "3x-ui operation failed"))
        if isinstance(payload, dict) and "obj" in payload:
            return payload["obj"]
        return payload

    async def list_inbounds(self) -> list[dict[str, Any]]:
        payload = await self.request("GET", "panel/api/inbounds/list")
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise XUIError("Unexpected inbounds response")
        return payload

    async def get_inbound(self, inbound_id: int) -> dict[str, Any]:
        try:
            payload = await self.request("GET", f"panel/api/inbounds/get/{inbound_id}")
        except XUIError as exc:
            if "HTTP 404" not in str(exc):
                raise
            payload = None
        if not isinstance(payload, dict):
            # Compatibility fallback for panels that do not expose /get consistently.
            for inbound in await self.list_inbounds():
                if int(inbound.get("id", -1)) == inbound_id:
                    return inbound
            raise XUIError(f"Inbound {inbound_id} not found")
        return payload

    async def server_status(self) -> dict[str, Any]:
        payload = await self.request("GET", "panel/api/server/status")
        return payload if isinstance(payload, dict) else {}

    async def online_emails(self) -> list[str]:
        # In current 3x-ui releases online clients are exposed by the clients
        # controller. Older releases used the inbounds controller, so retain a
        # compatibility fallback without letting a missing endpoint break the UI.
        for path in (
            "panel/api/clients/onlines",
            "panel/api/inbounds/onlines",
        ):
            try:
                payload = await self.request("POST", path)
            except XUIError as exc:
                if "HTTP 404" in str(exc):
                    continue
                raise

            if isinstance(payload, list):
                return sorted({str(item) for item in payload if str(item)})

            if isinstance(payload, dict):
                for key in ("emails", "online", "clients", "items"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        return sorted({str(item) for item in value if str(item)})

        return []

    async def client_links(self, sub_id: str) -> list[str]:
        """Return the exact share links generated by 3x-ui for a client.

        A client may be attached to more than one inbound, so the API can
        legitimately return several links. Keeping generation in 3x-ui is
        important because its transport, Reality and Hysteria link formats
        evolve together with the panel.
        """
        if not sub_id or len(sub_id) > 128:
            raise XUIError("Client subscription ID is missing or invalid")
        payload = await self.request(
            "GET",
            f"panel/api/clients/subLinks/{quote(sub_id, safe='')}",
        )
        links = _extract_connection_links(payload)
        if not links:
            raise XUIError("3x-ui did not return a connection link for this client")
        return links

    async def add_client(self, request: ClientCreate) -> dict[str, Any]:
        inbound = await self.get_inbound(request.inbound_id)
        protocol = str(inbound.get("protocol", "")).lower()
        credential = _new_credential(protocol)
        now_ms = int(time.time() * 1000)
        expiry_ms = now_ms + request.expiry_days * 86_400_000 if request.expiry_days else 0
        total_bytes = int(request.total_gb * 1024**3) if request.total_gb else 0

        client: dict[str, Any] = {
            "email": request.email,
            "enable": request.enable,
            "expiryTime": expiry_ms,
            "limitIp": request.limit_ip,
            "totalGB": total_bytes,
            "tgId": "",
            "subId": secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16],
            "reset": 0,
        }
        if protocol in {"vless", "vmess"}:
            client["id"] = credential
            client["flow"] = request.flow if protocol == "vless" else ""
        elif protocol in {"trojan", "hysteria", "hysteria2", "hy2"}:
            client["password"] = credential
        elif protocol == "shadowsocks":
            client["password"] = credential
            client["method"] = "chacha20-ietf-poly1305"
        else:
            raise XUIError(f"Client creation for protocol '{protocol}' is not implemented")

        payload = {
            "id": request.inbound_id,
            "settings": json.dumps({"clients": [client]}, separators=(",", ":")),
        }
        try:
            response = await self.request("POST", "panel/api/inbounds/addClient", json=payload)
        except XUIError as exc:
            if "HTTP 404" not in str(exc):
                raise
            # 3x-ui 3.x moved client mutations out of the inbounds controller.
            # Retain the legacy call above for older panels and transparently
            # switch to the current global-client API when that route is absent.
            response = await self.request(
                "POST",
                "panel/api/clients/add",
                json={
                    "client": _current_api_client(protocol, client),
                    "inboundIds": [request.inbound_id],
                },
            )

        # Some panel versions return an empty body after a successful mutation. Verify state.
        inbound_after = await self.get_inbound(request.inbound_id)
        created = find_client(inbound_after, request.email)
        if not created:
            raise XUIError("3x-ui did not return an error, but the client was not created")
        return {"api_response": response, "client": created, "protocol": protocol}

    async def delete_client_by_email(self, inbound_id: int, email: str) -> None:
        inbound = await self.get_inbound(inbound_id)
        protocol = str(inbound.get("protocol", "")).lower()
        client = find_client(inbound, email)
        if not client:
            raise XUIError(f"Client '{email}' not found")
        client_id = _client_identifier(protocol, client)
        try:
            await self.request("POST", f"panel/api/inbounds/{inbound_id}/delClient/{quote(client_id, safe='')}")
        except XUIError as exc:
            if "HTTP 404" not in str(exc):
                raise
            await self._delete_client_current_api(inbound_id, email)
        inbound_after = await self.get_inbound(inbound_id)
        if find_client(inbound_after, email):
            # Newer panels may provide deletion by email, which is safer for some protocols.
            try:
                await self.request("POST", f"panel/api/inbounds/{inbound_id}/delClientByEmail/{quote(email, safe='')}")
            except XUIError as exc:
                if "HTTP 404" not in str(exc):
                    raise
                await self._delete_client_current_api(inbound_id, email)
            inbound_after = await self.get_inbound(inbound_id)
        if find_client(inbound_after, email):
            raise XUIError("Client still exists after delete request")

    async def _delete_client_current_api(self, inbound_id: int, email: str) -> None:
        encoded_email = quote(email, safe="")
        payload = await self.request("GET", f"panel/api/clients/get/{encoded_email}")
        inbound_ids = payload.get("inboundIds") if isinstance(payload, dict) else None
        attached_ids = {
            int(value)
            for value in inbound_ids or []
            if isinstance(value, int) or (isinstance(value, str) and value.isdigit())
        }
        if attached_ids - {inbound_id}:
            await self.request(
                "POST",
                f"panel/api/clients/{encoded_email}/detach",
                json={"inboundIds": [inbound_id]},
            )
        else:
            await self.request("POST", f"panel/api/clients/del/{encoded_email}")

    async def download_database(self) -> bytes:
        await self.login()
        response = await self.client.get("panel/api/server/getDb")
        if response.is_error:
            raise XUIError(f"Database backup failed: HTTP {response.status_code}")
        if not response.content:
            raise XUIError("Database backup is empty")
        if "json" in response.headers.get("content-type", ""):
            payload = _safe_json(response)
            raise XUIError(f"Database backup returned JSON instead of a file: {payload}")
        return response.content

    async def get_xray_versions(self) -> Any:
        return await self.request("GET", "panel/api/server/getXrayVersion")

    async def install_xray(self, version: str) -> Any:
        return await self.request("POST", f"panel/api/server/installXray/{version}")


def parse_json_field(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def find_client(inbound: dict[str, Any], email: str) -> dict[str, Any] | None:
    settings = parse_json_field(inbound.get("settings"), {})
    for client in settings.get("clients", []) if isinstance(settings, dict) else []:
        if str(client.get("email", "")) == email:
            return client
    return None


def normalize_inbound(inbound: dict[str, Any], online: set[str] | None = None) -> dict[str, Any]:
    settings = parse_json_field(inbound.get("settings"), {})
    clients = settings.get("clients", []) if isinstance(settings, dict) else []
    stats_by_email = {
        str(stat.get("email", "")): stat
        for stat in (inbound.get("clientStats") or [])
        if isinstance(stat, dict)
    }
    normalized_clients = []
    for client in clients:
        email = str(client.get("email", ""))
        stat = stats_by_email.get(email, {})
        normalized_clients.append({
            "email": email,
            "enable": bool(client.get("enable", True)),
            "expiry_time": int(client.get("expiryTime") or 0),
            "total_gb": int(client.get("totalGB") or 0),
            "limit_ip": int(client.get("limitIp") or 0),
            "flow": client.get("flow") or "",
            "up": int(stat.get("up") or 0),
            "down": int(stat.get("down") or 0),
            "total": int(stat.get("up") or 0) + int(stat.get("down") or 0),
            "online": email in (online or set()),
        })
    return {
        "id": int(inbound.get("id", 0)),
        "remark": inbound.get("remark") or f"Inbound {inbound.get('id', '')}",
        "protocol": inbound.get("protocol") or "",
        "port": int(inbound.get("port") or 0),
        "enable": bool(inbound.get("enable", True)),
        "up": int(inbound.get("up") or 0),
        "down": int(inbound.get("down") or 0),
        "clients": normalized_clients,
    }


def _response_error_detail(response: httpx.Response) -> str:
    payload = _safe_json(response)
    if isinstance(payload, dict):
        for key in ("msg", "message", "detail", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:300]
    if isinstance(payload, str):
        value = payload.strip()
        if value and "<html" not in value.lower() and "<!doctype" not in value.lower():
            return value[:300]
    return ""


def _safe_json(response: httpx.Response) -> Any:
    if not response.content or not response.text.strip():
        return None
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type and not response.text.lstrip().startswith(("{", "[")):
        return response.text
    try:
        return response.json()
    except ValueError:
        return response.text


_CONNECTION_PREFIXES = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "hysteria2://",
    "hy2://",
)


def _extract_connection_links(value: Any) -> list[str]:
    found: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, str):
            for line in item.splitlines():
                candidate = line.strip()
                if candidate.lower().startswith(_CONNECTION_PREFIXES):
                    found.append(candidate)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)
        elif isinstance(item, dict):
            for nested in item.values():
                visit(nested)

    visit(value)
    return list(dict.fromkeys(found))


def _new_credential(protocol: str) -> str:
    if protocol in {"vless", "vmess"}:
        return str(uuid.uuid4())
    return secrets.token_urlsafe(24)


def _current_api_client(protocol: str, legacy_client: dict[str, Any]) -> dict[str, Any]:
    """Translate an inbound-embedded client to the 3x-ui 3.x client model."""
    client: dict[str, Any] = {
        "email": legacy_client["email"],
        "enable": legacy_client["enable"],
        "expiryTime": legacy_client["expiryTime"],
        "limitIp": legacy_client["limitIp"],
        "totalGB": legacy_client["totalGB"],
        "tgId": 0,
        "subId": legacy_client["subId"],
        "reset": legacy_client["reset"],
        "security": "auto",
        "comment": "",
    }
    if protocol in {"vless", "vmess"}:
        client["id"] = legacy_client["id"]
        client["flow"] = legacy_client.get("flow", "")
    elif protocol == "trojan":
        client["password"] = legacy_client["password"]
    elif protocol in {"hysteria", "hysteria2", "hy2"}:
        client["auth"] = legacy_client["password"]
    elif protocol == "shadowsocks":
        client["password"] = legacy_client["password"]
    return client


def _client_identifier(protocol: str, client: dict[str, Any]) -> str:
    if protocol in {"vless", "vmess"}:
        return str(client.get("id") or "")
    if protocol in {"trojan", "hysteria", "hysteria2", "hy2"}:
        return str(client.get("password") or client.get("email") or "")
    if protocol == "shadowsocks":
        return str(client.get("email") or "")
    raise XUIError(f"Client deletion for protocol '{protocol}' is not implemented")
