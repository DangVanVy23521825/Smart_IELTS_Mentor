from __future__ import annotations

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    submission_id: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    message: str | None = None
    extra_data: dict | None = None


class FeedbackCreateResponse(BaseModel):
    id: str
    created_at: str
