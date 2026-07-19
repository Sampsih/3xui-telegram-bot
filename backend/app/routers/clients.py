from __future__ import annotations

from fastapi import APIRouter, Depends

from ..audit import write_audit
from ..auth import current_user
from ..config import ServerConfig
from ..models import ClientCreate, TelegramUser
from ..services.links import build_connection, connection_payload
from ..services.xui import XUIClient, XUIError, find_client
from .common import get_server

router = APIRouter(prefix="/servers", tags=["clients"], dependencies=[Depends(current_user)])


@router.post("/{server_id}/clients")
async def create_client(
    payload: ClientCreate,
    server: ServerConfig = Depends(get_server),
    user: TelegramUser = Depends(current_user),
) -> dict:
    async with XUIClient(server) as panel:
        created = await panel.add_client(payload)
        inbound = await panel.get_inbound(payload.inbound_id)
        connections = await _client_connections(panel, server, inbound, payload.email)
    await write_audit(
        user,
        "create_client",
        server.id,
        {"inbound_id": payload.inbound_id, "email": payload.email, "total_gb": payload.total_gb, "expiry_days": payload.expiry_days},
    )
    return {
        "success": True,
        "client": created["client"],
        "protocol": created["protocol"],
        "connections": connections,
        "connection": connections[0],
    }


@router.delete("/{server_id}/clients/{inbound_id}/{email}")
async def delete_client(
    inbound_id: int,
    email: str,
    server: ServerConfig = Depends(get_server),
    user: TelegramUser = Depends(current_user),
) -> dict:
    async with XUIClient(server) as panel:
        await panel.delete_client_by_email(inbound_id, email)
    await write_audit(user, "delete_client", server.id, {"inbound_id": inbound_id, "email": email})
    return {"success": True}


@router.get("/{server_id}/clients/{inbound_id}/{email}/connection")
async def connection(
    inbound_id: int,
    email: str,
    server: ServerConfig = Depends(get_server),
) -> dict:
    async with XUIClient(server) as panel:
        inbound = await panel.get_inbound(inbound_id)
        connections = await _client_connections(panel, server, inbound, email)
    return {"connections": connections, "connection": connections[0]}


async def _client_connections(
    panel: XUIClient,
    server: ServerConfig,
    inbound: dict,
    email: str,
) -> list[dict[str, str]]:
    client = find_client(inbound, email)
    if not client:
        raise XUIError(f"Client '{email}' not found")

    sub_id = str(client.get("subId") or "").strip()
    if sub_id:
        try:
            links = await panel.client_links(sub_id)
            return [connection_payload(uri) for uri in links]
        except XUIError as exc:
            # Old panels do not expose /clients/subLinks. Retain the local
            # generator only for that compatibility case; other API errors
            # must remain visible instead of silently returning a wrong link.
            if "HTTP 404" not in str(exc):
                raise

    legacy = build_connection(server, inbound, email)
    protocol = str(inbound.get("protocol") or "").lower()
    return [{
        **legacy,
        "protocol": "hysteria2" if protocol in {"hysteria", "hy2"} else protocol,
        "label": f"{server.name} · {email}",
    }]
