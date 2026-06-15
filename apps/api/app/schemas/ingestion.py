from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

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
ENGLISH_MARKERS = {
    "and",
    "are",
    "christ",
    "come",
    "for",
    "from",
    "god",
    "is",
    "jesus",
    "of",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
    "you",
}
DISALLOWED_LANGUAGE_CODES = {"de", "deu", "en", "eng", "fr", "fra", "it", "ita", "por", "pt"}
PLACEHOLDER_MARKERS = (
    "[reemplazar antes de enviar]",
    "contenido de prueba",
    "documento de prueba",
    "no es una cita oficial",
    "no reemplaza ninguna fuente doctrinal",
    "placeholder",
)
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")


def appears_to_be_spanish(content: str) -> bool:
    words = re.findall(r"[a-záéíóúüñ]+", content.casefold())
    if not words:
        return False
    spanish_count = sum(word in SPANISH_MARKERS for word in words)
    english_count = sum(word in ENGLISH_MARKERS for word in words)
    return (
        spanish_count >= 8
        and spanish_count / len(words) >= 0.025
        and english_count <= spanish_count
    )


def has_disallowed_language_parameter(value: str | None) -> bool:
    if not value:
        return False
    language_values = parse_qs(urlsplit(value).query).get("lang", [])
    return any(language.casefold() in DISALLOWED_LANGUAGE_CODES for language in language_values)


def contains_placeholder(value: str | None) -> bool:
    normalized = normalize_text_es(value or "", preserve_newlines=True).casefold()
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


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
        if has_disallowed_language_parameter(self.source_url):
            raise ValueError("source_url contains a non-Spanish language parameter")
        if self.canonical_url:
            if has_disallowed_language_parameter(self.canonical_url):
                raise ValueError("canonical_url contains a non-Spanish language parameter")
            canonical_source = curated_source_for_url(self.canonical_url)
            if not canonical_source or canonical_source.key != source.key:
                raise ValueError("canonical_url must belong to the same authorized source")
        for metadata_key in ("source_url", "canonical_url"):
            metadata_url = self.metadata.get(metadata_key)
            if isinstance(metadata_url, str) and has_disallowed_language_parameter(metadata_url):
                raise ValueError(f"metadata.{metadata_key} contains a non-Spanish language parameter")
        if contains_raw_html(normalized_content):
            raise ValueError("content must be cleaned text, not raw HTML")
        if contains_placeholder(self.title) or contains_placeholder(normalized_content) or contains_placeholder(self.summary):
            raise ValueError("test or placeholder content is not accepted")
        if self.source_name.casefold() == "prueba n8n":
            raise ValueError("test sources are not accepted")
        if self.metadata.get("test_payload") is True or str(self.metadata.get("test_payload", "")).casefold() == "true":
            raise ValueError("test payloads are not accepted")
        language = (self.language or "").strip().casefold()
        if language != "es":
            raise ValueError("language must be es")
        if not appears_to_be_spanish(normalized_content):
            raise ValueError("content is not predominantly Spanish")
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
