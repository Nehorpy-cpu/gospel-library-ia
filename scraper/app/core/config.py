from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["local", "staging", "production"] = "local"
    service_name: str = "gospel-library-scraper"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://gospel:gospel@postgres:5432/gospel_library"
    redis_url: str = "redis://redis:6379/0"

    r2_endpoint_url: AnyHttpUrl | str = "http://minio:9000"
    r2_access_key_id: str = "minio"
    r2_secret_access_key: str = "miniosecret"
    r2_bucket: str = "gospel-library-assets"
    r2_region: str = "auto"

    crawler_concurrency: int = 8
    crawler_download_delay_seconds: float = 0.35
    crawler_timeout_seconds: int = 45
    crawler_max_depth: int = 4
    crawler_respect_robots_txt: bool = True
    crawler_user_agent_pool: list[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        ]
    )

    retry_max_attempts: int = 5
    retry_backoff_min_seconds: int = 2
    retry_backoff_max_seconds: int = 90

    playwright_enabled: bool = True
    playwright_headless: bool = True

    ocr_enabled: bool = True
    ocr_language: str = "eng+spa+por"
    pdf_text_density_threshold: int = 80

    allowed_domains: list[str] = Field(
        default_factory=lambda: [
            "discursosud.com",
            "speeches.byu.edu",
            "churchofjesuschrist.org",
            "www.churchofjesuschrist.org",
            "josephsmithpapers.org",
            "www.josephsmithpapers.org",
            "rsc.byu.edu",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
