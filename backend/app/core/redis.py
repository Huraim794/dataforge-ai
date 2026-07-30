from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from dataforge.backend.app.core.config import settings

_queue_client: Optional[Redis] = None
_cache_client: Optional[Redis] = None


async def get_queue_redis() -> Redis:
    global _queue_client
    if _queue_client is None:
        _queue_client = await aioredis.from_url(
            str(settings.redis_queue_url),
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _queue_client


async def get_cache_redis() -> Redis:
    global _cache_client
    if _cache_client is None:
        _cache_client = await aioredis.from_url(
            str(settings.redis_cache_url),
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _cache_client


async def close_redis() -> None:
    global _queue_client, _cache_client
    if _queue_client:
        await _queue_client.close()
        _queue_client = None
    if _cache_client:
        await _cache_client.close()
        _cache_client = None


async def check_redis_health() -> bool:
    try:
        client = await get_cache_redis()
        await client.ping()
        return True
    except Exception:
        return False
