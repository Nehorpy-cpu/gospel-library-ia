from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gospel_library_scraper",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    timezone="UTC",
    broker_connection_retry_on_startup=True,
    task_routes={
        "app.workers.tasks.discover_enabled_sources_task": {"queue": "scraping"},
        "app.workers.tasks.discover_source_task": {"queue": "scraping"},
        "app.workers.tasks.fetch_url_task": {"queue": "scraping"},
        "app.workers.tasks.download_asset_task": {"queue": "assets"},
        "app.workers.tasks.ocr_pdf_task": {"queue": "ocr"},
        "app.workers.tasks.index_incremental_task": {"queue": "indexing"},
    },
    beat_schedule={
        "discover-enabled-sources-hourly": {
            "task": "app.workers.tasks.discover_enabled_sources_task",
            "schedule": 3600.0,
        },
    },
)
