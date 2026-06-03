import asyncio
from uuid import UUID

from qdrant_client.models import PointStruct
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, DocumentChunk, EmbeddingRecord, Source
from app.services.chunker import SmartChunker
from app.services.openai_client import OpenAIService
from app.services.qdrant_service import QdrantService, point_id_for_chunk


class IndexingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.chunker = SmartChunker()
        self.openai = OpenAIService()
        self.qdrant = QdrantService()

    async def index_pending(self, db: Session, limit: int, force: bool = False) -> int:
        stmt = select(Document).where(Document.text.is_not(None)).limit(limit)
        if not force:
            stmt = stmt.where(Document.is_indexed.is_(False))
        documents = db.scalars(stmt).all()
        total = 0
        for document in documents:
            total += await self.index_document(db, document, force=force)
        return total

    async def index_document_ids(self, db: Session, document_ids: list[UUID], force: bool = False) -> int:
        documents = db.scalars(select(Document).where(Document.id.in_(document_ids))).all()
        total = 0
        for document in documents:
            total += await self.index_document(db, document, force=force)
        return total

    async def index_document(self, db: Session, document: Document, force: bool = False) -> int:
        if not document.text:
            return 0
        if force:
            chunk_ids = db.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id == document.id)).all()
            if chunk_ids:
                db.execute(delete(EmbeddingRecord).where(EmbeddingRecord.chunk_id.in_(chunk_ids)))
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            db.commit()

        source = db.get(Source, document.source_id)
        existing_chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
        ).all()
        if existing_chunks and not force:
            db_chunks = db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .where(
                    ~select(EmbeddingRecord.id)
                    .where(EmbeddingRecord.chunk_id == DocumentChunk.id)
                    .where(EmbeddingRecord.model == self.settings.openai_embedding_model)
                    .where(EmbeddingRecord.content_hash == DocumentChunk.text_hash)
                    .exists()
                )
                .order_by(DocumentChunk.chunk_index)
            ).all()
            if not db_chunks:
                return 0
        else:
            chunks = self.chunker.chunk(document.text)
            db_chunks: list[DocumentChunk] = []
            for chunk in chunks:
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    chunker_version=self.chunker.version,
                    language=document.language,
                    title=document.title,
                    section_title=chunk.section_title,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    token_count=chunk.token_count,
                    text=chunk.text,
                    text_hash=chunk.text_hash,
                    meta={
                        "source_id": str(document.source_id),
                        "source_key": source.key if source else None,
                        "author": document.author,
                        "category": document.category,
                        "topic": document.category,
                        "tags": document.tags or [],
                        "scripture_refs": document.scripture_refs or [],
                        "canonical_url": document.canonical_url,
                        "published_at": document.published_at.isoformat() if document.published_at else None,
                        "document_version": document.version,
                    },
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)
            db.commit()
            for chunk in db_chunks:
                db.refresh(chunk)

        await self._embed_and_upsert(db, db_chunks, document, source)
        document.is_indexed = True
        db.commit()
        return len(db_chunks)

    async def _embed_and_upsert(
        self,
        db: Session,
        chunks: list[DocumentChunk],
        document: Document,
        source: Source | None,
    ) -> None:
        for i in range(0, len(chunks), self.settings.embedding_batch_size):
            batch = chunks[i : i + self.settings.embedding_batch_size]
            vectors = await self.openai.embed_texts([chunk.text for chunk in batch])
            points: list[PointStruct] = []
            for chunk, vector in zip(batch, vectors, strict=True):
                point_id = point_id_for_chunk(chunk.id)
                payload = {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "source_id": str(document.source_id),
                    "source_key": source.key if source else None,
                    "title": document.title,
                    "author": document.author,
                    "language": document.language,
                    "category": document.category,
                    "tags": document.tags or [],
                    "scripture_refs": document.scripture_refs or [],
                    "canonical_url": document.canonical_url,
                    "published_at": document.published_at.isoformat() if document.published_at else None,
                    "section_title": chunk.section_title,
                    "chunk_index": chunk.chunk_index,
                    "text_hash": chunk.text_hash,
                    "text_preview": chunk.text[:700],
                }
                points.append(PointStruct(id=str(point_id), vector=vector, payload=payload))
                stmt = (
                    insert(EmbeddingRecord)
                    .values(
                        chunk_id=chunk.id,
                        qdrant_point_id=point_id,
                        model=self.settings.openai_embedding_model,
                        dimensions=self.settings.openai_embedding_dimensions,
                        content_hash=chunk.text_hash,
                    )
                    .on_conflict_do_nothing(constraint="uq_embedding_chunk_model_hash")
                )
                db.execute(stmt)
            self.qdrant.upsert(points)
            db.commit()


def run_indexing_sync(db: Session, limit: int, force: bool = False) -> int:
    return asyncio.run(IndexingService().index_pending(db, limit=limit, force=force))
