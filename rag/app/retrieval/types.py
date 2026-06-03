from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    title: str
    text: str
    author: str | None = None
    source_key: str | None = None
    canonical_url: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    section_title: str | None = None
    semantic_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
    final_score: float = 0.0
    metadata: dict = field(default_factory=dict)

    def citation_quote(self, max_chars: int = 380) -> str:
        text = " ".join(self.text.split())
        return text[:max_chars].strip()
