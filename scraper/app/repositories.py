from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.crawl import CrawlUrl, Document, DocumentAsset, IngestionJob, Source
from app.models.enums import CrawlStatus
from app.schemas.document import ExtractedDocument
from app.utils.hashing import sha256_text
from app.utils.source_types import source_type_for_url
from app.utils.urls import normalize_url


def get_or_create_source(db: Session, key: str, name: str, base_url: str) -> Source:
    source = db.scalar(select(Source).where(Source.key == key))
    if source:
        return source
    source = Source(key=key, name=name, base_url=base_url)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def upsert_crawl_url(
    db: Session,
    source_id: UUID,
    url: str,
    *,
    depth: int = 0,
    discovered_from: str | None = None,
    status: str = CrawlStatus.DISCOVERED,
) -> CrawlUrl:
    normalized = normalize_url(url)
    stmt = (
        insert(CrawlUrl)
        .values(
            source_id=source_id,
            url=url,
            normalized_url=normalized,
            depth=depth,
            discovered_from=discovered_from,
            status=status,
        )
        .on_conflict_do_update(
            constraint="uq_crawl_url_source_normalized",
            set_={"updated_at": datetime.utcnow()},
        )
        .returning(CrawlUrl)
    )
    crawl_url = db.execute(stmt).scalar_one()
    db.commit()
    return crawl_url


def mark_url(
    db: Session,
    crawl_url_id: UUID,
    status: str,
    *,
    content_hash: str | None = None,
    http_status: int | None = None,
    content_type: str | None = None,
    error: str | None = None,
) -> None:
    crawl_url = db.get(CrawlUrl, crawl_url_id)
    if not crawl_url:
        return
    crawl_url.status = status
    crawl_url.http_status = http_status
    crawl_url.content_type = content_type
    crawl_url.error = error
    crawl_url.last_crawled_at = datetime.utcnow()
    if content_hash:
        crawl_url.content_hash = content_hash
    db.commit()


def upsert_document(db: Session, source: Source, crawl_url: CrawlUrl, extracted: ExtractedDocument) -> Document:
    content_hash = sha256_text(extracted.text)
    existing = db.scalar(select(Document).where(Document.canonical_url == normalize_url(extracted.url)))
    metadata = {
        **(extracted.metadata or {}),
        "source_url": crawl_url.url,
        "source_type": source_type_for_url(source.key, crawl_url.url),
    }
    if existing:
        if existing.content_hash == content_hash:
            existing.updated_at = datetime.utcnow()
            existing.raw_metadata = {**(existing.raw_metadata or {}), **metadata}
            existing._ingestion_action = "unchanged"
            db.commit()
            return existing
        existing.version += 1
        existing.title = extracted.title
        existing.author = extracted.author
        existing.published_at = extracted.published_at
        existing.language = extracted.language
        existing.category = extracted.category
        existing.tags = extracted.tags
        existing.scripture_refs = extracted.scripture_refs
        existing.text = extracted.text
        existing.raw_metadata = metadata
        existing.content_hash = content_hash
        existing.is_indexed = False
        existing._ingestion_action = "updated"
        db.commit()
        return existing

    document = Document(
        source_id=source.id,
        crawl_url_id=crawl_url.id,
        title=extracted.title,
        canonical_url=normalize_url(extracted.url),
        author=extracted.author,
        published_at=extracted.published_at,
        language=extracted.language,
        category=extracted.category,
        tags=extracted.tags,
        scripture_refs=extracted.scripture_refs,
        text=extracted.text,
        raw_metadata=metadata,
        content_hash=content_hash,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document._ingestion_action = "created"
    return document


def create_asset(
    db: Session,
    *,
    document_id: UUID,
    asset_type: str,
    source_url: str | None,
    storage_key: str,
    mime_type: str | None,
    size_bytes: int,
    checksum: str,
) -> DocumentAsset:
    stmt = (
        insert(DocumentAsset)
        .values(
            document_id=document_id,
            asset_type=asset_type,
            source_url=source_url,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum=checksum,
        )
        .on_conflict_do_nothing(constraint="uq_document_asset_source")
        .returning(DocumentAsset)
    )
    row = db.execute(stmt).scalar_one_or_none()
    db.commit()
    if row:
        return row
    return db.scalar(
        select(DocumentAsset).where(
            DocumentAsset.document_id == document_id,
            DocumentAsset.asset_type == asset_type,
            DocumentAsset.source_url == source_url,
        )
    )


def create_job(
    db: Session,
    job_type: str,
    payload: dict,
    priority: int = 5,
    status: str = "queued",
    source_id: UUID | None = None,
    source: str | None = None,
) -> IngestionJob:
    source_value = source
    if source_value is None and payload:
        source_value = payload.get("source_key") or payload.get("source")
    if source_value is None and source_id is not None:
        source_row = db.get(Source, source_id)
        if source_row:
            source_value = source_row.key
    job = IngestionJob(
        job_type=job_type,
        payload=payload,
        priority=priority,
        status=status,
        source_id=source_id,
        source=source_value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def start_job(db: Session, job_id: UUID) -> None:
    job = db.get(IngestionJob, job_id)
    if not job:
        return
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.attempts += 1
    db.commit()


def finish_job(
    db: Session,
    job_id: UUID,
    status: str,
    error: str | None = None,
    *,
    documents_found: int | None = None,
    documents_created: int | None = None,
    documents_updated: int | None = None,
    errors: list[str] | None = None,
) -> None:
    job = db.get(IngestionJob, job_id)
    if not job:
        return
    job.status = status
    job.error = error
    if documents_found is not None:
        job.documents_found = documents_found
    if documents_created is not None:
        job.documents_created = documents_created
    if documents_updated is not None:
        job.documents_updated = documents_updated
    if errors is not None:
        job.errors = errors
    elif error:
        job.errors = [error]
    job.finished_at = datetime.utcnow()
    db.commit()
