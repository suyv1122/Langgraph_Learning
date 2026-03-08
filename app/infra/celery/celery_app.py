from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "enterprise_assistant",
    broker=settings.rabbitmq_url,
    backend=settings.celery_result_backend,
    include=[
        "app.modules.kb.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    timezone="UTC",
    task_always_eager=bool(settings.celery_task_always_eager),
)