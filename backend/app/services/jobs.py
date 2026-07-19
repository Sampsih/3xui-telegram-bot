from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import Awaitable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings


class JobManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def create(self, server_id: str, action: str, telegram_user_id: int) -> dict[str, Any]:
        now = _now()
        job = {
            "id": str(uuid.uuid4()),
            "server_id": server_id,
            "action": action,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "telegram_user_id": telegram_user_id,
            "result": None,
            "error": None,
        }
        async with self._lock:
            await asyncio.to_thread(_write_job, job)
        return _public_job(job)

    def start(self, job_id: str, operation: Awaitable[dict[str, Any]]) -> None:
        task = asyncio.create_task(self._run(job_id, operation), name=f"operation-{job_id}")
        self._tasks[job_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job_id, None))

    async def get(self, job_id: str, server_id: str) -> dict[str, Any] | None:
        try:
            uuid.UUID(job_id)
        except ValueError:
            return None
        async with self._lock:
            job = await asyncio.to_thread(_read_job, job_id)
            if not job or job.get("server_id") != server_id:
                return None
            if job.get("status") in {"queued", "running"} and job_id not in self._tasks:
                job["status"] = "failed"
                job["error"] = "Операция была прервана перезапуском backend"
                job["updated_at"] = _now()
                await asyncio.to_thread(_write_job, job)
        return _public_job(job)

    async def _run(self, job_id: str, operation: Awaitable[dict[str, Any]]) -> None:
        await self._update(job_id, status="running")
        try:
            result = await operation
        except Exception as exc:
            await self._update(job_id, status="failed", error=str(exc)[:4000])
        else:
            await self._update(job_id, status="succeeded", result=result)

    async def _update(self, job_id: str, **changes: Any) -> None:
        async with self._lock:
            job = await asyncio.to_thread(_read_job, job_id)
            if not job:
                return
            job.update(changes)
            job["updated_at"] = _now()
            await asyncio.to_thread(_write_job, job)


def _jobs_dir() -> Path:
    directory = Path(get_settings().data_dir) / "jobs"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    return directory


def _job_path(job_id: str) -> Path:
    return _jobs_dir() / f"{job_id}.json"


def _read_job(job_id: str) -> dict[str, Any] | None:
    path = _job_path(job_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_job(job: dict[str, Any]) -> None:
    path = _job_path(str(job["id"]))
    temporary = path.with_suffix(".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(temporary, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as handle:
            json.dump(job, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)
    os.replace(temporary, path)
    path.chmod(0o600)


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in job.items() if key != "telegram_user_id"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


job_manager = JobManager()
