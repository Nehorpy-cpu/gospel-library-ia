from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import AiRuntimeState, AiUsageEvent, Document, DocumentChunk, EmbeddingCache, EmbeddingRecord
from app.services.chunker import SmartChunker
from app.utils.tokens import count_tokens

INDEXING_STATE_KEY = "indexing"


@dataclass(frozen=True)
class IndexingEstimate:
    documents_to_index: int
    estimated_chunks: int
    chunks_to_embed: int
    cached_chunks: int
    skipped_chunks: int
    estimated_tokens: int
    estimated_cost_usd: float
    model: str
    mode: str
    batch_size: int
    daily_token_limit: int
    daily_tokens_used: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "documentsToIndex": self.documents_to_index,
            "estimatedChunks": self.estimated_chunks,
            "chunksToEmbed": self.chunks_to_embed,
            "cachedChunks": self.cached_chunks,
            "skippedChunks": self.skipped_chunks,
            "estimatedTokens": self.estimated_tokens,
            "estimatedCostUsd": self.estimated_cost_usd,
            "model": self.model,
            "mode": self.mode,
            "batchSize": self.batch_size,
            "dailyTokenLimit": self.daily_token_limit,
            "dailyTokensUsed": self.daily_tokens_used,
            "remainingDailyTokens": max(self.daily_token_limit - self.daily_tokens_used, 0),
        }


class AiCostService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def embedding_cost(self, tokens: int) -> float:
        return round((tokens / 1000) * self.settings.embedding_token_price_per_1k, 6)

    def today_start(self) -> datetime:
        now = datetime.now(UTC)
        return datetime(now.year, now.month, now.day, tzinfo=UTC)

    def month_start(self) -> datetime:
        now = datetime.now(UTC)
        return datetime(now.year, now.month, 1, tzinfo=UTC)

    def daily_embedding_tokens_used(self, db: Session) -> int:
        return int(
            db.scalar(
                select(func.coalesce(func.sum(AiUsageEvent.input_tokens), 0)).where(
                    AiUsageEvent.kind == "embedding",
                    AiUsageEvent.status == "ok",
                    AiUsageEvent.created_at >= self.today_start(),
                )
            )
            or 0
        )

    def remaining_daily_embedding_tokens(self, db: Session) -> int:
        return max(self.settings.max_daily_embedding_tokens - self.daily_embedding_tokens_used(db), 0)

    def is_indexing_paused(self, db: Session) -> bool:
        state = db.get(AiRuntimeState, INDEXING_STATE_KEY)
        return bool(state and state.value.get("paused"))

    def pause_indexing(self, db: Session, reason: str, error_code: str | None = None) -> dict[str, Any]:
        value = {
            "paused": True,
            "reason": reason,
            "error_code": error_code,
            "paused_at": datetime.now(UTC).isoformat(),
        }
        stmt = (
            insert(AiRuntimeState)
            .values(key=INDEXING_STATE_KEY, value=value, updated_at=datetime.now(UTC))
            .on_conflict_do_update(
                index_elements=[AiRuntimeState.key],
                set_={"value": value, "updated_at": datetime.now(UTC)},
            )
        )
        db.execute(stmt)
        db.commit()
        return value

    def resume_indexing(self, db: Session) -> dict[str, Any]:
        value = {"paused": False, "resumed_at": datetime.now(UTC).isoformat()}
        stmt = (
            insert(AiRuntimeState)
            .values(key=INDEXING_STATE_KEY, value=value, updated_at=datetime.now(UTC))
            .on_conflict_do_update(
                index_elements=[AiRuntimeState.key],
                set_={"value": value, "updated_at": datetime.now(UTC)},
            )
        )
        db.execute(stmt)
        db.commit()
        return value

    def indexing_state(self, db: Session) -> dict[str, Any]:
        state = db.get(AiRuntimeState, INDEXING_STATE_KEY)
        return state.value if state else {"paused": False}

    def record_usage(
        self,
        db: Session,
        *,
        kind: str,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        status: str = "ok",
        error_code: str | None = None,
        user_id: UUID | None = None,
        workspace_id: UUID | None = None,
        document_id: UUID | None = None,
        chunk_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        db.add(
            AiUsageEvent(
                kind=kind,
                model=model,
                user_id=user_id,
                workspace_id=workspace_id,
                document_id=document_id,
                chunk_id=chunk_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=self.embedding_cost(input_tokens) if kind == "embedding" else 0.0,
                status=status,
                error_code=error_code,
                meta=metadata or {},
            )
        )
        db.commit()

    def usage_summary(self, db: Session) -> dict[str, Any]:
        month = self.month_start()
        rows = db.execute(
            select(
                AiUsageEvent.kind,
                func.coalesce(func.sum(AiUsageEvent.input_tokens), 0),
                func.count(AiUsageEvent.id),
                func.coalesce(func.sum(AiUsageEvent.estimated_cost_usd), 0.0),
            )
            .where(AiUsageEvent.created_at >= month)
            .group_by(AiUsageEvent.kind)
        ).all()
        today_tokens = self.daily_embedding_tokens_used(db)
        month_tokens = int(
            db.scalar(
                select(func.coalesce(func.sum(AiUsageEvent.input_tokens), 0)).where(
                    AiUsageEvent.kind == "embedding",
                    AiUsageEvent.status == "ok",
                    AiUsageEvent.created_at >= month,
                )
            )
            or 0
        )
        errors = db.execute(
            select(AiUsageEvent.created_at, AiUsageEvent.kind, AiUsageEvent.model, AiUsageEvent.error_code, AiUsageEvent.meta)
            .where(AiUsageEvent.status != "ok")
            .order_by(AiUsageEvent.created_at.desc())
            .limit(10)
        ).all()
        cache_rows = db.execute(
            select(
                func.count(EmbeddingCache.id),
                func.coalesce(func.sum(EmbeddingCache.hit_count), 0),
            )
        ).one()
        return {
            "mode": self.settings.ai_cost_mode,
            "model": self.settings.openai_embedding_model,
            "tokensUsedToday": today_tokens,
            "tokensUsedThisMonth": month_tokens,
            "dailyTokenLimit": self.settings.max_daily_embedding_tokens,
            "estimatedCostToday": self.embedding_cost(today_tokens),
            "estimatedCostThisMonth": self.embedding_cost(month_tokens),
            "embeddingBatchSize": self.settings.embedding_batch_size,
            "cacheEntries": int(cache_rows[0] or 0),
            "cacheHits": int(cache_rows[1] or 0),
            "usageByKind": [
                {
                    "kind": row[0],
                    "tokens": int(row[1] or 0),
                    "events": int(row[2] or 0),
                    "estimatedCostUsd": float(row[3] or 0),
                }
                for row in rows
            ],
            "indexing": self.indexing_state(db),
            "recentErrors": [
                {
                    "createdAt": row[0].isoformat() if row[0] else None,
                    "kind": row[1],
                    "model": row[2],
                    "errorCode": row[3],
                    "metadata": row[4] or {},
                }
                for row in errors
            ],
            "generatedAt": datetime.now(UTC).isoformat(),
        }

    def estimate_indexing(self, db: Session, *, limit: int = 100, force: bool = False) -> IndexingEstimate:
        stmt = select(Document).where(Document.text.is_not(None)).limit(limit)
        if not force:
            stmt = stmt.where(Document.is_indexed.is_(False))
        documents = db.scalars(stmt).all()
        chunker = SmartChunker()
        estimated_chunks = 0
        chunks_to_embed = 0
        cached_chunks = 0
        skipped_chunks = 0
        estimated_tokens = 0
        model = self.settings.openai_embedding_model
        for document in documents:
            existing_chunks = db.scalars(
                select(DocumentChunk).where(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index)
            ).all()
            candidates = existing_chunks or chunker.chunk(document.text or "")
            estimated_chunks += len(candidates)
            for chunk in candidates:
                text_hash = chunk.text_hash
                token_count = chunk.token_count if hasattr(chunk, "token_count") else count_tokens(chunk.text)
                has_embedding = bool(
                    db.scalar(
                        select(EmbeddingRecord.id)
                        .where(EmbeddingRecord.chunk_id == chunk.id)
                        .where(EmbeddingRecord.model == model)
                        .where(EmbeddingRecord.content_hash == text_hash)
                        .limit(1)
                    )
                    if isinstance(chunk, DocumentChunk)
                    else False
                )
                if has_embedding and not force:
                    skipped_chunks += 1
                    continue
                has_cache = bool(
                    db.scalar(
                        select(EmbeddingCache.id)
                        .where(EmbeddingCache.content_hash == text_hash)
                        .where(EmbeddingCache.model == model)
                        .where(EmbeddingCache.vector.is_not(None))
                        .limit(1)
                    )
                )
                if has_cache:
                    cached_chunks += 1
                else:
                    chunks_to_embed += 1
                    estimated_tokens += token_count
        return IndexingEstimate(
            documents_to_index=len(documents),
            estimated_chunks=estimated_chunks,
            chunks_to_embed=chunks_to_embed,
            cached_chunks=cached_chunks,
            skipped_chunks=skipped_chunks,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=self.embedding_cost(estimated_tokens),
            model=model,
            mode=self.settings.ai_cost_mode,
            batch_size=self.settings.embedding_batch_size,
            daily_token_limit=self.settings.max_daily_embedding_tokens,
            daily_tokens_used=self.daily_embedding_tokens_used(db),
        )

    def is_quota_error(self, exc: Exception) -> bool:
        value = str(exc).lower()
        return "insufficient_quota" in value or "quota" in value or "429" in value or "rate limit" in value
