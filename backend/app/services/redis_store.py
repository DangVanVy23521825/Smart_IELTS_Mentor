from __future__ import annotations

from typing import Any

from app.core.config import settings

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - defensive fallback
    redis = None


_client: Any = None


def has_redis() -> bool:
    return redis is not None


def build_key(*parts: str) -> str:
    return ":".join([settings.redis_key_prefix, *parts])


async def get_redis_client():
    global _client
    if redis is None:
        return None
    if _client is None:
        _client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _client


async def close_redis_client() -> None:
    global _client
    if _client is None:
        return
    close_fn = getattr(_client, "aclose", None)
    if close_fn is not None:
        await close_fn()
    else:  # pragma: no cover - compatibility fallback
        await _client.close()
    _client = None
