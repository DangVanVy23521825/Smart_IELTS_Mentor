from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select

from app.core.config import settings
from app.db.models import AssessmentResult, Job, JobStatus, Submission, SubmissionType
from app.db.sync_session import SessionLocalSync
from app.services.scoring.writing import assess_writing_task2
from app.workers.celery_app import celery_app

log = structlog.get_logger()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _can_start_processing(job: Job) -> bool:
    if job.status == JobStatus.queued:
        return True
    if job.status != JobStatus.running:
        return False

    if job.started_at is None:
        return True
    reclaim_after = timedelta(seconds=settings.job_reclaim_running_after_seconds)
    return job.started_at <= (_utcnow() - reclaim_after)


@celery_app.task(name="app.process_writing_job")
def process_writing_job(job_id: str) -> None:
    """
    Sync Celery task entrypoint for Writing Task 2.
    Call async scoring with asyncio.run().
    """
    with SessionLocalSync() as db:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job is None:
            log.warning("job_not_found", job_id=job_id)
            return

        if not _can_start_processing(job):
            log.info("job_not_queued_skip", job_id=job_id, status=str(job.status))
            return

        submission = db.execute(select(Submission).where(Submission.id == job.submission_id)).scalar_one_or_none()
        if submission is None:
            job.status = JobStatus.failed
            job.error_message = "Submission not found"
            job.finished_at = _utcnow()
            db.commit()
            return

        if submission.type != SubmissionType.writing:
            job.status = JobStatus.failed
            job.error_message = f"Unsupported submission type: {submission.type}"
            job.finished_at = _utcnow()
            db.commit()
            return

        essay = (submission.text or "").strip()
        if not essay:
            job.status = JobStatus.failed
            job.error_message = "Submission text is empty"
            job.finished_at = _utcnow()
            db.commit()
            return

        try:
            job.status = JobStatus.running
            job.progress = 10
            job.started_at = _utcnow()
            db.commit()

            assessment = asyncio.run(assess_writing_task2(essay=essay, prompt=submission.prompt))
            assessment_dict = assessment.model_dump()

            existing = db.execute(
                select(AssessmentResult).where(AssessmentResult.submission_id == submission.id)
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    AssessmentResult(
                        submission_id=submission.id,
                        schema_version=assessment.schema_version,
                        assessment_json=assessment_dict,
                        token_usage_json=None,
                    )
                )
            else:
                existing.schema_version = assessment.schema_version
                existing.assessment_json = assessment_dict
                existing.token_usage_json = None

            job.status = JobStatus.succeeded
            job.progress = 100
            job.error_message = None
            job.finished_at = _utcnow()
            db.commit()

            log.info("job_succeeded", job_id=job_id, submission_id=submission.id)
        except Exception as e:
            db.rollback()
            job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
            if job is not None:
                job.status = JobStatus.failed
                job.error_message = str(e)[:500]
                job.finished_at = _utcnow()
                db.commit()
            log.exception("job_failed", job_id=job_id, error=str(e))


@celery_app.task(name="app.process_job")
def process_job(job_id: str) -> None:
    process_writing_job(job_id)

