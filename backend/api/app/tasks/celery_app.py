"""Celery application for BhumiSetu."""

from celery import Celery

from backend.api.app.config import settings


celery_app = Celery(
    "bhumisetu",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.api.app.tasks.pipeline"],
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
