from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import re
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from dotenv import dotenv_values
from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    name: str
    location: str | None = None

    ssh_host: str
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str
    ssh_key_path: str
    ssh_known_hosts_path: str
    ssh_connect_timeout: int = Field(default=10, ge=1, le=120)

    # URL must include the secret web base path when it is enabled.
    panel_url: str
    panel_api_token: SecretStr | None = None
    panel_username: str | None = None
    panel_password: SecretStr | None = None
    panel_verify_tls: bool = True

    # Host/IP encoded into client connection links.
    public_host: str | None = None

    # Fixed administrator-configured commands. They are never supplied by a
    # Mini App request. Prefer sudo wrappers callable by an unprivileged SSH
    # account instead of logging in as root.
    system_update_command: str | None = None
    system_update_timeout: int = Field(default=3600, ge=60, le=14_400)
    panel_update_command: str | None = None
    panel_update_timeout: int = Field(default=900, ge=60, le=14_400)

    # Optional escape hatch for sending arbitrary commands from Telegram.
    # Keep disabled unless ssh_user is an unprivileged dedicated account.
    enable_raw_ssh: bool = False
    raw_ssh_timeout: int = Field(default=60, ge=1, le=600)

    panel_type: Literal["3x-ui"] = "3x-ui"

    @model_validator(mode="after")
    def validate_panel_auth(self) -> "ServerConfig":
        if self.panel_api_token is None and not (self.panel_username and self.panel_password):
            raise ValueError("Set panel_api_token or panel_username + panel_password")
        parsed = urlparse(self.panel_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("panel_url must be an absolute HTTP(S) URL")
        host = parsed.hostname or ""
        private_host = host in {"localhost", "nl-tunnel"}
        try:
            private_host = private_host or ipaddress.ip_address(host).is_private
        except ValueError:
            pass
        if not self.panel_verify_tls and parsed.scheme == "https" and not private_host:
            raise ValueError("Do not disable TLS verification for a public HTTPS panel")
        if self.enable_raw_ssh and self.ssh_user == "root":
            raise ValueError("Raw SSH commands may not be enabled for the root account")
        return self


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "X-UI Telegram Admin"
    bot_token: SecretStr = SecretStr("change-me")
    mini_app_url: str = "https://example.com/app/"
    allowed_telegram_ids: list[int] = Field(default_factory=list)
    auth_max_age_seconds: int = Field(default=900, ge=60, le=86_400)
    dev_bypass_auth: bool = False
    dev_telegram_id: int = 1

    enable_api_docs: bool = False
    max_request_body_bytes: int = Field(default=65_536, ge=1024, le=1_048_576)
    backup_retention_days: int = Field(default=30, ge=1, le=3650)
    bot_output_max_chars: int = Field(default=12_000, ge=1000, le=100_000)
    server_probe_concurrency: int = Field(default=10, ge=1, le=100)

    data_dir: str = "/data"
    servers_file: str | None = None
    servers: list[ServerConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.servers_file and self.servers:
            raise ValueError("Configure either SERVERS_FILE or SERVERS, not both")
        if self.servers_file:
            self.servers = _load_servers_file(self.servers_file)
        host = (urlparse(self.mini_app_url).hostname or "").lower()
        if self.dev_bypass_auth and host not in {"localhost", "127.0.0.1"}:
            raise ValueError("DEV_BYPASS_AUTH may only be used with a localhost Mini App URL")
        if not self.dev_bypass_auth and self.bot_token.get_secret_value() == "change-me":
            raise ValueError("BOT_TOKEN is not configured")
        if not self.allowed_telegram_ids:
            raise ValueError("ALLOWED_TELEGRAM_IDS must not be empty")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


_ENV_REFERENCE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")


def _load_servers_file(filename: str) -> list[ServerConfig]:
    path = _resolve_servers_path(filename)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"SERVERS_FILE does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in SERVERS_FILE {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(payload, list):
        raise ValueError("SERVERS_FILE must contain a JSON array")
    expanded = _expand_environment_references(payload)
    servers = [ServerConfig.model_validate(item) for item in expanded]
    identifiers = [server.id for server in servers]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Server IDs in SERVERS_FILE must be unique")
    return servers


def _resolve_servers_path(filename: str) -> Path:
    """Use Docker's /config path, with a repository-local fallback for development."""
    path = Path(filename).expanduser()
    if path.exists() or not path.is_absolute():
        return path
    try:
        relative = path.relative_to("/config")
    except ValueError:
        return path
    local_path = Path("config") / relative
    return local_path if local_path.exists() else path


def _expand_environment_references(value):
    if isinstance(value, str):
        match = _ENV_REFERENCE.fullmatch(value)
        if not match:
            return value
        name = match.group(1)
        resolved = os.getenv(name)
        if resolved is None:
            resolved = _local_dotenv_values().get(name)
        if resolved is None:
            raise ValueError(f"Environment variable {name} referenced by SERVERS_FILE is not set")
        return resolved
    if isinstance(value, list):
        return [_expand_environment_references(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_environment_references(item) for key, item in value.items()}
    return value


@lru_cache
def _local_dotenv_values() -> dict[str, str | None]:
    return dict(dotenv_values(".env"))
