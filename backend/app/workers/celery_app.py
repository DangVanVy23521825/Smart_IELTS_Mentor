from __future__ import annotations

from celery import Celery

from app.core.config import settings
from app.core.observability import init_sentry

init_sentry(service_name="smart-ielts-worker")

celery_app = Celery(
    "smart_ielts_mentor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_track_started = True
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.broker_transport_options = {"visibility_timeout": 60 * 60}
celery_app.conf.task_soft_time_limit = int(settings.openai_timeout_seconds * 4)
celery_app.conf.task_time_limit = int(settings.openai_timeout_seconds * 5)

