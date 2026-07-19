#!/usr/bin/env python3
from __future__ import annotations

import getpass
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from urllib.parse import urlparse


PROJECT_DIR = Path(__file__).resolve().parent.parent
SERVER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SSH_USER = re.compile(r"^[a-z_][a-z0-9_-]*[$]?$", re.IGNORECASE)

TEXT = {
    "ru": {
        "title": "Интерактивная настройка X-UI Telegram Admin",
        "existing": "Файлы .env или config/servers.json уже существуют. Перезаписать их",
        "domain": "Домен приложения без https://",
        "token": "Токен Telegram-бота",
        "telegram_ids": "Telegram ID администраторов через запятую",
        "server_count": "Количество управляемых серверов",
        "server": "Сервер",
        "server_id": "Короткий ID сервера (a-z, 0-9, _ и -)",
        "server_name": "Отображаемое имя",
        "location": "Локация (можно оставить пустой)",
        "ssh_host": "SSH адрес или имя хоста",
        "ssh_port": "SSH порт",
        "public_host": "Публичный адрес для ссылок подключения",
        "tunnel": "Панель 3x-ui доступна только через SSH-туннель",
        "panel_port": "Локальный порт панели 3x-ui на удалённом сервере",
        "panel_path": "Web base path панели без начального /",
        "panel_url": "Полный URL панели вместе с web base path",
        "panel_auth": "Авторизация панели: token или login",
        "panel_token": "API-токен панели",
        "panel_username": "Логин панели",
        "panel_password": "Пароль панели",
        "verify_tls": "Проверять TLS-сертификат панели",
        "system_update": "Разрешить безопасное обновление пакетов ОС",
        "panel_update": "Разрешить обновление 3x-ui",
        "raw_ssh": "Разрешить произвольные SSH-команды из Telegram (не рекомендуется)",
        "scan_key": "Получить SSH host key и показать fingerprint",
        "confirm_fingerprint": "Fingerprint проверен через доверенный канал; добавить ключ",
        "provision": "Сейчас создать xuiadmin и wrappers на удалённом сервере",
        "provision_user": "Пользователь для первоначальной SSH-настройки",
        "reuse_key": "SSH-ключ уже существует. Использовать его",
        "start": "Запустить приложение через Docker Compose сейчас",
        "done": "Конфигурация создана успешно.",
        "next": "Следующие действия:",
        "language": "Язык / Language [ru/en]",
    },
    "en": {
        "title": "X-UI Telegram Admin interactive setup",
        "existing": ".env or config/servers.json already exists. Overwrite them",
        "domain": "Application domain without https://",
        "token": "Telegram bot token",
        "telegram_ids": "Administrator Telegram IDs separated by commas",
        "server_count": "Number of managed servers",
        "server": "Server",
        "server_id": "Short server ID (a-z, 0-9, _ and -)",
        "server_name": "Display name",
        "location": "Location (optional)",
        "ssh_host": "SSH address or hostname",
        "ssh_port": "SSH port",
        "public_host": "Public host used in connection links",
        "tunnel": "The 3x-ui panel is reachable only through an SSH tunnel",
        "panel_port": "3x-ui panel port on the remote server",
        "panel_path": "Panel web base path without the leading /",
        "panel_url": "Full panel URL including its web base path",
        "panel_auth": "Panel authentication: token or login",
        "panel_token": "Panel API token",
        "panel_username": "Panel username",
        "panel_password": "Panel password",
        "verify_tls": "Verify the panel TLS certificate",
        "system_update": "Enable safe OS package updates",
        "panel_update": "Enable 3x-ui updates",
        "raw_ssh": "Enable arbitrary SSH commands from Telegram (not recommended)",
        "scan_key": "Fetch the SSH host key and show its fingerprint",
        "confirm_fingerprint": "Fingerprint was verified through a trusted channel; add this key",
        "provision": "Create xuiadmin and wrappers on the remote server now",
        "provision_user": "User for initial SSH provisioning",
        "reuse_key": "The SSH key already exists. Reuse it",
        "start": "Start the application with Docker Compose now",
        "done": "Configuration created successfully.",
        "next": "Next steps:",
        "language": "Language / Язык [ru/en]",
    },
}


def choose_language() -> str:
    default = "ru" if os.environ.get("LANG", "").lower().startswith("ru") else "en"
    value = input(f"Language / Язык [ru/en] ({default}): ").strip().lower() or default
    return value if value in TEXT else default


def ask(label: str, default: str | None = None, *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default not in {None, ""} else ""
    reader = getpass.getpass if secret else input
    value = reader(f"{label}{suffix}: ").strip()
    return value or (default or "")


def ask_required(label: str, default: str | None = None, *, secret: bool = False) -> str:
    while True:
        value = ask(label, default, secret=secret)
        if value:
            return value
        print("This value is required.")


def ask_bool(label: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} [{hint}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes", "д", "да"}:
            return True
        if value in {"n", "no", "н", "нет"}:
            return False
        print("Enter yes/no or да/нет.")


def ask_int(label: str, default: int, minimum: int, maximum: int) -> int:
    while True:
        raw = ask(label, str(default))
        try:
            value = int(raw)
        except ValueError:
            print(f"Enter a number from {minimum} to {maximum}.")
            continue
        if minimum <= value <= maximum:
            return value
        print(f"Enter a number from {minimum} to {maximum}.")


def ask_matching(label: str, pattern: re.Pattern[str], default: str | None = None) -> str:
    while True:
        value = ask(label, default)
        if pattern.fullmatch(value):
            return value
        print("Invalid value.")


def validate_host(value: str) -> bool:
    if not value or any(character.isspace() for character in value):
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value))


def ask_host(label: str) -> str:
    while True:
        value = ask(label)
        if validate_host(value):
            return value
        print("Enter a valid IP address or hostname.")


def validate_panel_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def may_disable_tls_verification(value: str) -> bool:
    parsed = urlparse(value)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or host in {"localhost", "panel-tunnel"} or host.startswith("panel-tunnel-"):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def parse_telegram_ids(value: str) -> list[int]:
    identifiers: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not re.fullmatch(r"[1-9][0-9]*", item):
            raise ValueError("Telegram IDs must be positive integers")
        identifier = int(item)
        if identifier not in identifiers:
            identifiers.append(identifier)
    if not identifiers:
        raise ValueError("At least one Telegram ID is required")
    return identifiers


def dotenv_quote(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("Multiline environment values are not supported")
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def secret_name(server_id: str, suffix: str) -> str:
    prefix = re.sub(r"[^A-Z0-9]", "_", server_id.upper())
    return f"{prefix}_{suffix}"


def write_private(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(mode)
    temporary.replace(path)


def backup_existing(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    backup = PROJECT_DIR / "data" / "installer-backups" / datetime.now().strftime("%Y%m%dT%H%M%S")
    backup.mkdir(parents=True, mode=0o700)
    for path in existing:
        shutil.copy2(path, backup / path.name)
    return backup


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=PROJECT_DIR, check=check, text=True)


def ensure_ssh_key(server_id: str, comment: str, language: str) -> Path:
    key_path = PROJECT_DIR / "secrets" / f"id_ed25519_{server_id}"
    if key_path.exists():
        if not ask_bool(TEXT[language]["reuse_key"], True):
            raise RuntimeError(f"Refusing to overwrite {key_path}")
    else:
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key_path), "-C", comment])
    key_path.chmod(0o600)
    key_path.with_suffix(key_path.suffix + ".pub").chmod(0o644)
    return key_path


def scan_host_key(host: str, port: int, known_hosts: Path, language: str) -> bool:
    if not ask_bool(TEXT[language]["scan_key"], True):
        return False
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as temporary:
        result = subprocess.run(
            ["ssh-keyscan", "-H", "-p", str(port), host],
            check=False,
            text=True,
            stdout=temporary,
        )
        temporary.flush()
        if result.returncode != 0 or Path(temporary.name).stat().st_size == 0:
            print("ssh-keyscan did not return a host key.", file=sys.stderr)
            return False
        subprocess.run(["ssh-keygen", "-lf", temporary.name], check=True)
        if not ask_bool(TEXT[language]["confirm_fingerprint"], False):
            return False
        temporary.seek(0)
        new_lines = [line for line in temporary.read().splitlines() if line and not line.startswith("#")]
    known_hosts.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    current = known_hosts.read_text(encoding="utf-8").splitlines() if known_hosts.exists() else []
    merged = current + [line for line in new_lines if line not in current]
    write_private(known_hosts, "\n".join(merged) + "\n", 0o644)
    return True


def ssh_options(host: str, port: int, known_hosts: Path) -> list[str]:
    return [
        "-p",
        str(port),
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
    ]


def scp_target(user: str, host: str, path: str) -> str:
    rendered_host = f"[{host}]" if ":" in host else host
    return f"{user}@{rendered_host}:{path}"


def provision_host(
    server_id: str,
    host: str,
    port: int,
    public_key: Path,
    known_hosts: Path,
    language: str,
) -> bool:
    if not ask_bool(TEXT[language]["provision"], True):
        return False
    admin_user = ask_matching(TEXT[language]["provision_user"], SSH_USER, "root")
    remote_dir = f"/tmp/xui-managed-host-{server_id}"
    options = ssh_options(host, port, known_hosts)
    target = f"{admin_user}@{host}"
    run(["ssh", *options, target, f"install -d -m 700 {remote_dir}"])
    scp_options = ["-P", str(port), "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={known_hosts}"]
    files = [
        PROJECT_DIR / "scripts" / "install-managed-host",
        PROJECT_DIR / "scripts" / "xui-system-update",
        PROJECT_DIR / "scripts" / "xui-safe-update",
        PROJECT_DIR / "scripts" / "xuiadmin.sudoers",
        public_key,
    ]
    run(["scp", *scp_options, *(str(path) for path in files), scp_target(admin_user, host, remote_dir + "/")])
    public_name = public_key.name
    install_command = (
        f"chmod 755 {remote_dir}/install-managed-host && "
        f"{remote_dir}/install-managed-host {remote_dir}/{public_name}"
    )
    if admin_user != "root":
        install_command = f"sudo bash -c '{install_command}'"
    run(["ssh", "-t", *options, target, install_command])
    run(
        [
            "ssh",
            *options,
            "-i",
            str(public_key.with_suffix("")),
            "-o",
            "IdentitiesOnly=yes",
            f"xuiadmin@{host}",
            "sudo -n /usr/local/sbin/xui-system-update --check && sudo -n -l",
        ]
    )
    return True


def render_tunnel_compose(tunnels: list[dict[str, object]]) -> str:
    if not tunnels:
        return ""
    lines = ["services:"]
    for tunnel in tunnels:
        service = f"panel-tunnel-{tunnel['id']}"
        key_name = f"id_ed25519_{tunnel['id']}"
        command = [
            "-g",
            "-N",
            "-p",
            str(tunnel["ssh_port"]),
            "-i",
            f"/run/secrets/{key_name}",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "UserKnownHostsFile=/run/secrets/known_hosts",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-L",
            f"0.0.0.0:{tunnel['panel_port']}:127.0.0.1:{tunnel['panel_port']}",
            f"xuiadmin@{tunnel['ssh_host']}",
        ]
        lines.extend(
            [
                f"  {service}:",
                "    build:",
                "      context: ./tunnel",
                "    restart: unless-stopped",
                "    command:",
                *(f"      - {json.dumps(item)}" for item in command),
                "    volumes:",
                "      - ./secrets:/run/secrets:ro",
                "    read_only: true",
                "    tmpfs:",
                "      - /tmp:size=16m,mode=1777",
                "    cap_drop: [ALL]",
                "    security_opt:",
                "      - no-new-privileges:true",
                "    networks: [control_net]",
            ]
        )
    return "\n".join(lines) + "\n"


def collect_server(index: int, language: str) -> tuple[dict[str, object], dict[str, str], dict[str, object] | None]:
    text = TEXT[language]
    print(f"\n--- {text['server']} {index} ---")
    server_id = ask_matching(text["server_id"], SERVER_ID, f"server-{index}")
    name = ask(text["server_name"], server_id)
    location = ask(text["location"])
    ssh_host = ask_host(text["ssh_host"])
    ssh_port = ask_int(text["ssh_port"], 22, 1, 65535)
    public_host = ask(text["public_host"], ssh_host)
    tunnel = ask_bool(text["tunnel"], False)
    tunnel_config: dict[str, object] | None = None
    if tunnel:
        panel_port = ask_int(text["panel_port"], 2053, 1, 65535)
        panel_path = ask(text["panel_path"]).strip("/")
        panel_url = f"http://panel-tunnel-{server_id}:{panel_port}"
        if panel_path:
            panel_url += f"/{panel_path}"
        verify_tls = False
        tunnel_config = {
            "id": server_id,
            "ssh_host": ssh_host,
            "ssh_port": ssh_port,
            "panel_port": panel_port,
        }
    else:
        while True:
            panel_url = ask(text["panel_url"])
            if validate_panel_url(panel_url):
                break
            print("Enter an absolute HTTP(S) URL.")
        while True:
            verify_tls = ask_bool(text["verify_tls"], panel_url.startswith("https://"))
            if verify_tls or may_disable_tls_verification(panel_url):
                break
            print("TLS verification cannot be disabled for a public HTTPS panel.")

    auth = ask(text["panel_auth"], "login").lower()
    while auth not in {"token", "login"}:
        auth = ask(text["panel_auth"], "login").lower()
    environment: dict[str, str] = {}
    server: dict[str, object] = {
        "id": server_id,
        "name": name,
        "location": location or None,
        "ssh_host": ssh_host,
        "ssh_port": ssh_port,
        "ssh_user": "xuiadmin",
        "ssh_key_path": f"/run/secrets/id_ed25519_{server_id}",
        "ssh_known_hosts_path": "/run/secrets/known_hosts",
        "panel_url": panel_url,
        "panel_verify_tls": verify_tls,
        "public_host": public_host or None,
        "enable_raw_ssh": ask_bool(text["raw_ssh"], False),
    }
    if auth == "token":
        variable = secret_name(server_id, "PANEL_API_TOKEN")
        environment[variable] = ask_required(text["panel_token"], secret=True)
        server["panel_api_token"] = "${" + variable + "}"
    else:
        username_variable = secret_name(server_id, "PANEL_USERNAME")
        password_variable = secret_name(server_id, "PANEL_PASSWORD")
        environment[username_variable] = ask_required(text["panel_username"])
        environment[password_variable] = ask_required(text["panel_password"], secret=True)
        server["panel_username"] = "${" + username_variable + "}"
        server["panel_password"] = "${" + password_variable + "}"
    if ask_bool(text["system_update"], True):
        server["system_update_command"] = "sudo -n /usr/local/sbin/xui-system-update"
    if ask_bool(text["panel_update"], True):
        server["panel_update_command"] = "sudo -n /usr/local/sbin/xui-safe-update"
    return server, environment, tunnel_config


def main() -> int:
    language = choose_language()
    text = TEXT[language]
    print(f"\n{text['title']}\n")
    env_path = PROJECT_DIR / ".env"
    inventory_path = PROJECT_DIR / "config" / "servers.json"
    tunnel_path = PROJECT_DIR / "docker-compose.tunnel.yml"
    if (env_path.exists() or inventory_path.exists()) and not ask_bool(text["existing"], False):
        print("Cancelled.")
        return 2

    domain = ask(text["domain"], "xui-admin.example.com").removeprefix("https://").removeprefix("http://").strip("/")
    if not validate_host(domain):
        raise ValueError("Invalid application domain")
    bot_token = ask_required(text["token"], secret=True)
    while True:
        try:
            telegram_ids = parse_telegram_ids(ask(text["telegram_ids"]))
            break
        except ValueError as exc:
            print(exc)
    server_count = ask_int(text["server_count"], 1, 1, 100)
    servers: list[dict[str, object]] = []
    environment: dict[str, str] = {}
    tunnels: list[dict[str, object]] = []
    for index in range(1, server_count + 1):
        server, secrets, tunnel = collect_server(index, language)
        if any(item["id"] == server["id"] for item in servers):
            raise ValueError(f"Duplicate server ID: {server['id']}")
        servers.append(server)
        environment.update(secrets)
        if tunnel:
            tunnels.append(tunnel)

    backup = backup_existing([env_path, inventory_path, tunnel_path])
    secrets_dir = PROJECT_DIR / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    secrets_dir.chmod(0o700)
    known_hosts = secrets_dir / "known_hosts"
    for server in servers:
        server_id = str(server["id"])
        key = ensure_ssh_key(server_id, f"xuiadmin-{server_id}", language)
        host_key_added = scan_host_key(str(server["ssh_host"]), int(server["ssh_port"]), known_hosts, language)
        if host_key_added:
            provision_host(server_id, str(server["ssh_host"]), int(server["ssh_port"]), key.with_suffix(key.suffix + ".pub"), known_hosts, language)

    env_values = {
        "APP_DOMAIN": domain,
        "MINI_APP_URL": f"https://{domain}/app/",
        "BOT_TOKEN": bot_token,
        "ALLOWED_TELEGRAM_IDS": json.dumps(telegram_ids, separators=(",", ":")),
        "AUTH_MAX_AGE_SECONDS": "900",
        "BOT_OUTPUT_MAX_CHARS": "12000",
        "DEV_BYPASS_AUTH": "false",
        "ENABLE_API_DOCS": "false",
        "MAX_REQUEST_BODY_BYTES": "65536",
        "BACKUP_RETENTION_DAYS": "30",
        "SERVER_PROBE_CONCURRENCY": "10",
        "DATA_DIR": "/data",
        "SERVERS_FILE": "/config/servers.json",
        **environment,
    }
    if tunnels:
        env_values["COMPOSE_FILE"] = "docker-compose.yml:docker-compose.tunnel.yml"
    env_content = "\n".join(f"{name}={dotenv_quote(value)}" for name, value in env_values.items()) + "\n"
    write_private(env_path, env_content)
    write_private(inventory_path, json.dumps(servers, ensure_ascii=False, indent=2) + "\n")
    if tunnels:
        write_private(tunnel_path, render_tunnel_compose(tunnels))
    elif tunnel_path.exists():
        tunnel_path.unlink()

    run([sys.executable, "scripts/validate-config.py"])
    print(f"\n{text['done']}")
    if backup:
        print(f"Backup: {backup}")
    if shutil.which("docker"):
        run(["docker", "compose", "config", "-q"])
        if ask_bool(text["start"], False):
            run(["docker", "compose", "up", "-d", "--build"])
            run(["docker", "compose", "ps"])
    else:
        print("Docker Compose was not found; install it before starting the application.")
    print(f"\n{text['next']}")
    print(f"1. Point DNS for {domain} to this host and allow TCP 80/443.")
    print("2. Run: docker compose up -d --build")
    print("3. Configure the Telegram Mini App URL shown in .env through BotFather.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
