from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.retrieval.types import RetrievedChunk
from app.schemas.search import MetadataFilter
from app.services.openai_client import OpenAIService
from app.services.qdrant_service import QdrantService


class SemanticRetriever:
    def __init__(self) -> None:
        self.openai = OpenAIService()
        self.qdrant = QdrantService()

    async def search(
        self,
        db: Session,
        query: str,
        filters: MetadataFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        vector = (await self.openai.embed_texts([query]))[0]
        points = self.qdrant.search(vector, limit=limit, filters=filters.model_dump())
        chunk_ids = [UUID(str(point.payload["chunk_id"])) for point in points if point.payload]
        chunks_by_id = {
            chunk.id: chunk for chunk in db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))).all()
        }
        results: list[RetrievedChunk] = []
        for point in points:
            payload = point.payload or {}
            chunk_id = UUID(str(payload["chunk_id"]))
            chunk = chunks_by_id.get(chunk_id)
            if not chunk:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=UUID(str(payload["document_id"])),
                    title=payload.get("title") or chunk.title or "Untitled",
                    text=chunk.text,
                    author=payload.get("author"),
                    source_key=payload.get("source_key"),
                    canonical_url=payload.get("canonical_url"),
                    language=payload.get("language"),
                    section_title=payload.get("section_title"),
                    semantic_score=float(point.score or 0),
                    metadata=payload,
                )
            )
        return results
