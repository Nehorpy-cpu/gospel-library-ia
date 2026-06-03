import asyncio
from uuid import UUID

from app.core.logging import configure_logging, logger
from app.db.session import SessionLocal
from app.services.indexer import IndexingService
from app.workers.celery_app import celery_app

configure_logging()
log = logger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def index_pending_task(self, limit: int = 100, force: bool = False):
    with SessionLocal() as db:
        count = asyncio.run(IndexingService().index_pending(db, limit=limit, force=force))
    log.info("rag_index_pending_completed", count=count, force=force)
    return {"chunks_indexed": count}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def index_documents_task(self, document_ids: list[str], force: bool = False):
    ids = [UUID(value) for value in document_ids]
    with SessionLocal() as db:
        count = asyncio.run(IndexingService().index_document_ids(db, ids, force=force))
    log.info("rag_index_documents_completed", count=count, documents=len(ids), force=force)
    return {"chunks_indexed": count}
