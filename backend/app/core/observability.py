from __future__ import annotations

from app.core.config import settings

_initialized = False

try:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
except Exception:  # pragma: no cover - optional dependency
    sentry_sdk = None
    CeleryIntegration = None
    FastApiIntegration = None
    LoggingIntegration = None


def init_sentry(service_name: str) -> None:
    global _initialized
    if _initialized or not settings.sentry_dsn or sentry_sdk is None:
        return

    integrations = []
    if FastApiIntegration is not None:
        integrations.append(FastApiIntegration())
    if CeleryIntegration is not None:
        integrations.append(CeleryIntegration())
    if LoggingIntegration is not None:
        integrations.append(LoggingIntegration(level=None, event_level=None))

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.app_env,
        server_name=service_name,
        integrations=integrations,
    )
    _initialized = True
