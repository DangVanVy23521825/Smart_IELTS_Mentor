from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import auth, feedback, jobs, submissions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])

