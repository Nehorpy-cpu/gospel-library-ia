from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://gospel:gospel@postgres:5432/gospel_library"
    redis_url: str = "redis://redis:6379/2"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "doctrinal_chunks_v1"
    qdrant_dimensions: int = 3072
    rag_api_url: str = "http://rag-api:8090"
    scraper_api_url: str = "http://scraper-api:8080"
    cors_origins: str = "http://localhost:3000,http://web:3000"
    rate_limit_per_minute: int = 120
    chat_rate_limit_per_minute: int = 30
    max_user_chat_messages_per_day: int = 50
    max_user_talk_builder_per_day: int = 20
    ai_cost_mode: str = "balanced"
    rag_top_k: int = 12
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-large"
    openai_chat_model: str = "gpt-5.5"
    env: str = "development"
    auth_provider: str = "clerk"
    allow_dev_auth_headers: bool = True
    clerk_jwks_url: str = ""
    clerk_jwt_issuer: str = ""
    clerk_secret_key: str = ""
    clerk_admin_emails: str = ""
    admin_user_ids: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
