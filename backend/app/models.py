from __future__ import annotations

from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class ClientCreate(BaseModel):
    inbound_id: int
    email: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.@+-]+$")
    total_gb: float = Field(default=0, ge=0, le=100000)
    expiry_days: int = Field(default=0, ge=0, le=3650)
    limit_ip: int = Field(default=0, ge=0, le=100)
    # Empty by default: Vision is not valid for every VLESS transport/security
    # combination. A caller may opt in when the selected inbound supports it.
    flow: str = Field(default="", max_length=64)
    enable: bool = True


class ConfirmAction(BaseModel):
    confirm: str


class XrayInstallRequest(BaseModel):
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._+-]+$")
    confirm: str
