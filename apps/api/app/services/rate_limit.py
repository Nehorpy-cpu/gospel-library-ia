import time

import redis
from fastapi import HTTPException, Request

from app.core.config import get_settings

_memory: dict[str, tuple[int, float]] = {}


class RateLimiter:
    def __init__(self) -> None:
        self.settings = get_settings()
        try:
            self.redis = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)
            self.redis.ping()
        except Exception:
            self.redis = None

    async def check(self, request: Request, limit: int | None = None) -> None:
        max_hits = limit or self.settings.rate_limit_per_minute
        ip = request.client.host if request.client else "unknown"
        key = f"rl:{ip}:{int(time.time() // 60)}"
        if self.redis:
            hits = self.redis.incr(key)
            self.redis.expire(key, 90)
        else:
            count, expires = _memory.get(key, (0, time.time() + 90))
            hits = count + 1
            _memory[key] = (hits, expires)
        if hits > max_hits:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
