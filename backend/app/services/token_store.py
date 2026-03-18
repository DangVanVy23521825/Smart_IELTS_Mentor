from __future__ import annotations

from app.services.redis_store import build_key, get_redis_client


def _revoked_key(jti: str) -> str:
    return build_key("auth", "revoked", jti)


async def revoke_token_jti(jti: str, *, ttl_seconds: int) -> None:
    if not jti or ttl_seconds <= 0:
        return
    client = await get_redis_client()
    if client is None:
        return
    try:
        await client.set(_revoked_key(jti), "1", ex=ttl_seconds)
    except Exception:
        return


async def is_token_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    client = await get_redis_client()
    if client is None:
        return False
    try:
        return (await client.exists(_revoked_key(jti))) > 0
    except Exception:
        return False
