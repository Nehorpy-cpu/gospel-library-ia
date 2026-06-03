from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gospel_library_rag",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    task_routes={
        "app.workers.tasks.index_pending_task": {"queue": "rag-indexing"},
        "app.workers.tasks.index_documents_task": {"queue": "rag-indexing"},
    },
)
