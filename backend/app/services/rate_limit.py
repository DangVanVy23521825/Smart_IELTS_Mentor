from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import time

from app.core.config import settings


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


login_rate_limiter = LoginRateLimiter()
