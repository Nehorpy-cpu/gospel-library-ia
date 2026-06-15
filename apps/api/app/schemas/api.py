from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.scripture_refs import extract_scripture_refs, normalize_scripture_ref
from app.services.source_filters import source_type_aliases


class MetadataFilter(BaseModel):
    source_keys: list[str] | None = None
    languages: list[str] | None = None
    authors: list[str] | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    scripture_refs: list[str] | None = None
    published_after: date | None = None
    published_before: date | None = None
    document_ids: list[str] | None = None
    include_seed: bool | None = None

    @field_validator("source_keys")
    @classmethod
    def normalize_source_keys(cls, value: list[str] | None) -> list[str] | None:
        if not value:
            return value
        expanded: set[str] = set()
        for source_key in value:
            expanded.update(source_type_aliases(source_key))
        return sorted(expanded)

    @field_validator("scripture_refs")
    @classmethod
    def normalize_scripture_refs(cls, value: list[str] | None) -> list[str] | None:
        if not value:
            return value
        normalized = {normalize_scripture_ref(item) or item.strip() for item in value if item.strip()}
        return sorted(normalized)


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=1000)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    language: str | None = Field(default=None, max_length=16)
    limit: int = Field(default=12, ge=1, le=50)
    use_reranker: bool = True

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def include_query_scripture_refs(self):
        refs = set(self.filters.scripture_refs or [])
        refs.update(extract_scripture_refs(self.query))
        self.filters.scripture_refs = sorted(refs) or None
        return self


class SearchResponse(BaseModel):
    query: str
    rewritten_query: str | None = None
    mode: str = "postgres_text"
    warnings: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class CallingFocus(BaseModel):
    callingCategory: str | None = Field(default=None, max_length=120)
    callingName: str | None = Field(default=None, max_length=200)
    customCallingName: str | None = Field(default=None, max_length=200)
    callingFocusEnabled: bool = False

    def display_name(self) -> str | None:
        if not self.callingFocusEnabled:
            return None
        if self.callingName and "otro" in self.callingName.lower() and self.customCallingName:
            return self.customCallingName.strip() or None
        return (self.callingName or self.customCallingName or "").strip() or None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    mode: str = "doctrinal_assistant"
    language: str | None = Field(default=None, max_length=16)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    calling_focus: CallingFocus | None = None

    @model_validator(mode="after")
    def include_message_scripture_refs(self):
        refs = set(self.filters.scripture_refs or [])
        refs.update(extract_scripture_refs(self.message))
        self.filters.scripture_refs = sorted(refs) or None
        return self


class DocumentListResponse(BaseModel):
    items: list[dict[str, Any]]
    documents: list[dict[str, Any]] | None = None
    total: int | None = None
    limit: int | None = None
    offset: int | None = None
    next_cursor: str | None = None


class ReindexRequest(BaseModel):
    document_ids: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=5000)
    force: bool = False
