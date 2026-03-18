from __future__ import annotations

import hashlib
from datetime import timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.models import AssessmentResult, Job, JobStatus, Submission, SubmissionType, User
from app.db.session import get_db
from app.schemas.submissions import JobEnqueuedResponse, SubmissionResultResponse, SubmitWritingRequest
from app.services.quota import enforce_and_increment_daily_quota
from app.workers.tasks import process_writing_job

router = APIRouter()
log = structlog.get_logger()


def _word_count(text: str) -> int:
    return len(text.split())


@router.post("/writing", response_model=JobEnqueuedResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_writing(
    payload: SubmitWritingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobEnqueuedResponse:
    normalized_text = payload.text.strip()
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    # Deduplicate exact same essay to avoid duplicate jobs.
    existing_row = (
        await db.execute(
            select(Submission, Job)
            .join(Job, Job.submission_id == Submission.id, isouter=True)
            .where(
                Submission.user_id == current_user.id,
                Submission.type == SubmissionType.writing,
                Submission.content_hash == content_hash,
            )
            .order_by(Submission.created_at.desc())
            .limit(1)
        )
    ).one_or_none()
    if existing_row is not None:
        existing_submission, existing_job = existing_row
        if existing_job is not None and existing_job.status in {JobStatus.queued, JobStatus.running, JobStatus.succeeded}:
            return JobEnqueuedResponse(submission_id=existing_submission.id, job_id=existing_job.id)

    words = _word_count(payload.text)
    if words > settings.max_writing_words:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Essay too long: {words} words (max {settings.max_writing_words})",
        )

    await enforce_and_increment_daily_quota(db=db, user_id=current_user.id)

    submission = Submission(
        user_id=current_user.id,
        type=SubmissionType.writing,
        prompt=payload.prompt,
        text=normalized_text,
        content_hash=content_hash,
    )
    db.add(submission)
    await db.flush()

    job = Job(submission_id=submission.id)
    db.add(job)
    await db.commit()
    await db.refresh(submission)
    await db.refresh(job)

    try:
        process_writing_job.delay(job.id)
    except Exception as exc:
        job.status = JobStatus.failed
        job.error_message = "Queue unavailable: failed to enqueue job"
        await db.commit()
        log.exception("job_enqueue_failed", job_id=job.id, submission_id=submission.id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue is temporarily unavailable. Please try again shortly.",
        ) from exc

    return JobEnqueuedResponse(submission_id=submission.id, job_id=job.id)


@router.get("/{submission_id}", response_model=SubmissionResultResponse)
async def get_submission_result(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionResultResponse:
    submission = (
        await db.execute(
            select(Submission).where(
                Submission.id == str(submission_id),
                Submission.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    assessment_row = (
        await db.execute(select(AssessmentResult).where(AssessmentResult.submission_id == submission.id))
    ).scalar_one_or_none()

    created_at = submission.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return SubmissionResultResponse(
        submission_id=submission.id,
        type=submission.type.value,
        created_at=created_at.isoformat(),
        assessment=assessment_row.assessment_json if assessment_row else None,
    )
