from __future__ import annotations

import re
import time
from typing import Any

import httpx

LATEST_RELEASE_URL = "https://api.github.com/repos/MHSanaei/3x-ui/releases/latest"
_CACHE_TTL_SECONDS = 300
_cache: dict[str, Any] = {"expires": 0.0, "value": None}


async def get_latest_xui_release() -> dict[str, Any]:
    now = time.monotonic()
    cached = _cache.get("value")
    if cached and now < float(_cache.get("expires") or 0):
        return dict(cached)

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "xui-telegram-admin",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(12.0, connect=7.0),
        headers=headers,
    ) as client:
        response = await client.get(LATEST_RELEASE_URL)
        response.raise_for_status()
        payload = response.json()

    tag = str(payload.get("tag_name") or "").strip()
    if not tag:
        raise RuntimeError("GitHub did not return a 3x-ui release tag")

    result = {
        "version": tag,
        "name": payload.get("name") or tag,
        "url": payload.get("html_url") or "https://github.com/MHSanaei/3x-ui/releases/latest",
        "published_at": payload.get("published_at"),
        "notes": str(payload.get("body") or "").strip()[:30000],
    }
    _cache["value"] = result
    _cache["expires"] = now + _CACHE_TTL_SECONDS
    return dict(result)


def summarize_release_notes(value: str | None, max_items: int = 24) -> str:
    if not value:
        return "Описание релиза недоступно."
    output: list[str] = []
    items = 0
    for raw_line in value.replace("\r", "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("![") or line.lower().startswith("full changelog:"):
            continue
        if line.startswith("#"):
            heading = line.lstrip("# ").strip()
            if heading and heading.lower() not in {"contributors", "reports"}:
                output.append(heading)
            continue
        if line.startswith(("- ", "* ", "+ ")):
            if items >= max_items:
                continue
            output.append("• " + line[2:].strip())
            items += 1
        if len("\n".join(output)) >= 5000:
            break
    return "\n".join(output).strip() or str(value).strip()[:5000]


def normalize_version(value: str | None) -> str:
    if not value:
        return ""
    match = re.search(r"v?(\d+(?:\.\d+)+)", value)
    return f"v{match.group(1)}" if match else value.strip()


def version_tuple(value: str | None) -> tuple[int, ...]:
    normalized = normalize_version(value)
    match = re.search(r"(\d+(?:\.\d+)+)", normalized)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def is_update_available(installed: str | None, latest: str | None) -> bool | None:
    installed_parts = version_tuple(installed)
    latest_parts = version_tuple(latest)
    if not installed_parts or not latest_parts:
        return None
    length = max(len(installed_parts), len(latest_parts))
    installed_parts += (0,) * (length - len(installed_parts))
    latest_parts += (0,) * (length - len(latest_parts))
    return latest_parts > installed_parts
