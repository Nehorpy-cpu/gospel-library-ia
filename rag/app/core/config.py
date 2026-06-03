from functools import lru_cache
from typing import Literal

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

    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "doctrinal_chunks_v1"

    chunk_target_tokens: int = 650
    chunk_min_tokens: int = 180
    chunk_max_tokens: int = 950
    chunk_overlap_tokens: int = 120

    embedding_batch_size: int = 64
    retrieval_semantic_limit: int = 80
    retrieval_bm25_limit: int = 80
    retrieval_final_limit: int = 12
    retrieval_context_token_budget: int = 10000
    retrieval_candidate_token_budget: int = 22000

    cache_ttl_seconds: int = 900
    memory_max_messages: int = 12
    answer_max_context_citations: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
