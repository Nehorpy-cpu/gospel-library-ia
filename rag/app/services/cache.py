import json
from typing import Any

import redis

from app.core.config import get_settings


class CacheService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)

    def get_json(self, key: str) -> Any | None:
        value = self.client.get(key)
        return json.loads(value) if value else None

    def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.client.setex(key, ttl or self.settings.cache_ttl_seconds, json.dumps(value, default=str))

    def delete_prefix(self, prefix: str) -> None:
        for key in self.client.scan_iter(f"{prefix}*"):
            self.client.delete(key)
