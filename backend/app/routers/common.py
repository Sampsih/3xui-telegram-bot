from __future__ import annotations

from fastapi import Depends, HTTPException, status

from ..config import ServerConfig, Settings, get_settings


def get_server(server_id: str, settings: Settings = Depends(get_settings)) -> ServerConfig:
    for server in settings.servers:
        if server.id == server_id:
            return server
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
