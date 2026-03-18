from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models import Job, Submission, User
from app.db.session import get_db
from app.schemas.submissions import JobStatusResponse

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    row = (
        await db.execute(
            select(Job, Submission)
            .join(Submission, Submission.id == Job.submission_id)
            .where(Job.id == str(job_id), Submission.user_id == current_user.id)
        )
    ).one_or_none()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job, submission = row
    return JobStatusResponse(
        job_id=job.id,
        submission_id=submission.id,
        status=job.status.value,
        progress=job.progress,
        error_message=job.error_message,
    )
