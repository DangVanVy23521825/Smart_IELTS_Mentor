from __future__ import annotations

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.observability import init_sentry
from app.db.session import engine
from app.services.redis_store import close_redis_client, get_redis_client, has_redis

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.app_env)
    init_sentry(service_name="smart-ielts-api")
    yield
    await close_redis_client()


app = FastAPI(
    title="Smart IELTS Mentor API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (frontend local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount api
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.middleware("http")
async def bind_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    start = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((perf_counter() - start) * 1000)
        log.exception("request_failed", duration_ms=duration_ms)
        structlog.contextvars.clear_contextvars()
        raise

    duration_ms = int((perf_counter() - start) * 1000)
    response.headers["x-request-id"] = request_id
    log.info("request_completed", status_code=response.status_code, duration_ms=duration_ms)
    structlog.contextvars.clear_contextvars()
    return response


@app.get("/api")
async def api_versions():
    return {"default": settings.api_v1_prefix, "available": [settings.api_v1_prefix]}


@app.get("/health")
async def health():
    checks: dict[str, dict[str, str | bool]] = {
        "database": {"ok": True},
        "redis": {"ok": True},
    }

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        checks["database"] = {"ok": False, "error": str(exc)}

    if not has_redis():
        checks["redis"] = {"ok": False, "error": "redis package unavailable"}
    else:
        client = await get_redis_client()
        try:
            if client is None:
                checks["redis"] = {"ok": False, "error": "redis client unavailable"}
                pong = False
            else:
                pong = await client.ping()
            if not pong:
                checks["redis"] = {"ok": False, "error": "ping failed"}
        except Exception as exc:
            checks["redis"] = {"ok": False, "error": str(exc)}

    ok = bool(checks["database"]["ok"]) and bool(checks["redis"]["ok"])
    payload = {"status": "ok" if ok else "degraded", "checks": checks}
    if ok:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)