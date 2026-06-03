from pathlib import PurePosixPath
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.extractors.pdf import extract_pdf_text
from app.models.crawl import CrawlUrl, Source
from app.models.enums import AssetType, CrawlStatus
from app.parsers.sources import parser_for_url
from app.repositories import create_asset, mark_url, upsert_document
from app.schemas.document import ExtractedAsset
from app.storage.r2 import R2Storage
from app.utils.hashing import sha256_text
from app.utils.source_types import source_type_for_url


def source_by_id(db: Session, source_id: UUID) -> Source:
    source = db.get(Source, source_id)
    if not source:
        raise ValueError(f"Unknown source id {source_id}")
    return source


def persist_html_document(db: Session, crawl_url: CrawlUrl, html: str) -> tuple[UUID, list[ExtractedAsset], str]:
    source = source_by_id(db, crawl_url.source_id)
    parser = parser_for_url(crawl_url.url)
    extracted = parser.parse(crawl_url.url, html)
    extracted.metadata = {
        **(extracted.metadata or {}),
        "source_url": crawl_url.url,
        "source_type": source_type_for_url(source.key, crawl_url.url),
    }
    document = upsert_document(db, source, crawl_url, extracted)
    mark_url(db, crawl_url.id, CrawlStatus.PARSED, content_hash=sha256_text(extracted.text))
    return document.id, extracted.assets, getattr(document, "_ingestion_action", "updated")


def persist_asset(
    db: Session,
    *,
    document_id: UUID,
    asset: ExtractedAsset,
    content: bytes,
) -> None:
    storage = R2Storage()
    extension = PurePosixPath(asset.url.split("?")[0]).suffix or f".{asset.asset_type}"
    key = f"documents/{document_id}/assets/{asset.asset_type}/{sha256_text(asset.url)}{extension}"
    stored = storage.put_bytes(key, content, asset.mime_type)
    create_asset(
        db,
        document_id=document_id,
        asset_type=asset.asset_type,
        source_url=asset.url,
        storage_key=stored.key,
        mime_type=asset.mime_type,
        size_bytes=stored.size_bytes,
        checksum=stored.checksum,
    )


def persist_pdf_text_if_needed(db: Session, *, document_id: UUID, pdf_bytes: bytes, source_url: str) -> bool:
    result = extract_pdf_text(pdf_bytes)
    if result.text:
        asset = ExtractedAsset(url=source_url, asset_type=AssetType.OCR_TEXT, mime_type="text/plain")
        storage = R2Storage()
        key = f"documents/{document_id}/extracted/pdf_text_{sha256_text(source_url)}.txt"
        stored = storage.put_bytes(key, result.text.encode("utf-8"), "text/plain")
        create_asset(
            db,
            document_id=document_id,
            asset_type="pdf_text",
            source_url=source_url,
            storage_key=stored.key,
            mime_type="text/plain",
            size_bytes=stored.size_bytes,
            checksum=stored.checksum,
        )
    return result.needs_ocr


def mark_document_indexed(db: Session, document_id: UUID) -> None:
    from app.models.crawl import Document

    document = db.get(Document, document_id)
    if document:
        document.is_indexed = False
        document.status = "READY"
        db.commit()
