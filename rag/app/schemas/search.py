from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MetadataFilter(BaseModel):
    source_keys: list[str] | None = None
    languages: list[str] | None = None
    document_types: list[str] | None = None
    authors: list[str] | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None
    document_ids: list[UUID] | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    language: str | None = None
    limit: int = Field(default=12, ge=1, le=50)
    use_reranker: bool = True


class Citation(BaseModel):
    citation_id: int
    chunk_id: UUID
    document_id: UUID
    title: str
    author: str | None = None
    source_key: str | None = None
    canonical_url: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    section_title: str | None = None
    quote: str
    score: float


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    author: str | None = None
    source_key: str | None = None
    canonical_url: str | None = None
    language: str | None = None
    section_title: str | None = None
    snippet: str
    score: float
    semantic_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    rewritten_query: str | None = None
    results: list[SearchResult]


class IndexRequest(BaseModel):
    document_ids: list[UUID] | None = None
    limit: int = Field(default=100, ge=1, le=5000)
    force: bool = False
