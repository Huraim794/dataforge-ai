from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update

from dataforge.backend.app.core.config import settings
from dataforge.backend.app.core.database import async_session_factory
from dataforge.backend.app.models.proxy import Proxy, ProxyStatus
from dataforge.backend.app.monitoring.logger import get_logger
from dataforge.backend.app.monitoring.metrics import metrics_collector
from dataforge.backend.app.proxy.checker import ProxyChecker
from dataforge.backend.app.proxy.rotator import ProxyRotator

logger = get_logger(__name__)


class ProxyManager:
    def __init__(self) -> None:
        self.checker = ProxyChecker()
        self.rotator: Optional[ProxyRotator] = None
        self._pool: list[dict[str, Any]] = []
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._pool_lock = asyncio.Lock()
        self._reload_lock = asyncio.Lock()

    async def start(self) -> None:
        self._running = True
        await self._load_proxies()
        self._check_task = asyncio.create_task(self._periodic_check())
        logger.info(
            "Proxy manager started",
            extra={"pool_size": len(self._pool)},
        )

    async def stop(self) -> None:
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Proxy manager stopped")

    async def get_proxy(self) -> Optional[dict[str, Any]]:
        async with self._pool_lock:
            usable = [p for p in self._pool if p.get("is_usable", False)]
            if not usable:
                logger.warning("No usable proxies available")
                return None
            if self.rotator:
                proxy = self.rotator.get_weighted()
            else:
                import random
                proxy = random.choice(usable)

            proxy_id = proxy.get("id")
            if proxy_id:
                async with async_session_factory() as session:
                    await session.execute(
                        update(Proxy)
                        .where(Proxy.id == proxy_id)
                        .values(
                            last_used_at=datetime.now(timezone.utc),
                            requests_this_minute=Proxy.requests_this_minute + 1,
                            total_requests=Proxy.total_requests + 1,
                        )
                    )
                    await session.commit()

            return proxy

    async def report_failure(self, proxy_id: str) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Proxy).where(Proxy.id == proxy_id)
            )
            proxy = result.scalar_one_or_none()
            if proxy:
                proxy.failure_count += 1
                proxy.consecutive_failures += 1
                if proxy.consecutive_failures >= settings.proxy_max_failures:
                    proxy.status = ProxyStatus.INACTIVE
                    logger.warning(
                        f"Proxy {proxy.host}:{proxy.port} marked inactive",
                        extra={"consecutive_failures": proxy.consecutive_failures},
                    )
                await session.commit()
                metrics_collector.proxy_requests.labels(status="failed").inc()

    async def report_success(self, proxy_id: str) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Proxy).where(Proxy.id == proxy_id)
            )
            proxy = result.scalar_one_or_none()
            if proxy:
                proxy.success_count += 1
                proxy.consecutive_failures = 0
                if proxy.status == ProxyStatus.INACTIVE:
                    proxy.status = ProxyStatus.ACTIVE
                await session.commit()
                metrics_collector.proxy_requests.labels(status="success").inc()

    async def add_proxy(self, proxy_data: dict[str, Any]) -> Proxy:
        async with async_session_factory() as session:
            proxy = Proxy(**proxy_data)
            session.add(proxy)
            await session.commit()
            await session.refresh(proxy)
        await self._reload_pool()
        return proxy

    async def remove_proxy(self, proxy_id: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Proxy).where(Proxy.id == proxy_id)
            )
            proxy = result.scalar_one_or_none()
            if proxy:
                await session.delete(proxy)
                await session.commit()
                await self._reload_pool()
                return True
        return False

    async def get_all_proxies(self) -> list[Proxy]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Proxy).order_by(Proxy.score.desc())
            )
            return list(result.scalars().all())

    async def _load_proxies(self) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE)
            )
            proxies = result.scalars().all()
            pool = [
                {
                    "id": p.id,
                    "host": p.host,
                    "port": p.port,
                    "protocol": p.protocol.value,
                    "username": p.username,
                    "password": p.password,
                    "url": p.url,
                    "weight": p.weight,
                    "score": p.score,
                    "country": p.country,
                    "anonymity_level": p.anonymity_level,
                    "is_usable": p.is_usable,
                    "consecutive_failures": p.consecutive_failures,
                    "latency_ms": p.latency_ms,
                }
                for p in proxies
            ]
        async with self._pool_lock:
            self._pool = pool
            self.rotator = ProxyRotator(pool) if pool else None
        metrics_collector.proxy_active.labels(status="active").set(len(pool))
        logger.info(f"Loaded {len(pool)} proxies")

    async def _reload_pool(self) -> None:
        if self._reload_lock.locked():
            return
        async with self._reload_lock:
            await self._load_proxies()

    async def _periodic_check(self) -> None:
        while self._running:
            await asyncio.sleep(settings.proxy_check_interval_seconds)
            try:
                await self._check_all_proxies()
            except Exception as e:
                logger.error(f"Proxy check cycle failed: {e}")

    async def _check_all_proxies(self) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Proxy).where(
                    Proxy.status.in_([ProxyStatus.ACTIVE, ProxyStatus.INACTIVE])
                )
            )
            proxies = list(result.scalars().all())

        if not proxies:
            return

        batch = [
            {
                "id": p.id,
                "host": p.host,
                "port": p.port,
                "protocol": p.protocol.value,
                "username": p.username,
                "password": p.password,
            }
            for p in proxies
        ]

        results = await self.checker.check_proxy_batch(batch, concurrency=20)

        async with async_session_factory() as session:
            for r in results:
                proxy_id = r.get("id")
                if not proxy_id:
                    continue
                p = next((x for x in proxies if x.id == proxy_id), None)
                if not p:
                    continue

                if r.get("alive"):
                    p.status = ProxyStatus.ACTIVE
                    p.latency_ms = r.get("latency_ms")
                    p.last_checked_at = datetime.now(timezone.utc)
                    if r.get("country"):
                        p.country = r.get("country")
                else:
                    p.consecutive_failures += 1
                    if p.consecutive_failures >= settings.proxy_max_failures:
                        p.status = ProxyStatus.INACTIVE
                    p.last_checked_at = datetime.now(timezone.utc)

            await session.commit()

        await self._reload_pool()
