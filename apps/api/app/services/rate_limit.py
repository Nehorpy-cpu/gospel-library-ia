import time
from datetime import UTC, datetime

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

    async def check(self, request: Request, limit: int | None = None, scope: str | None = None) -> None:
        max_hits = limit or self.settings.rate_limit_per_minute
        ip = request.client.host if request.client else "unknown"
        user_id = request.headers.get("X-User-Id", "anonymous")
        safe_scope = scope or request.url.path.replace("/", ":")
        key = f"rl:{safe_scope}:{ip}:{user_id}:{int(time.time() // 60)}"
        if self.redis:
            hits = self.redis.incr(key)
            self.redis.expire(key, 90)
        else:
            count, expires = _memory.get(key, (0, time.time() + 90))
            hits = count + 1
            _memory[key] = (hits, expires)
        if hits > max_hits:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    async def check_daily(self, request: Request, limit: int, scope: str) -> None:
        ip = request.client.host if request.client else "unknown"
        user_id = request.headers.get("X-User-Id", "anonymous")
        today = datetime.now(UTC).strftime("%Y%m%d")
        key = f"daily:{scope}:{today}:{user_id}:{ip}"
        if self.redis:
            hits = self.redis.incr(key)
            self.redis.expire(key, 60 * 60 * 36)
        else:
            count, expires = _memory.get(key, (0, time.time() + 60 * 60 * 36))
            if time.time() > expires:
                count = 0
            hits = count + 1
            _memory[key] = (hits, expires)
        if hits > limit:
            raise HTTPException(status_code=429, detail="Daily AI usage limit exceeded")
