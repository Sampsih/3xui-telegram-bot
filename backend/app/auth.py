from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings
from .models import TelegramUser


def validate_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int) -> TelegramUser:
    try:
        values = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram initData") from exc

    received_hash = values.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram hash is missing")

    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram signature")

    try:
        auth_date = int(values["auth_date"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram auth_date") from exc

    now = int(time.time())
    if auth_date > now + 30 or now - auth_date > max_age_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram session has expired")

    try:
        user_data = json.loads(values["user"])
        return TelegramUser.model_validate(user_data)
    except (KeyError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram user is missing") from exc


async def current_user(
    x_telegram_init_data: str | None = Header(default=None),
    x_dev_telegram_id: int | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> TelegramUser:
    if settings.dev_bypass_auth and not x_telegram_init_data:
        user = TelegramUser(id=x_dev_telegram_id or settings.dev_telegram_id, first_name="Developer")
    else:
        if not x_telegram_init_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Open this page from Telegram")
        user = validate_telegram_init_data(
            x_telegram_init_data,
            settings.bot_token.get_secret_value(),
            settings.auth_max_age_seconds,
        )

    if not settings.allowed_telegram_ids or user.id not in settings.allowed_telegram_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account is not allowed")
    return user
