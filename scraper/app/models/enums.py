from enum import StrEnum


class SourceKey(StrEnum):
    DISCURSO_SUD = "discursosud"
    BYU_SPEECHES = "byu_speeches"
    BYU_SPEECHES_ES = "byu_speeches_es"
    CHURCH = "churchofjesuschrist"
    JOSEPH_SMITH_PAPERS = "josephsmithpapers"


class CrawlStatus(StrEnum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PARSED = "parsed"
    ASSET_DOWNLOADED = "asset_downloaded"
    OCR_PENDING = "ocr_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_UNCHANGED = "skipped_unchanged"


class AssetType(StrEnum):
    HTML = "html"
    PDF = "pdf"
    MP3 = "mp3"
    VIDEO = "video"
    IMAGE = "image"
    OCR_TEXT = "ocr_text"


class JobType(StrEnum):
    DISCOVER_SOURCE = "discover_source"
    FETCH_URL = "fetch_url"
    PARSE_DOCUMENT = "parse_document"
    DOWNLOAD_ASSET = "download_asset"
    EXTRACT_PDF = "extract_pdf"
    RUN_OCR = "run_ocr"
    INDEX_INCREMENTAL = "index_incremental"
