from __future__ import annotations

import json
import time
from typing import Any, Optional

from redis.asyncio import Redis

from dataforge.backend.app.core.config import settings
from dataforge.backend.app.core.redis import get_queue_redis
from dataforge.backend.app.monitoring.logger import get_logger
from dataforge.backend.app.monitoring.metrics import metrics_collector

logger = get_logger(__name__)


class QueueManager:
    QUEUES = {
        "critical": "queue:critical",
        "high": "queue:high",
        "default": "queue:default",
        "low": "queue:low",
        "retry": "queue:retry",
        "dead_letter": "queue:dead_letter",
        "scheduled": "queue:scheduled",
    }

    def __init__(self) -> None:
        self._redis: Optional[Redis] = None

    async def start(self) -> None:
        self._redis = await get_queue_redis()
        logger.info("Queue manager started")

    async def stop(self) -> None:
        pass

    async def enqueue(
        self,
        job_data: dict[str, Any],
        queue: str = "default",
        priority: int = 5,
        delay_seconds: int = 0,
        retry_count: int = 0,
    ) -> str:
        job_id = job_data.get("id") or f"job_{int(time.time() * 1000)}_{id(job_data)}"
        payload = {
            "id": job_id,
            "data": job_data,
            "priority": priority,
            "enqueued_at": time.time(),
            "retry_count": retry_count,
            "max_retries": settings.queue_max_retries,
        }

        serialized = json.dumps(payload)

        if delay_seconds > 0:
            queue_key = self.QUEUES["scheduled"]
            await self._redis.zadd(queue_key, {serialized: time.time() + delay_seconds})
        else:
            queue_key = self._get_queue_key(queue)
            await self._redis.lpush(queue_key, serialized)

        metrics_collector.queue_depth.labels(queue=queue).inc()
        logger.info(f"Enqueued job {job_id} to {queue}", extra={"job_id": job_id, "queue": queue})
        return job_id

    async def dequeue(
        self,
        queue: str = "default",
        timeout: int = 5,
    ) -> Optional[dict[str, Any]]:
        if not self._redis:
            return None

        # Check scheduled jobs
        scheduled_key = self.QUEUES["scheduled"]
        now = time.time()
        scheduled_jobs = await self._redis.zrangebyscore(
            scheduled_key, 0, now, start=0, num=1
        )
        if scheduled_jobs:
            await self._redis.zrem(scheduled_key, scheduled_jobs[0])
            if scheduled_jobs[0]:
                metrics_collector.queue_depth.labels(queue="scheduled").dec()
                return json.loads(scheduled_jobs[0])

        # Priority order
        queue_priority = ["critical", "high", "default", "low", "retry"]
        for q in queue_priority:
            queue_key = self.QUEUES[q]
            result = await self._redis.brpop(queue_key, timeout=1)
            if result:
                metrics_collector.queue_depth.labels(queue=q).dec()
                payload = json.loads(result[1])
                payload["queue"] = q
                return payload

        return None

    async def requeue(
        self,
        payload: dict[str, Any],
        delay_seconds: Optional[int] = None,
    ) -> None:
        retry_count = payload.get("retry_count", 0) + 1
        max_retries = payload.get("max_retries", settings.queue_max_retries)

        if retry_count >= max_retries:
            await self._send_to_dead_letter(payload)
            return

        payload["retry_count"] = retry_count
        delay = delay_seconds or (settings.queue_retry_delay_seconds * (settings.queue_retry_backoff_multiplier ** (retry_count - 1)))
        payload["next_retry_at"] = time.time() + delay

        await self.enqueue(
            payload["data"],
            queue="retry",
            delay_seconds=int(delay),
            retry_count=retry_count,
        )
        metrics_collector.queue_processed.labels(status="requeued").inc()
        logger.info(
            f"Requeued job {payload.get('id')} (attempt {retry_count}/{max_retries})",
            extra={"job_id": payload.get("id"), "retry_count": retry_count},
        )

    async def _send_to_dead_letter(self, payload: dict[str, Any]) -> None:
        if not self._redis:
            return
        dead_key = self.QUEUES["dead_letter"]
        await self._redis.lpush(dead_key, json.dumps(payload))
        metrics_collector.queue_processed.labels(status="dead_letter").inc()
        logger.error(
            f"Job sent to dead letter queue: {payload.get('id')}",
            extra={"job_id": payload.get("id")},
        )

    async def get_queue_length(self, queue: str = "default") -> int:
        if not self._redis:
            return 0
        queue_key = self.QUEUES.get(queue, self.QUEUES["default"])
        return await self._redis.llen(queue_key)

    async def get_all_queue_lengths(self) -> dict[str, int]:
        lengths = {}
        for name, key in self.QUEUES.items():
            if not self._redis:
                lengths[name] = 0
            else:
                if name == "scheduled":
                    lengths[name] = await self._redis.zcard(key)
                else:
                    lengths[name] = await self._redis.llen(key)
        return lengths

    async def clear_queue(self, queue: str = "default") -> None:
        if not self._redis:
            return
        queue_key = self.QUEUES.get(queue, self.QUEUES["default"])
        await self._redis.delete(queue_key)

    def _get_queue_key(self, queue: str) -> str:
        return self.QUEUES.get(queue, self.QUEUES["default"])
