from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings
from .models import TelegramUser

_lock = asyncio.Lock()


async def write_audit(
    user: TelegramUser,
    action: str,
    server_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "telegram_user_id": user.id,
        "telegram_username": user.username,
        "action": action,
        "server_id": server_id,
        "details": details or {},
    }
    path = Path(get_settings().data_dir) / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    async with _lock:
        await asyncio.to_thread(
            _append_line,
            path,
            json.dumps(record, ensure_ascii=False, separators=(",", ":")),
        )


def _append_line(path: Path, line: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8", closefd=False) as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)
