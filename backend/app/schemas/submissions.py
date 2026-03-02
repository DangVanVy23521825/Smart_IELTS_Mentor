from __future__ import annotations

from pydantic import BaseModel, Field


class SubmitWritingRequest(BaseModel):
    prompt: str | None = Field(default=None, description="Task prompt/question")
    text: str = Field(min_length=1)


class JobEnqueuedResponse(BaseModel):
    submission_id: str
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    submission_id: str
    status: str
    progress: int
    error_message: str | None = None


class SubmissionResultResponse(BaseModel):
    submission_id: str
    type: str
    created_at: str
    assessment: dict | None = None

