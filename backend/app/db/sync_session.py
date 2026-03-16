from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _sync_postgres_dsn() -> str:
    return settings.postgres_dsn.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


engine = create_engine(_sync_postgres_dsn(), pool_pre_ping=True)
SessionLocalSync = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)

