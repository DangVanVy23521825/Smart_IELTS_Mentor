from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DailyUsage


def utc_day_string(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


async def enforce_and_increment_daily_quota(*, db: AsyncSession, user_id: str) -> None:
    day = utc_day_string()
    row = (await db.execute(select(DailyUsage).where(DailyUsage.user_id == user_id, DailyUsage.day == day))).scalar_one_or_none()
    if row is None:
        row = DailyUsage(user_id=user_id, day=day, submissions_count=0)
        db.add(row)
        await db.flush()

    if row.submissions_count >= settings.free_trial_daily_submissions:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily quota exceeded",
        )

    row.submissions_count += 1
    await db.flush()

