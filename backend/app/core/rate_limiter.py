from __future__ import annotations

import time
from typing import Optional

from fastapi import HTTPException, Request, status

from dataforge.backend.app.core.config import settings
from dataforge.backend.app.core.redis import get_cache_redis


class RateLimiter:
    def __init__(self, requests_per_second: int, burst_size: int, window_seconds: int = 1):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        client_key = self._get_client_key(request)
        if not client_key:
            return

        try:
            redis = await get_cache_redis()
            now = time.time()
            window_start = now - self.window_seconds
            key = f"ratelimit:{client_key}"

            await redis.zremrangebyscore(key, "-inf", window_start)
            count = await redis.zcard(key)

            if count >= self.burst_size:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )

            await redis.zadd(key, {str(now): now})
            await redis.expire(key, self.window_seconds * 2)
        except HTTPException:
            raise
        except Exception:
            pass

    def _get_client_key(self, request: Request) -> Optional[str]:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key[:16]}"

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            if len(token) > 20:
                return f"token:{token[:20]}"

        client = request.client
        if client:
            return f"ip:{client.host}"

        return None


login_limiter = RateLimiter(
    requests_per_second=settings.rate_limit_requests_per_second,
    burst_size=settings.rate_limit_burst_size,
    window_seconds=1,
)

api_limiter = RateLimiter(
    requests_per_second=settings.rate_limit_requests_per_second * 2,
    burst_size=settings.rate_limit_burst_size * 2,
    window_seconds=1,
)
