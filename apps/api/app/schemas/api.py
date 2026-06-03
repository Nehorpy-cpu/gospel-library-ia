from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class MetadataFilter(BaseModel):
    source_keys: list[str] | None = None
    languages: list[str] | None = None
    authors: list[str] | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    published_after: date | None = None
    published_before: date | None = None
    document_ids: list[str] | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    language: str | None = Field(default=None, max_length=16)
    limit: int = Field(default=12, ge=1, le=50)
    use_reranker: bool = True


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    mode: str = "doctrinal_assistant"
    language: str | None = Field(default=None, max_length=16)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)


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
