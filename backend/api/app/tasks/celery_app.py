"""Celery app. Owner: Developer 4. ML work is orchestrated here, not imported from Dev 1/2 folders."""

from celery import Celery

from backend.api.app.config import settings

celery_app = Celery(
    "bhumisetu",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
