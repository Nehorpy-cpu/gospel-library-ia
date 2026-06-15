from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.curated_sources import curated_source_for_url
from app.services.spanish_text import normalize_tag_es, normalize_text_es, normalize_visible_metadata


SPANISH_MARKERS = {
    "al",
    "como",
    "con",
    "cristo",
    "de",
    "del",
    "dios",
    "el",
    "en",
    "es",
    "evangelio",
    "jesucristo",
    "la",
    "las",
    "los",
    "para",
    "por",
    "que",
    "se",
    "su",
    "una",
    "y",
}
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")


def appears_to_be_spanish(content: str) -> bool:
    words = re.findall(r"[a-záéíóúüñ]+", content.casefold())
    if not words:
        return False
    marker_count = sum(word in SPANISH_MARKERS for word in words)
    return marker_count >= 8 and marker_count / len(words) >= 0.025


def contains_raw_html(content: str) -> bool:
    tags = HTML_TAG_RE.findall(content)
    lowered = content.casefold()
    return (
        any(tag in lowered for tag in ("<html", "<body", "<script", "<style", "<nav", "<header", "<footer"))
        or len(tags) >= 3
    )


class N8nDocumentIngestionRequest(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    author: str | None = Field(default=None, max_length=255)
    source_name: str = Field(min_length=2, max_length=255)
    source_url: str
    canonical_url: str | None = None
    language: str | None = Field(default=None, max_length=16)
    content_type: str = Field(default="text/plain", max_length=100)
    published_at: datetime | None = None
    year: int | None = Field(default=None, ge=1800, le=2200)
    content: str = Field(min_length=301, max_length=2_000_000)
    summary: str | None = Field(default=None, max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "source_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = normalize_text_es(value)
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("author", "summary")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_text_es(value, preserve_newlines=value is not None and "\n" in value)
        return normalized or None

    @field_validator("source_url", "canonical_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value.strip())
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("must be an absolute HTTPS URL")
        return value.strip()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        tags: list[str] = []
        seen: set[str] = set()
        for item in value:
            tag = normalize_tag_es(item)
            key = tag.casefold()
            if not tag or len(tag) > 100 or key in seen:
                continue
            seen.add(key)
            tags.append(tag)
        return tags

    @field_validator("metadata")
    @classmethod
    def normalize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_visible_metadata(value)

    @model_validator(mode="after")
    def validate_clean_spanish_content(self):
        normalized_content = normalize_text_es(self.content, preserve_newlines=True)
        source = curated_source_for_url(self.source_url)
        if not source:
            raise ValueError("source_url is not an authorized Spanish document URL")
        if self.canonical_url:
            canonical_source = curated_source_for_url(self.canonical_url)
            if not canonical_source or canonical_source.key != source.key:
                raise ValueError("canonical_url must belong to the same authorized source")
        if contains_raw_html(normalized_content):
            raise ValueError("content must be cleaned text, not raw HTML")
        language = (self.language or "").strip().casefold()
        if not language:
            if not appears_to_be_spanish(normalized_content):
                raise ValueError("language is missing and Spanish could not be confirmed")
            language = "es"
        if language not in {"es", "spa"}:
            raise ValueError("only Spanish content is accepted")
        self.language = "es"
        self.content = normalized_content
        if self.published_at is None and self.year is not None:
            self.published_at = datetime(self.year, 1, 1)
        return self


class N8nDocumentIngestionResponse(BaseModel):
    status: str
    document_id: str
    source_id: str
    canonical_url: str
    content_hash: str
    chunks: int


class N8nIngestionHealthResponse(BaseModel):
    status: str = "ok"
    required_header: str = "X-Ingestion-Key"
    accepted_language: str = "es"
    storage_used: bool = False
