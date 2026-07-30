from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from prometheus_client import generate_latest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataforge.backend.app.core.database import check_database_health
from dataforge.backend.app.core.deps import get_current_user, get_db
from dataforge.backend.app.core.redis import check_redis_health
from dataforge.backend.app.models.job import Job, JobStatus
from dataforge.backend.app.models.proxy import Proxy, ProxyStatus
from dataforge.backend.app.monitoring.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    db_healthy = await check_database_health()
    redis_healthy = await check_redis_health()
    status = "healthy" if db_healthy and redis_healthy else "degraded"

    return {
        "status": status,
        "version": "1.0.0",
        "uptime_seconds": time.time() - start_time if "start_time" in globals() else 0,
        "database": "connected" if db_healthy else "disconnected",
        "redis": "connected" if redis_healthy else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics")
async def get_metrics() -> Any:
    return generate_latest()


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    total_jobs = (await db.execute(select(func.count(Job.id)))).scalar()
    active_jobs = (await db.execute(
        select(func.count(Job.id)).where(
            Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.RETRYING])
        )
    )).scalar()
    completed_24h = (await db.execute(
        select(func.count(Job.id)).where(
            Job.status == JobStatus.COMPLETED,
            Job.created_at >= last_24h,
        )
    )).scalar()
    failed_24h = (await db.execute(
        select(func.count(Job.id)).where(
            Job.status == JobStatus.FAILED,
            Job.created_at >= last_24h,
        )
    )).scalar()
    total_proxies = (await db.execute(select(func.count(Proxy.id)))).scalar()
    active_proxies = (await db.execute(
        select(func.count(Proxy.id)).where(Proxy.status == ProxyStatus.ACTIVE)
    )).scalar()

    success_rate = (completed_24h / (completed_24h + failed_24h) * 100) if (completed_24h + failed_24h) > 0 else 0

    return {
        "total_jobs": total_jobs or 0,
        "active_jobs": active_jobs or 0,
        "completed_24h": completed_24h or 0,
        "failed_24h": failed_24h or 0,
        "success_rate_24h": round(success_rate, 2),
        "total_proxies": total_proxies or 0,
        "active_proxies": active_proxies or 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/queue-status")
async def get_queue_status(
    current_user: dict = Depends(get_current_user),
) -> Any:
    from dataforge.backend.app.core.redis import get_queue_redis

    redis_client = await get_queue_redis()
    queues = {
        "critical": "queue:critical",
        "high": "queue:high",
        "default": "queue:default",
        "low": "queue:low",
        "retry": "queue:retry",
        "dead_letter": "queue:dead_letter",
        "scheduled": "queue:scheduled",
    }

    status = {}
    for name, key in queues.items():
        if name == "scheduled":
            length = await redis_client.zcard(key)
        else:
            length = await redis_client.llen(key)
        status[name] = length

    return status


start_time = time.time()
