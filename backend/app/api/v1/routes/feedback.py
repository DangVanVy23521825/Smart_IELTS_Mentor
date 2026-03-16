from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models import Submission, User, UserFeedback
from app.db.session import get_db
from app.schemas.feedback import FeedbackCreateRequest, FeedbackCreateResponse

router = APIRouter()


@router.post("", response_model=FeedbackCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackCreateResponse:
    if payload.rating is None and (payload.message is None or not payload.message.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one of rating or message",
        )

    if payload.submission_id:
        submission = (
            await db.execute(
                select(Submission).where(
                    Submission.id == payload.submission_id,
                    Submission.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    feedback = UserFeedback(
        user_id=current_user.id,
        submission_id=payload.submission_id,
        rating=payload.rating,
        message=payload.message.strip() if payload.message else None,
        extra_data=payload.extra_data,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    created_at = feedback.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return FeedbackCreateResponse(id=feedback.id, created_at=created_at.isoformat())
