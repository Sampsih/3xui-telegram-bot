#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


REFERENCE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
            value = value[1:-1]
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            os.environ.setdefault(name, value)


def main() -> int:
    load_dotenv()
    filename = os.getenv("SERVERS_FILE", "config/servers.json")
    if filename.startswith("/config/"):
        filename = "config/" + filename.removeprefix("/config/")
    path = Path(filename)
    try:
        servers = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: {path} does not exist. Run: make bootstrap", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path}:{exc.lineno}:{exc.colno}: {exc.msg}", file=sys.stderr)
        return 1
    if not isinstance(servers, list) or not servers:
        print("ERROR: server inventory must be a non-empty JSON array", file=sys.stderr)
        return 1

    errors: list[str] = []
    identifiers: set[str] = set()
    required = {
        "id",
        "name",
        "ssh_host",
        "ssh_user",
        "ssh_key_path",
        "ssh_known_hosts_path",
        "panel_url",
    }
    for index, server in enumerate(servers):
        if not isinstance(server, dict):
            errors.append(f"servers[{index}] must be an object")
            continue
        missing = sorted(required - set(server))
        if missing:
            errors.append(f"servers[{index}] missing: {', '.join(missing)}")
        identifier = str(server.get("id") or "")
        if identifier in identifiers:
            errors.append(f"duplicate server id: {identifier}")
        identifiers.add(identifier)
        if not server.get("panel_api_token") and not (
            server.get("panel_username") and server.get("panel_password")
        ):
            errors.append(f"server {identifier or index}: configure panel token or username/password")
        for key, value in server.items():
            if isinstance(value, str) and (match := REFERENCE.fullmatch(value)):
                name = match.group(1)
                if name not in os.environ:
                    errors.append(f"server {identifier or index}: environment variable {name} is not set")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {len(servers)} server(s) configured; IDs are unique")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
