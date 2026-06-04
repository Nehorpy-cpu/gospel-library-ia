import json

from langdetect import LangDetectException, detect

from app.schemas.search import MetadataFilter
from app.retrieval.scripture_refs import extract_scripture_refs
from app.services.cache import CacheService
from app.services.openai_client import OpenAIService


class QueryPlanner:
    def __init__(self) -> None:
        self.openai = OpenAIService()
        self.cache = CacheService()

    def detect_language(self, query: str, fallback: str | None = None) -> str | None:
        if fallback:
            return fallback
        try:
            return detect(query)
        except LangDetectException:
            return None

    async def rewrite(self, query: str, language: str | None, filters: MetadataFilter) -> str:
        cache_key = f"rewrite:{language}:{query}:{filters.model_dump_json()}"
        cached = self.cache.get_json(cache_key)
        if cached:
            return cached["query"]
        messages = [
            {
                "role": "system",
                "content": (
                    "Rewrite the user query for doctrinal retrieval. Preserve named people, "
                    "scripture references, source constraints, and language. Return JSON only: "
                    '{"query":"..."}'
                ),
            },
            {"role": "user", "content": query},
        ]
        try:
            raw = await self.openai.complete(messages, temperature=0)
            rewritten = json.loads(raw).get("query") or query
        except Exception:
            rewritten = self._local_rewrite(query, filters)
        self.cache.set_json(cache_key, {"query": rewritten})
        return rewritten

    def _local_rewrite(self, query: str, filters: MetadataFilter) -> str:
        refs = sorted(set(filters.scripture_refs or []) | set(extract_scripture_refs(query)))
        if not refs:
            return query
        additions = " ".join(refs)
        return f"{query} {additions} scripture reference doctrinal citation".strip()
