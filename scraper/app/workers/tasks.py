import asyncio
from datetime import datetime
from urllib.parse import unquote, urlparse
from uuid import UUID

from sqlalchemy import func, select

from app.crawler.runner import run_spider
from app.db.session import SessionLocal
from app.extractors.ocr import run_pdf_ocr
from app.logging.structured import configure_logging, logger
from app.models.crawl import CrawlUrl, Document, Source
from app.models.enums import AssetType, CrawlStatus
from app.parsers.sources import parser_for_url
from app.repositories import create_asset, create_job, finish_job, mark_url, start_job
from app.schemas.document import ExtractedAsset
from app.services.asset_validation import asset_response_error
from app.services.fetcher import Fetcher
from app.services.ingestion import (
    mark_document_indexed,
    persist_asset,
    persist_html_document,
    persist_pdf_text_if_needed,
)
from app.storage.r2 import R2Storage
from app.utils.hashing import sha256_text
from app.utils.source_types import source_type_for_url
from app.workers.celery_app import celery_app

configure_logging()
log = logger(__name__)


def _title_from_asset_url(url: str) -> str:
    slug = unquote(urlparse(url).path.rstrip("/").rsplit("/", 1)[-1] or "Downloaded asset")
    if "." in slug:
        slug = slug.rsplit(".", 1)[0]
    slug = slug.replace("-", " ").replace("_", " ").strip()
    return slug.title() if slug else "Downloaded asset"


def _looks_like_html(url: str, content_type: str) -> bool:
    normalized_url = url.lower().split("?", 1)[0]
    if normalized_url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".mp4", ".mov")):
        return False
    if not content_type:
        return True
    return any(token in content_type.lower() for token in ["text/html", "application/xhtml", "text/plain"])


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def discover_enabled_sources_task(self):
    with SessionLocal() as db:
        job = create_job(db, "discover_enabled_sources", {}, status="running")
        start_job(db, job.id)
        try:
            sources = db.scalars(select(Source).where(Source.enabled.is_(True))).all()
            for source in sources:
                discover_source_task.delay(str(source.id))
            finish_job(db, job.id, "completed", documents_found=len(sources))
            log.info("discover_enabled_sources_completed", sources=len(sources), job_id=str(job.id))
            return {"sources": len(sources), "job_id": str(job.id)}
        except Exception as exc:
            finish_job(db, job.id, "failed", str(exc))
            log.error("discover_enabled_sources_failed", error=str(exc), job_id=str(job.id))
            raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def discover_source_task(self, source_id: str):
    with SessionLocal() as db:
        source = db.get(Source, UUID(source_id))
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        job = create_job(
            db,
            "discover_source",
            {
                "source_id": source_id,
                "source_key": source.key,
                "base_url": source.base_url,
                "max_pages_per_run": source.max_pages_per_run,
                "crawl_strategy": source.crawl_strategy,
            },
            status="running",
            source_id=source.id,
        )
        start_job(db, job.id)
        try:
            before_count = db.scalar(select(func.count(CrawlUrl.id)).where(CrawlUrl.source_id == source.id)) or 0
            log.info("source_discovery_started", source_key=source.key, base_url=source.base_url, job_id=str(job.id))
            run_spider(source.key, source.base_url, max_pages_per_run=source.max_pages_per_run)
            after_count = db.scalar(select(func.count(CrawlUrl.id)).where(CrawlUrl.source_id == source.id)) or 0
            documents_found = max(after_count - before_count, 0)
            source.last_crawled_at = datetime.utcnow()
            db.commit()
            finish_job(db, job.id, "completed", documents_found=documents_found)
            log.info("source_discovery_finished", source_key=source.key, discovered=documents_found, job_id=str(job.id))
            return {"source": source.key, "documents_found": documents_found, "job_id": str(job.id)}
        except Exception as exc:
            finish_job(db, job.id, "failed", str(exc))
            log.error("source_discovery_failed", source_key=source.key, error=str(exc), job_id=str(job.id))
            raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def fetch_url_task(self, crawl_url_id: str):
    with SessionLocal() as db:
        crawl_url = db.get(CrawlUrl, UUID(crawl_url_id))
        if not crawl_url:
            raise ValueError(f"Crawl URL not found: {crawl_url_id}")
        job = create_job(
            db,
            "fetch_url",
            {"crawl_url_id": crawl_url_id, "url": crawl_url.url},
            status="running",
            source_id=crawl_url.source_id,
        )
        start_job(db, job.id)
        try:
            parser_for_url(crawl_url.url)
        except ValueError as exc:
            mark_url(db, crawl_url.id, CrawlStatus.SKIPPED_UNCHANGED, error=str(exc))
            finish_job(db, job.id, "skipped", str(exc), documents_skipped=1)
            log.info("url_skipped_no_parser", crawl_url_id=crawl_url_id, url=crawl_url.url, job_id=str(job.id))
            return {"crawl_url_id": crawl_url_id, "skipped": True, "reason": "no_parser", "job_id": str(job.id)}
        crawl_url.status = CrawlStatus.FETCHING
        crawl_url.attempts += 1
        db.commit()

        try:
            result = _run_async(Fetcher().fetch(crawl_url.url))
            log.info(
                "url_fetched",
                url=crawl_url.url,
                status_code=result.status_code,
                content_type=result.content_type,
                blocked=result.block.is_blocked,
                job_id=str(job.id),
            )

            if result.block.is_blocked:
                mark_url(
                    db,
                    crawl_url.id,
                    CrawlStatus.FAILED,
                    http_status=result.status_code,
                    content_type=result.content_type,
                    error=f"blocked:{result.block.reason}",
                )
                raise RuntimeError(f"Anti-block detection triggered: {result.block.reason}")

            content_type = result.content_type or ""
            if "pdf" in content_type or result.url.lower().split("?")[0].endswith(".pdf"):
                payload = _handle_direct_asset(db, crawl_url, result.content, "pdf", "application/pdf")
                finish_job(
                    db,
                    job.id,
                    "completed",
                    documents_found=1,
                    documents_created=1 if payload.get("action") == "created" else 0,
                    documents_updated=1 if payload.get("action") == "updated" else 0,
                    documents_skipped=1 if payload.get("action") == "unchanged" else 0,
                )
                return payload
            if "mpeg" in content_type or result.url.lower().split("?")[0].endswith(".mp3"):
                payload = _handle_direct_asset(db, crawl_url, result.content, "mp3", "audio/mpeg")
                finish_job(
                    db,
                    job.id,
                    "completed",
                    documents_found=1,
                    documents_created=1 if payload.get("action") == "created" else 0,
                    documents_updated=1 if payload.get("action") == "updated" else 0,
                    documents_skipped=1 if payload.get("action") == "unchanged" else 0,
                )
                return payload
            if not _looks_like_html(result.url, content_type):
                mark_url(
                    db,
                    crawl_url.id,
                    CrawlStatus.SKIPPED_UNCHANGED,
                    http_status=result.status_code,
                    content_type=content_type,
                    error=f"unsupported_content_type:{content_type or 'unknown'}",
                )
                finish_job(db, job.id, "skipped", f"unsupported_content_type:{content_type or 'unknown'}", documents_skipped=1)
                log.info(
                    "url_skipped_unsupported_content",
                    crawl_url_id=crawl_url_id,
                    url=crawl_url.url,
                    content_type=content_type,
                    job_id=str(job.id),
                )
                return {"crawl_url_id": crawl_url_id, "skipped": True, "reason": "unsupported_content_type", "job_id": str(job.id)}

            document_id, assets, action = persist_html_document(db, crawl_url, result.text)
            mark_url(db, crawl_url.id, CrawlStatus.PARSED, http_status=result.status_code, content_type=content_type)
            log.info(
                "document_persisted",
                document_id=str(document_id),
                url=crawl_url.url,
                assets=len(assets),
                action=action,
                job_id=str(job.id),
            )

            for asset in assets:
                download_asset_task.delay(str(document_id), asset.model_dump())

            index_incremental_task.delay(str(document_id))
            finish_job(
                db,
                job.id,
                "completed",
                documents_found=1,
                documents_created=1 if action == "created" else 0,
                documents_updated=1 if action == "updated" else 0,
                documents_skipped=1 if action == "unchanged" else 0,
            )
            return {"document_id": str(document_id), "assets": len(assets), "action": action, "job_id": str(job.id)}
        except Exception as exc:
            finish_job(db, job.id, "failed", str(exc), documents_failed=1)
            log.error("url_fetch_failed", crawl_url_id=crawl_url_id, url=crawl_url.url, error=str(exc), job_id=str(job.id))
            raise


def _handle_direct_asset(db, crawl_url: CrawlUrl, content: bytes, asset_type: str, mime_type: str):
    source = db.get(Source, crawl_url.source_id)
    title = _title_from_asset_url(crawl_url.url)
    from app.models.crawl import Document
    from app.utils.hashing import sha256_bytes

    content_hash = sha256_bytes(content)
    metadata = {
        "direct_asset": True,
        "source_url": crawl_url.url,
        "source_type": source_type_for_url(source.key, crawl_url.url),
    }
    document = db.scalar(select(Document).where(Document.canonical_url == crawl_url.normalized_url))
    if document:
        action = "unchanged" if document.content_hash == content_hash else "updated"
        document.title = title if document.title == "Untitled document" else document.title
        document.raw_metadata = {**(document.raw_metadata or {}), **metadata}
        document.content_hash = content_hash
        document.status = "READY"
        db.commit()
    else:
        action = "created"
        document = Document(
            source_id=source.id,
            crawl_url_id=crawl_url.id,
            title=title,
            canonical_url=crawl_url.normalized_url,
            language=None,
            text=None,
            raw_metadata=metadata,
            content_hash=content_hash,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
    asset = ExtractedAsset(url=crawl_url.url, asset_type=asset_type, mime_type=mime_type)
    persist_asset(db, document_id=document.id, asset=asset, content=content)
    if asset_type == "pdf":
        needs_ocr = persist_pdf_text_if_needed(db, document_id=document.id, pdf_bytes=content, source_url=crawl_url.url)
        if needs_ocr:
            ocr_pdf_task.delay(str(document.id), crawl_url.url)
    mark_url(db, crawl_url.id, CrawlStatus.COMPLETED)
    return {"document_id": str(document.id), "asset_type": asset_type, "action": action}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def download_asset_task(self, document_id: str, asset_payload: dict):
    asset = ExtractedAsset.model_validate(asset_payload)
    with SessionLocal() as db:
        document = db.get(Document, UUID(document_id))
        job = create_job(
            db,
            "download_asset",
            {"document_id": document_id, "url": asset.url, "asset_type": asset.asset_type},
            status="running",
            source_id=document.source_id if document else None,
        )
        start_job(db, job.id)
        try:
            result = _run_async(Fetcher().fetch_http(asset.url))
            response_error = asset_response_error(
                asset_type=str(asset.asset_type),
                final_url=result.url,
                status_code=result.status_code,
                content=result.content,
                content_type=result.content_type,
            )
            if response_error:
                finish_job(db, job.id, "failed", response_error)
                log.warning(
                    "asset_download_rejected",
                    document_id=document_id,
                    url=asset.url,
                    final_url=result.url,
                    error=response_error,
                    job_id=str(job.id),
                )
                return {
                    "document_id": document_id,
                    "asset": asset.asset_type,
                    "url": asset.url,
                    "job_id": str(job.id),
                    "status": "rejected",
                    "error": response_error,
                }
            persist_asset(db, document_id=UUID(document_id), asset=asset, content=result.content)
            if asset.asset_type == AssetType.PDF:
                needs_ocr = persist_pdf_text_if_needed(
                    db,
                    document_id=UUID(document_id),
                    pdf_bytes=result.content,
                    source_url=asset.url,
                )
                if needs_ocr:
                    ocr_pdf_task.delay(document_id, asset.url)
            finish_job(db, job.id, "completed")
            log.info("asset_downloaded", document_id=document_id, asset_type=asset.asset_type, url=asset.url, job_id=str(job.id))
            return {"document_id": document_id, "asset": asset.asset_type, "url": asset.url, "job_id": str(job.id)}
        except Exception as exc:
            finish_job(db, job.id, "failed", str(exc))
            log.error("asset_download_failed", document_id=document_id, url=asset.url, error=str(exc), job_id=str(job.id))
            raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=2)
def ocr_pdf_task(self, document_id: str, source_url: str):
    result = _run_async(Fetcher().fetch_http(source_url))
    ocr = run_pdf_ocr(result.content)
    storage = R2Storage()
    key = f"documents/{document_id}/ocr/{sha256_text(source_url)}.txt"
    stored = storage.put_bytes(key, ocr.text.encode("utf-8"), "text/plain")
    with SessionLocal() as db:
        document = db.get(Document, UUID(document_id))
        job = create_job(
            db,
            "run_ocr",
            {"document_id": document_id, "source_url": source_url},
            status="running",
            source_id=document.source_id if document else None,
        )
        start_job(db, job.id)
        try:
            create_asset(
                db,
                document_id=UUID(document_id),
                asset_type=AssetType.OCR_TEXT,
                source_url=source_url,
                storage_key=stored.key,
                mime_type="text/plain",
                size_bytes=stored.size_bytes,
                checksum=stored.checksum,
            )
            finish_job(db, job.id, "completed")
            log.info("ocr_completed", document_id=document_id, pages=ocr.pages, job_id=str(job.id))
            return {"document_id": document_id, "pages": ocr.pages, "job_id": str(job.id)}
        except Exception as exc:
            finish_job(db, job.id, "failed", str(exc))
            log.error("ocr_failed", document_id=document_id, error=str(exc), job_id=str(job.id))
            raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def index_incremental_task(self, document_id: str):
    with SessionLocal() as db:
        document = db.get(Document, UUID(document_id))
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        job = create_job(db, "index_incremental", {"document_id": document_id}, status="running", source_id=document.source_id)
        start_job(db, job.id)
        try:
            document.raw_metadata = {
                **(document.raw_metadata or {}),
                "incremental_index_ready_at": datetime.utcnow().isoformat(),
            }
            mark_document_indexed(db, document.id)
            finish_job(db, job.id, "completed")
            log.info("document_ready_for_rag", document_id=document_id, job_id=str(job.id))
            return {"document_id": document_id, "indexed": False, "ready_for_rag": True, "job_id": str(job.id)}
        except Exception as exc:
            finish_job(db, job.id, "failed", str(exc))
            log.error("document_ready_for_rag_failed", document_id=document_id, error=str(exc), job_id=str(job.id))
            raise
