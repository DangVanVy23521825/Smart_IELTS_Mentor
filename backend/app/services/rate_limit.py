from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import time

from app.core.config import settings
from app.services.redis_store import build_key, get_redis_client


@dataclass
class LoginRateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class LoginRateLimiter:
    """
    Lightweight in-memory rate limiter for login attempts.
    Note: per-process only; move to Redis for multi-instance production.
    """

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def evaluate(self, key: str) -> LoginRateLimitDecision:
        now = time()
        window = settings.login_rate_limit_window_seconds
        limit = settings.login_rate_limit_attempts

        bucket = self._attempts[key]
        while bucket and (now - bucket[0]) > window:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(1, int(window - (now - bucket[0])))
            return LoginRateLimitDecision(allowed=False, retry_after_seconds=retry_after)
        return LoginRateLimitDecision(allowed=True, retry_after_seconds=0)

    def register_failure(self, key: str) -> None:
        self._attempts[key].append(time())

    def clear(self, key: str) -> None:
        self._attempts.pop(key, None)


class HybridLoginRateLimiter:
    """
    Redis-first login limiter with in-memory fallback.
    """

    def __init__(self) -> None:
        self._fallback = LoginRateLimiter()

    async def evaluate(self, key: str) -> LoginRateLimitDecision:
        client = await get_redis_client()
        if client is None:
            return self._fallback.evaluate(key)

        redis_key = build_key("rl", "login", key)
        try:
            attempts_raw = await client.get(redis_key)
            attempts = int(attempts_raw) if attempts_raw is not None else 0
            if attempts >= settings.login_rate_limit_attempts:
                ttl = await client.ttl(redis_key)
                retry_after = ttl if isinstance(ttl, int) and ttl > 0 else settings.login_rate_limit_window_seconds
                return LoginRateLimitDecision(allowed=False, retry_after_seconds=retry_after)
            return LoginRateLimitDecision(allowed=True, retry_after_seconds=0)
        except Exception:
            return self._fallback.evaluate(key)

    async def register_failure(self, key: str) -> None:
        client = await get_redis_client()
        if client is None:
            self._fallback.register_failure(key)
            return

        redis_key = build_key("rl", "login", key)
        try:
            pipe = client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, settings.login_rate_limit_window_seconds)
            await pipe.execute()
        except Exception:
            self._fallback.register_failure(key)

    async def clear(self, key: str) -> None:
        client = await get_redis_client()
        if client is None:
            self._fallback.clear(key)
            return

        redis_key = build_key("rl", "login", key)
        try:
            await client.delete(redis_key)
        except Exception:
            self._fallback.clear(key)


login_rate_limiter = HybridLoginRateLimiter()
