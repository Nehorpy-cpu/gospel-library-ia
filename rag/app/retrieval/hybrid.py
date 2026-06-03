from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.query import QueryPlanner
from app.retrieval.ranking import HybridRanker, LLMReranker
from app.retrieval.semantic import SemanticRetriever
from app.retrieval.types import RetrievedChunk
from app.schemas.search import MetadataFilter
from app.utils.tokens import count_tokens


class HybridSearchService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.query_planner = QueryPlanner()
        self.bm25 = BM25Retriever()
        self.semantic = SemanticRetriever()
        self.ranker = HybridRanker()
        self.reranker = LLMReranker()

    async def search(
        self,
        db: Session,
        query: str,
        filters: MetadataFilter,
        language: str | None = None,
        limit: int | None = None,
        use_reranker: bool = True,
    ) -> tuple[str, list[RetrievedChunk]]:
        detected_language = self.query_planner.detect_language(query, language)
        if detected_language and not filters.languages:
            filters.languages = [detected_language]
        rewritten = await self.query_planner.rewrite(query, detected_language, filters)

        semantic = await self.semantic.search(
            db, rewritten, filters, limit=self.settings.retrieval_semantic_limit
        )
        bm25 = self.bm25.search(db, rewritten, filters, limit=self.settings.retrieval_bm25_limit)
        merged = self.ranker.merge(semantic, bm25)
        diversified = self._diversify(merged)
        final_limit = limit or self.settings.retrieval_final_limit
        if use_reranker:
            diversified = await self.reranker.rerank(rewritten, diversified, final_limit)
        return rewritten, self._fit_context(diversified[:final_limit])

    def _diversify(self, items: list[RetrievedChunk]) -> list[RetrievedChunk]:
        seen_docs: dict[str, int] = {}
        result: list[RetrievedChunk] = []
        overflow: list[RetrievedChunk] = []
        for item in items:
            count = seen_docs.get(str(item.document_id), 0)
            if count < 3:
                result.append(item)
                seen_docs[str(item.document_id)] = count + 1
            else:
                overflow.append(item)
        return result + overflow

    def _fit_context(self, items: list[RetrievedChunk]) -> list[RetrievedChunk]:
        fitted: list[RetrievedChunk] = []
        used = 0
        for item in items:
            tokens = count_tokens(item.text)
            if used + tokens > self.settings.retrieval_context_token_budget:
                continue
            fitted.append(item)
            used += tokens
        return fitted
