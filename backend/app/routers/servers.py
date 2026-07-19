from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..audit import write_audit
from ..auth import current_user
from ..config import ServerConfig, Settings, get_settings
from ..models import ConfirmAction, TelegramUser, XrayInstallRequest
from ..services.jobs import job_manager
from ..services.ssh import SSHService
from ..services.version import get_latest_xui_release, is_update_available, normalize_version, summarize_release_notes
from ..services.xui import XUIClient, normalize_inbound, parse_json_field
from .common import get_server

router = APIRouter(prefix="/servers", tags=["servers"], dependencies=[Depends(current_user)])

_operation_locks: dict[tuple[str, str], asyncio.Lock] = {}
_operation_jobs: dict[tuple[str, str], str] = {}


def _operation_lock(server_id: str, action: str) -> asyncio.Lock:
    return _operation_locks.setdefault((server_id, action), asyncio.Lock())


def _ensure_not_running(lock: asyncio.Lock, action: str) -> None:
    if lock.locked():
        raise HTTPException(status_code=409, detail=f"{action} is already running")


@router.get("")
async def list_servers(settings: Settings = Depends(get_settings)) -> list[dict]:
    semaphore = asyncio.Semaphore(settings.server_probe_concurrency)
    results = await asyncio.gather(
        *[_server_overview_limited(server, semaphore) for server in settings.servers],
        return_exceptions=True,
    )
    response: list[dict] = []
    for server, result in zip(settings.servers, results, strict=True):
        if isinstance(result, Exception):
            response.append(_base_server(server) | {
                "active": False,
                "status": "inactive",
                "os": None,
                "total_users": None,
                "online_users": None,
                "error": str(result)[:500],
            })
        else:
            response.append(result)
    return response


async def _server_overview_limited(
    server: ServerConfig,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        return await _server_overview(server)


@router.get("/{server_id}/status")
async def server_status(server: ServerConfig = Depends(get_server)) -> dict:
    ssh_service = SSHService(server)
    async with XUIClient(server) as panel:
        ssh_result, panel_result = await asyncio.gather(
            ssh_service.status(),
            panel.server_status(),
            return_exceptions=True,
        )
    return {
        "server": {"id": server.id, "name": server.name, "location": server.location},
        "ssh": _result_or_error(ssh_result),
        "panel": _result_or_error(panel_result),
    }


@router.get("/{server_id}/inbounds")
async def inbounds(server: ServerConfig = Depends(get_server)) -> list[dict]:
    async with XUIClient(server) as panel:
        raw_inbounds, online = await asyncio.gather(panel.list_inbounds(), panel.online_emails())
    online_set = set(online)
    return [normalize_inbound(item, online_set) for item in raw_inbounds]


@router.get("/{server_id}/xui/version")
async def xui_version(server: ServerConfig = Depends(get_server)) -> dict:
    installed = normalize_version(await SSHService(server).xui_version())
    try:
        release = await get_latest_xui_release()
    except Exception as exc:
        return {
            "installed": installed or None,
            "latest": None,
            "update_available": None,
            "release_name": None,
            "release_notes": None,
            "release_summary": None,
            "release_url": None,
            "published_at": None,
            "update_enabled": bool(server.panel_update_command),
            "error": str(exc)[:500],
        }

    latest = normalize_version(release["version"])
    return {
        "installed": installed or None,
        "latest": latest or None,
        "update_available": is_update_available(installed, latest),
        "release_name": release.get("name"),
        "release_notes": release.get("notes"),
        "release_summary": summarize_release_notes(release.get("notes")),
        "release_url": release.get("url"),
        "published_at": release.get("published_at"),
        "update_enabled": bool(server.panel_update_command),
        "error": None,
    }


@router.post("/{server_id}/system/update", status_code=202)
async def update_system(
    payload: ConfirmAction,
    server: ServerConfig = Depends(get_server),
    user: TelegramUser = Depends(current_user),
) -> dict:
    expected = f"APT {server.id}"
    if payload.confirm != expected:
        raise HTTPException(status_code=400, detail=f"Confirmation must be exactly: {expected}")
    if not server.system_update_command:
        raise HTTPException(status_code=501, detail="System update is disabled for this server")

    key = (server.id, "system_update")
    if key in _operation_jobs:
        raise HTTPException(status_code=409, detail="System update is already running")
    job = await job_manager.create(server.id, "system_update", user.id)
    _operation_jobs[key] = job["id"]
    job_manager.start(job["id"], _run_system_update(server, user, key))
    return job


@router.get("/{server_id}/xray/versions")
async def xray_versions(server: ServerConfig = Depends(get_server)) -> dict:
    async with XUIClient(server) as panel:
        versions = await panel.get_xray_versions()
    return {"versions": versions}


@router.post("/{server_id}/xray/install")
async def install_xray(
    payload: XrayInstallRequest,
    server: ServerConfig = Depends(get_server),
    user: TelegramUser = Depends(current_user),
) -> dict:
    expected = f"XRAY {server.id} {payload.version}"
    if payload.confirm != expected:
        raise HTTPException(status_code=400, detail=f"Confirmation must be exactly: {expected}")
    lock = _operation_lock(server.id, "xray_install")
    _ensure_not_running(lock, "Xray installation")
    async with lock:
        await _backup_database(server)
        async with XUIClient(server) as panel:
            result = await panel.install_xray(payload.version)
        await write_audit(user, "install_xray", server.id, {"version": payload.version})
    return {"success": True, "result": result}


@router.post("/{server_id}/panel/update", status_code=202)
async def update_panel(
    payload: ConfirmAction,
    server: ServerConfig = Depends(get_server),
    user: TelegramUser = Depends(current_user),
) -> dict:
    expected = f"UPDATE {server.id}"
    if payload.confirm != expected:
        raise HTTPException(status_code=400, detail=f"Confirmation must be exactly: {expected}")
    if not server.panel_update_command:
        raise HTTPException(status_code=501, detail="Panel update is disabled for this server")

    key = (server.id, "panel_update")
    if key in _operation_jobs:
        raise HTTPException(status_code=409, detail="Panel update is already running")
    job = await job_manager.create(server.id, "panel_update", user.id)
    _operation_jobs[key] = job["id"]
    job_manager.start(job["id"], _run_panel_update(server, user, key))
    return job


@router.get("/{server_id}/jobs/{job_id}")
async def operation_job(
    job_id: str,
    server: ServerConfig = Depends(get_server),
) -> dict:
    job = await job_manager.get(job_id, server.id)
    if not job:
        raise HTTPException(status_code=404, detail="Operation job not found")
    return job


async def _run_system_update(
    server: ServerConfig,
    user: TelegramUser,
    key: tuple[str, str],
) -> dict[str, Any]:
    try:
        result = await SSHService(server).system_update()
        await write_audit(
            user,
            "system_update",
            server.id,
            {"reboot_required": result["reboot_required"]},
        )
        return {"success": True, **result}
    finally:
        _operation_jobs.pop(key, None)


async def _run_panel_update(
    server: ServerConfig,
    user: TelegramUser,
    key: tuple[str, str],
) -> dict[str, Any]:
    backup_path: Path | None = None
    try:
        backup_path = await _backup_database(server)
        output = await SSHService(server).update_panel()
        last_error = None
        for _ in range(12):
            try:
                await asyncio.sleep(5)
                async with XUIClient(server) as panel:
                    health = await panel.server_status()
                await write_audit(user, "update_panel", server.id, {"backup": str(backup_path)})
                return {
                    "success": True,
                    "backup": str(backup_path),
                    "health": health,
                    "output": output[-4000:],
                }
            except Exception as exc:
                last_error = str(exc)
        raise RuntimeError(
            f"Update completed, but panel health check failed; backup={backup_path}; error={last_error}"
        )
    finally:
        _operation_jobs.pop(key, None)


async def _server_overview(server: ServerConfig) -> dict[str, Any]:
    ssh_task = SSHService(server).status()

    async def panel_snapshot() -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
        async with XUIClient(server) as panel:
            status, raw_inbounds, online = await asyncio.gather(
                panel.server_status(),
                panel.list_inbounds(),
                panel.online_emails(),
            )
        return status, raw_inbounds, online

    ssh_result, panel_result = await asyncio.gather(
        ssh_task,
        panel_snapshot(),
        return_exceptions=True,
    )

    ssh_data = ssh_result if isinstance(ssh_result, dict) else {}
    panel_status: dict[str, Any] = {}
    raw_inbounds: list[dict[str, Any]] = []
    online: list[str] = []
    panel_error = None
    if isinstance(panel_result, Exception):
        panel_error = str(panel_result)[:500]
    else:
        panel_status, raw_inbounds, online = panel_result

    service_active = str(ssh_data.get("xui_service") or "").lower() in {"active", "running"}
    panel_active = panel_error is None
    active = service_active and panel_active
    total_users = _count_clients(raw_inbounds) if panel_active else None
    online_users = len(set(online))
    if not online:
        status_count = _extract_online_count(panel_status)
        if status_count is not None:
            online_users = status_count
        else:
            flags_count = _count_online_flags(raw_inbounds)
            if flags_count is not None:
                online_users = flags_count

    ssh_error = str(ssh_result)[:500] if isinstance(ssh_result, Exception) else None
    errors = [item for item in (ssh_error, panel_error) if item]
    return _base_server(server) | {
        "active": active,
        "status": "active" if active else "inactive",
        "os": ssh_data.get("os") or None,
        "xui_version": ssh_data.get("xui_version") or None,
        "total_users": total_users,
        "online_users": online_users,
        "error": " | ".join(errors) if errors else None,
    }


def _base_server(server: ServerConfig) -> dict[str, Any]:
    return {
        "id": server.id,
        "name": server.name,
        "location": server.location,
        "panel_type": server.panel_type,
        "update_enabled": bool(server.panel_update_command),
        "system_update_enabled": bool(server.system_update_command),
    }


def _count_clients(inbounds: list[dict[str, Any]]) -> int:
    total = 0
    for inbound in inbounds:
        settings = parse_json_field(inbound.get("settings"), {})
        clients = settings.get("clients", []) if isinstance(settings, dict) else []
        total += sum(1 for client in clients if isinstance(client, dict))
    return total


def _extract_online_count(value: Any) -> int | None:
    preferred = {
        "online",
        "onlinecount",
        "onlineusers",
        "onlineclients",
        "onlineclientcount",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = "".join(ch for ch in str(key).lower() if ch.isalnum())
            if normalized in preferred and isinstance(item, (int, float)) and not isinstance(item, bool):
                return max(0, int(item))
        for item in value.values():
            found = _extract_online_count(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _extract_online_count(item)
            if found is not None:
                return found
    return None


def _count_online_flags(inbounds: list[dict[str, Any]]) -> int | None:
    found_flag = False
    total = 0
    for inbound in inbounds:
        for stat in inbound.get("clientStats") or []:
            if not isinstance(stat, dict):
                continue
            for key in ("online", "isOnline", "is_online"):
                if key in stat:
                    found_flag = True
                    if bool(stat.get(key)):
                        total += 1
                    break
    return total if found_flag else None


async def _backup_database(server: ServerConfig) -> Path:
    settings = get_settings()
    backup_dir = Path(settings.data_dir) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        backup_dir.chmod(0o700)
    except OSError:
        pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = backup_dir / f"{server.id}-{stamp}-x-ui.db"
    async with XUIClient(server) as panel:
        content = await panel.download_database()
    await asyncio.to_thread(_write_private_file, path, content)
    await asyncio.to_thread(_cleanup_old_backups, backup_dir, settings.backup_retention_days)
    return path


def _write_private_file(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def _cleanup_old_backups(directory: Path, retention_days: int) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - retention_days * 86_400
    for candidate in directory.glob("*-x-ui.db"):
        try:
            if candidate.is_file() and candidate.stat().st_mtime < cutoff:
                candidate.unlink()
        except OSError:
            continue


def _result_or_error(value: Any) -> dict[str, Any]:
    if isinstance(value, Exception):
        return {"ok": False, "error": str(value)}
    return {"ok": True, "data": value}
