from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from . import config, security, seed
from .api import router
from .config import CORS_ORIGINS
from .webmock import router as webmock_router

log = logging.getLogger("conciliabot")

_LOCAL_TOKEN = security.load_or_create_token()


def _provided_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-conciliabot-token", "").strip()


class LocalAuthMiddleware(BaseHTTPMiddleware):
    """Protect /api/* for non-local callers.

    Loopback clients are trusted (they already share the machine and the DB);
    everyone else must present the local API token. This closes the "anyone on
    the network can drive the agent" gap without breaking the local PWA.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        if not config.AUTH_ENABLED or not path.startswith("/api") or path == "/api/health":
            return await call_next(request)
        provided = _provided_token(request)
        if provided and secrets.compare_digest(provided, _LOCAL_TOKEN):
            return await call_next(request)
        client = request.client.host if request.client else None
        if security.is_loopback(client):
            return await call_next(request)
        return JSONResponse({"detail": "no autorizado"}, status_code=401)


app = FastAPI(title="ConciliaBot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LocalAuthMiddleware)

app.include_router(router)
if config.WEBMOCK_ENABLED:
    app.include_router(webmock_router)


@app.on_event("startup")
def _startup() -> None:
    if config.AUTH_ENABLED and not config.AUTH_TOKEN:
        log.info(
            "Auth local activa: los clientes no-locales requieren el token de %s",
            config.AUTH_TOKEN_FILE,
        )
    if not config.WEBMOCK_ENABLED:
        log.info("ERP web mock deshabilitado (CONCILIABOT_WEBMOCK=off)")
    seed.seed_if_empty()


@app.on_event("shutdown")
def _shutdown() -> None:
    from .agent.erp import get_erp

    erp = get_erp()
    client = getattr(erp, "_client", None)
    close = getattr(client, "close", None)
    if callable(close):
        close()


_DIST = Path(__file__).resolve().parent.parent.parent / "dist"


class SPAStaticFiles(StaticFiles):
    """Serves the built PWA and falls back to index.html for client routes."""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and "." not in path.split("/")[-1]:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and "." not in path.split("/")[-1]:
            return await super().get_response("index.html", scope)
        return response


if _DIST.exists():
    # API routes are registered first, so this catch-all only serves the app.
    app.mount("/", SPAStaticFiles(directory=str(_DIST), html=True), name="app")
else:

    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "hint": "Frontend no compilado. Ejecuta `npm run build` o usa el dev server en :5173.",
            }
        )
