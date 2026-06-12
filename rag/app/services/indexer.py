import asyncio
from datetime import UTC, datetime
from uuid import UUID

from qdrant_client.models import PointStruct
from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, DocumentChunk, EmbeddingCache, EmbeddingRecord, Source
from app.retrieval.scripture_refs import normalize_scripture_ref, structured_scripture_refs
from app.retrieval.source_filters import normalize_source_type
from app.services.ai_cost import AiCostService
from app.services.chunker import SmartChunker
from app.services.openai_client import OpenAIService
from app.services.qdrant_service import QdrantService, point_id_for_chunk
from app.utils.tokens import count_tokens


NOT_CONFIRMED_DUPLICATE = text(
    """
    NOT EXISTS (
      SELECT 1
      FROM document_duplicate_relations duplicate_relation
      WHERE duplicate_relation.duplicate_document_id = documents.id
        AND duplicate_relation.review_status = 'confirmed'
        AND duplicate_relation.classification IN ('exact_duplicate', 'probable_duplicate')
    )
    """
)


class IndexingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.chunker = SmartChunker()
        self.openai = OpenAIService()
        self.qdrant = QdrantService()
        self.costs = AiCostService()

    async def index_pending(self, db: Session, limit: int, force: bool = False) -> int:
        if self.costs.is_indexing_paused(db):
            return 0
        stmt = select(Document).where(Document.text.is_not(None)).where(NOT_CONFIRMED_DUPLICATE).limit(limit)
        if not force:
            stmt = stmt.where(Document.is_indexed.is_(False))
        documents = db.scalars(stmt).all()
        total = 0
        for document in documents:
            total += await self.index_document(db, document, force=force)
            if self.costs.is_indexing_paused(db):
                break
        return total

    async def index_document_ids(self, db: Session, document_ids: list[UUID], force: bool = False) -> int:
        documents = db.scalars(
            select(Document).where(Document.id.in_(document_ids)).where(NOT_CONFIRMED_DUPLICATE)
        ).all()
        total = 0
        for document in documents:
            total += await self.index_document(db, document, force=force)
            if self.costs.is_indexing_paused(db):
                break
        return total

    async def index_document(self, db: Session, document: Document, force: bool = False) -> int:
        if not document.text or self.costs.is_indexing_paused(db):
            return 0

        source = db.get(Source, document.source_id)
        source_type = normalize_source_type((document.raw_metadata or {}).get("source_type") or (source.key if source else None))
        scripture_refs = sorted(
            {
                normalize_scripture_ref(ref) or ref
                for ref in (document.scripture_refs or [])
                if str(ref).strip()
            }
        )
        scripture_structured = structured_scripture_refs(scripture_refs)

        existing_chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
        ).all()
        chunks_outdated = any(
            (chunk.meta or {}).get("document_content_hash") not in (None, document.content_hash)
            for chunk in existing_chunks
        )
        if force or chunks_outdated:
            self._delete_document_chunks(db, document.id)
            existing_chunks = []

        if existing_chunks:
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
                document.is_indexed = True
                db.commit()
                return 0
        else:
            db_chunks = self._create_chunks(db, document, source_type, scripture_refs, scripture_structured)

        completed = await self._embed_and_upsert(
            db,
            db_chunks,
            document,
            source_type,
            scripture_refs,
            scripture_structured,
        )
        if completed:
            document.is_indexed = True
        db.commit()
        return len(db_chunks) if completed else 0

    def _delete_document_chunks(self, db: Session, document_id: UUID) -> None:
        chunk_ids = db.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id == document_id)).all()
        if chunk_ids:
            db.execute(delete(EmbeddingRecord).where(EmbeddingRecord.chunk_id.in_(chunk_ids)))
            db.execute(update(EmbeddingCache).where(EmbeddingCache.chunk_id.in_(chunk_ids)).values(chunk_id=None))
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        db.commit()

    def _create_chunks(
        self,
        db: Session,
        document: Document,
        source_type: str | None,
        scripture_refs: list[str],
        scripture_structured: list[dict],
    ) -> list[DocumentChunk]:
        db_chunks: list[DocumentChunk] = []
        for chunk in self.chunker.chunk(document.text or ""):
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
                    "source_key": source_type,
                    "author": document.author,
                    "category": document.category,
                    "topic": document.category,
                    "tags": document.tags or [],
                    "scripture_refs": scripture_refs,
                    "scripture_refs_structured": scripture_structured,
                    "canonical_url": document.canonical_url,
                    "published_at": document.published_at.isoformat() if document.published_at else None,
                    "document_version": document.version,
                    "document_content_hash": document.content_hash,
                },
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)
        db.commit()
        for chunk in db_chunks:
            db.refresh(chunk)
        return db_chunks

    async def _embed_and_upsert(
        self,
        db: Session,
        chunks: list[DocumentChunk],
        document: Document,
        source_type: str | None,
        scripture_refs: list[str],
        scripture_structured: list[dict],
    ) -> bool:
        for i in range(0, len(chunks), self.settings.embedding_batch_size):
            batch = chunks[i : i + self.settings.embedding_batch_size]
            cached_vectors = self._cached_vectors(db, batch)
            points: list[PointStruct] = []
            missing_chunks = [chunk for chunk in batch if chunk.text_hash not in cached_vectors]

            for chunk in batch:
                vector = cached_vectors.get(chunk.text_hash)
                if vector is None:
                    continue
                points.append(
                    PointStruct(
                        id=str(point_id_for_chunk(chunk.id)),
                        vector=vector,
                        payload=self._payload(chunk, document, source_type, scripture_refs, scripture_structured),
                    )
                )
                self._insert_embedding_record(db, chunk)

            if missing_chunks:
                requested_tokens = sum(count_tokens(chunk.text) for chunk in missing_chunks)
                if requested_tokens > self.costs.remaining_daily_embedding_tokens(db):
                    self.costs.pause_indexing(db, "daily_embedding_token_limit", "max_daily_embedding_tokens")
                    return False

                try:
                    vectors = await self.openai.embed_texts([chunk.text for chunk in missing_chunks])
                except Exception as exc:
                    error_code = "openai_insufficient_quota" if self.costs.is_quota_error(exc) else "openai_embedding_error"
                    self.costs.record_usage(
                        db,
                        kind="embedding",
                        model=self.settings.openai_embedding_model,
                        input_tokens=requested_tokens,
                        status="error",
                        error_code=error_code,
                        metadata={"document_id": str(document.id), "error": str(exc)[:500]},
                    )
                    if self.costs.is_quota_error(exc):
                        self.costs.pause_indexing(db, "openai_insufficient_quota", error_code)
                        return False
                    raise

                for chunk, vector in zip(missing_chunks, vectors, strict=True):
                    points.append(
                        PointStruct(
                            id=str(point_id_for_chunk(chunk.id)),
                            vector=vector,
                            payload=self._payload(chunk, document, source_type, scripture_refs, scripture_structured),
                        )
                    )
                    self._insert_embedding_record(db, chunk)
                    self._upsert_embedding_cache(db, chunk, vector)
                self.costs.record_usage(
                    db,
                    kind="embedding",
                    model=self.settings.openai_embedding_model,
                    input_tokens=requested_tokens,
                    status="ok",
                    metadata={"document_id": str(document.id), "chunks": len(missing_chunks)},
                )

            if points:
                self.qdrant.upsert(points)
            db.commit()
        return True

    def _payload(
        self,
        chunk: DocumentChunk,
        document: Document,
        source_type: str | None,
        scripture_refs: list[str],
        scripture_structured: list[dict],
    ) -> dict:
        return {
            "chunk_id": str(chunk.id),
            "document_id": str(document.id),
            "source_id": str(document.source_id),
            "source_key": source_type,
            "title": document.title,
            "author": document.author,
            "language": document.language,
            "category": document.category,
            "tags": document.tags or [],
            "scripture_refs": scripture_refs,
            "scripture_refs_structured": scripture_structured,
            "scripture_books": sorted({item["book"] for item in scripture_structured}),
            "canonical_url": document.canonical_url,
            "published_at": document.published_at.isoformat() if document.published_at else None,
            "section_title": chunk.section_title,
            "chunk_index": chunk.chunk_index,
            "text_hash": chunk.text_hash,
            "text_preview": chunk.text[:700],
        }

    def _cached_vectors(self, db: Session, chunks: list[DocumentChunk]) -> dict[str, list[float]]:
        hashes = sorted({chunk.text_hash for chunk in chunks})
        if not hashes:
            return {}
        rows = db.scalars(
            select(EmbeddingCache)
            .where(EmbeddingCache.content_hash.in_(hashes))
            .where(EmbeddingCache.model == self.settings.openai_embedding_model)
            .where(EmbeddingCache.dimensions == self.settings.openai_embedding_dimensions)
            .where(EmbeddingCache.vector.is_not(None))
        ).all()
        cached = {row.content_hash: row.vector for row in rows if row.vector}
        if cached:
            now = datetime.now(UTC)
            db.execute(
                update(EmbeddingCache)
                .where(EmbeddingCache.content_hash.in_(list(cached.keys())))
                .where(EmbeddingCache.model == self.settings.openai_embedding_model)
                .values(hit_count=EmbeddingCache.hit_count + 1, last_used_at=now, updated_at=now)
            )
        return cached

    def _insert_embedding_record(self, db: Session, chunk: DocumentChunk) -> None:
        stmt = (
            insert(EmbeddingRecord)
            .values(
                chunk_id=chunk.id,
                qdrant_point_id=point_id_for_chunk(chunk.id),
                model=self.settings.openai_embedding_model,
                dimensions=self.settings.openai_embedding_dimensions,
                content_hash=chunk.text_hash,
            )
            .on_conflict_do_nothing(constraint="uq_embedding_chunk_model_hash")
        )
        db.execute(stmt)

    def _upsert_embedding_cache(self, db: Session, chunk: DocumentChunk, vector: list[float]) -> None:
        now = datetime.now(UTC)
        stmt = (
            insert(EmbeddingCache)
            .values(
                content_hash=chunk.text_hash,
                model=self.settings.openai_embedding_model,
                dimensions=self.settings.openai_embedding_dimensions,
                vector=vector,
                vector_id=point_id_for_chunk(chunk.id),
                chunk_id=chunk.id,
                token_count=chunk.token_count,
                hit_count=0,
                updated_at=now,
                last_used_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_embedding_cache_hash_model",
                set_={
                    "vector": vector,
                    "vector_id": point_id_for_chunk(chunk.id),
                    "chunk_id": chunk.id,
                    "token_count": chunk.token_count,
                    "dimensions": self.settings.openai_embedding_dimensions,
                    "updated_at": now,
                    "last_used_at": now,
                },
            )
        )
        db.execute(stmt)


def run_indexing_sync(db: Session, limit: int, force: bool = False) -> int:
    return asyncio.run(IndexingService().index_pending(db, limit=limit, force=force))
