from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.retrieval.scripture_refs import extract_scripture_refs, normalize_scripture_ref
from app.retrieval.source_filters import expand_source_keys


class MetadataFilter(BaseModel):
    source_keys: list[str] | None = None
    languages: list[str] | None = None
    document_types: list[str] | None = None
    authors: list[str] | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    scripture_refs: list[str] | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None
    document_ids: list[UUID] | None = None

    @field_validator("source_keys")
    @classmethod
    def normalize_source_keys(cls, value: list[str] | None) -> list[str] | None:
        return expand_source_keys(value)

    @field_validator("scripture_refs")
    @classmethod
    def normalize_scripture_refs(cls, value: list[str] | None) -> list[str] | None:
        if not value:
            return value
        refs = {normalize_scripture_ref(item) or item.strip() for item in value if item.strip()}
        return sorted(refs)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    language: str | None = None
    limit: int = Field(default=12, ge=1, le=50)
    use_reranker: bool = True

    @model_validator(mode="after")
    def include_query_scripture_refs(self):
        refs = set(self.filters.scripture_refs or [])
        refs.update(extract_scripture_refs(self.query))
        self.filters.scripture_refs = sorted(refs) or None
        return self


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
    mode: str = "hybrid"
    warnings: list[str] = Field(default_factory=list)
    results: list[SearchResult]


class IndexRequest(BaseModel):
    document_ids: list[UUID] | None = None
    limit: int = Field(default=100, ge=1, le=5000)
    force: bool = False
