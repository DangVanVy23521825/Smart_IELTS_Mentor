from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(app_env: str) -> None:
    level = logging.INFO if app_env != "local" else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

