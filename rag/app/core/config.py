from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["local", "staging", "production"] = "local"
    service_name: str = "gospel-library-rag"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://gospel:gospel@postgres:5432/gospel_library"
    redis_url: str = "redis://redis:6379/1"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-large"
    openai_embedding_dimensions: int = 3072
    openai_chat_model: str = "gpt-5.5"
    openai_rerank_model: str = "gpt-4.1-mini"
    ai_cost_mode: Literal["low", "balanced", "quality"] = "balanced"

    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "doctrinal_chunks_v1"

    chunk_target_tokens: int | None = Field(default=None, validation_alias=AliasChoices("CHUNK_TARGET_TOKENS", "CHUNK_SIZE"))
    chunk_min_tokens: int = 180
    chunk_max_tokens: int | None = None
    chunk_overlap_tokens: int | None = Field(default=None, validation_alias=AliasChoices("CHUNK_OVERLAP_TOKENS", "CHUNK_OVERLAP"))

    embedding_batch_size: int = 64
    max_daily_embedding_tokens: int = 100000
    max_user_chat_messages_per_day: int = 50
    max_user_talk_builder_per_day: int = 20

    rag_top_k: int | None = None
    retrieval_semantic_limit: int | None = None
    retrieval_bm25_limit: int | None = None
    retrieval_final_limit: int | None = None
    retrieval_context_token_budget: int | None = None
    retrieval_candidate_token_budget: int | None = None

    cache_ttl_seconds: int = 900
    memory_max_messages: int = 12
    answer_max_context_citations: int = 10
    embedding_token_price_per_1k: float = 0.00013

    @property
    def effective_chunk_target_tokens(self) -> int:
        if self.chunk_target_tokens is not None:
            return self.chunk_target_tokens
        return {"low": 950, "balanced": 650, "quality": 520}[self.ai_cost_mode]

    @property
    def effective_chunk_max_tokens(self) -> int:
        if self.chunk_max_tokens is not None:
            return self.chunk_max_tokens
        return {"low": 1300, "balanced": 950, "quality": 780}[self.ai_cost_mode]

    @property
    def effective_chunk_overlap_tokens(self) -> int:
        if self.chunk_overlap_tokens is not None:
            return self.chunk_overlap_tokens
        return {"low": 40, "balanced": 120, "quality": 180}[self.ai_cost_mode]

    @property
    def effective_retrieval_final_limit(self) -> int:
        if self.rag_top_k is not None:
            return self.rag_top_k
        if self.retrieval_final_limit is not None:
            return self.retrieval_final_limit
        return {"low": 6, "balanced": 12, "quality": 16}[self.ai_cost_mode]

    @property
    def effective_retrieval_semantic_limit(self) -> int:
        if self.retrieval_semantic_limit is not None:
            return self.retrieval_semantic_limit
        return {"low": 32, "balanced": 80, "quality": 120}[self.ai_cost_mode]

    @property
    def effective_retrieval_bm25_limit(self) -> int:
        if self.retrieval_bm25_limit is not None:
            return self.retrieval_bm25_limit
        return {"low": 32, "balanced": 80, "quality": 120}[self.ai_cost_mode]

    @property
    def effective_retrieval_context_token_budget(self) -> int:
        if self.retrieval_context_token_budget is not None:
            return self.retrieval_context_token_budget
        return {"low": 4500, "balanced": 10000, "quality": 14000}[self.ai_cost_mode]

    @property
    def effective_retrieval_candidate_token_budget(self) -> int:
        if self.retrieval_candidate_token_budget is not None:
            return self.retrieval_candidate_token_budget
        return {"low": 8000, "balanced": 22000, "quality": 32000}[self.ai_cost_mode]


@lru_cache
def get_settings() -> Settings:
    return Settings()
