import json
import math

from app.core.config import get_settings
from app.retrieval.types import RetrievedChunk
from app.services.openai_client import OpenAIService
from app.utils.tokens import count_tokens


def normalize_scores(values: list[float | None]) -> list[float]:
    clean = [value or 0.0 for value in values]
    if not clean:
        return []
    lo = min(clean)
    hi = max(clean)
    if math.isclose(lo, hi):
        return [1.0 if value > 0 else 0.0 for value in clean]
    return [(value - lo) / (hi - lo) for value in clean]


class HybridRanker:
    def merge(self, semantic: list[RetrievedChunk], bm25: list[RetrievedChunk]) -> list[RetrievedChunk]:
        merged: dict[str, RetrievedChunk] = {}
        for item in semantic + bm25:
            key = str(item.chunk_id)
            if key not in merged:
                merged[key] = item
            else:
                existing = merged[key]
                existing.semantic_score = existing.semantic_score or item.semantic_score
                existing.bm25_score = existing.bm25_score or item.bm25_score

        items = list(merged.values())
        semantic_norm = normalize_scores([item.semantic_score for item in items])
        bm25_norm = normalize_scores([item.bm25_score for item in items])
        for item, sem, bm in zip(items, semantic_norm, bm25_norm, strict=True):
            trust_boost = 0.08 if item.source_key in {"churchofjesuschrist", "josephsmithpapers"} else 0.0
            lang_boost = 0.03 if item.language else 0.0
            item.final_score = 0.52 * sem + 0.36 * bm + trust_boost + lang_boost
        return sorted(items, key=lambda item: item.final_score, reverse=True)


class LLMReranker:
    def __init__(self) -> None:
        self.openai = OpenAIService()
        self.settings = get_settings()

    async def rerank(self, query: str, candidates: list[RetrievedChunk], limit: int) -> list[RetrievedChunk]:
        if not candidates:
            return []
        shortlist = self._fit_budget(candidates)
        numbered = "\n\n".join(
            f"[{i}] {item.title}\n{item.citation_quote(900)}" for i, item in enumerate(shortlist)
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a retrieval reranker for doctrinal research. Score relevance, source "
                    "quality, citation usefulness, and directness. Return JSON only: "
                    '{"scores":[{"index":0,"score":0.0,"reason":"..."}]}'
                ),
            },
            {"role": "user", "content": f"Query: {query}\n\nCandidates:\n{numbered}"},
        ]
        try:
            raw = await self.openai.complete(messages, temperature=0)
            parsed = json.loads(raw)
            scores = {int(item["index"]): float(item["score"]) for item in parsed.get("scores", [])}
            for index, item in enumerate(shortlist):
                item.rerank_score = scores.get(index, 0.0)
                item.final_score = 0.7 * item.rerank_score + 0.3 * item.final_score
            return sorted(shortlist, key=lambda item: item.final_score, reverse=True)[:limit]
        except Exception:
            return candidates[:limit]

    def _fit_budget(self, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        budget = self.settings.effective_retrieval_candidate_token_budget
        fitted: list[RetrievedChunk] = []
        used = 0
        for item in candidates:
            tokens = count_tokens(item.text)
            if used + tokens > budget:
                break
            fitted.append(item)
            used += tokens
        return fitted
