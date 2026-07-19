from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import get_settings
from .routers import clients_router, servers_router
from .services.xui import XUIError

settings = get_settings()
_docs_url = "/api/docs" if settings.enable_api_docs else None
_openapi_url = "/api/openapi.json" if settings.enable_api_docs else None
app = FastAPI(
    title=settings.app_name,
    docs_url=_docs_url,
    redoc_url=None,
    openapi_url=_openapi_url,
)

mini_app_host = urlparse(settings.mini_app_url).hostname
allowed_hosts = ["localhost", "127.0.0.1", "api", "testserver"]
if mini_app_host:
    allowed_hosts.append(mini_app_host)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.include_router(servers_router, prefix="/api")
app.include_router(clients_router, prefix="/api")


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_request_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://telegram.org; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.exception_handler(XUIError)
async def xui_error_handler(_, exc: XUIError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)[:1000]},
        headers={"Cache-Control": "no-store, max-age=0"},
    )


_module_path = Path(__file__).resolve()
_frontend_candidates = (
    _module_path.parents[1] / "frontend",  # Docker image: /app/frontend
    _module_path.parents[2] / "frontend",  # Source tree: <repo>/frontend
)
frontend_path = next((path for path in _frontend_candidates if path.is_dir()), _frontend_candidates[0])
app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="mini-app")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def readiness() -> JSONResponse:
    data_directory = Path(settings.data_dir)
    ready = bool(settings.servers) and data_directory.exists() and os.access(data_directory, os.W_OK)
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "servers": len(settings.servers),
            "data_dir_writable": data_directory.exists() and os.access(data_directory, os.W_OK),
        },
    )


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")
