from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from dataforge.backend.app.core.config import settings
from dataforge.backend.app.monitoring.logger import get_logger
from dataforge.backend.app.monitoring.metrics import metrics_collector

logger = get_logger(__name__)


@dataclass
class BrowserInstance:
    browser: Browser
    browser_type: str
    context: BrowserContext
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0
    is_healthy: bool = True
    proxy_url: Optional[str] = None
    user_agent: Optional[str] = None


class BrowserPool:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._instances: list[BrowserInstance] = []
        self._lock = asyncio.Lock()
        self._create_lock = asyncio.Lock()
        self._min_size = settings.browser_pool_min
        self._max_size = settings.browser_pool_max
        self._idle_timeout = settings.browser_pool_idle_timeout_seconds
        self._health_check_interval = settings.browser_pool_health_check_seconds
        self._max_uses = settings.browser_pool_max_uses_per_context
        self._running = False
        self._health_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._running = True
        await self._warm_pool()
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info(
            "Browser pool started",
            extra={"min_size": self._min_size, "max_size": self._max_size},
        )

    async def stop(self) -> None:
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            for instance in self._instances:
                try:
                    await instance.context.close()
                    await instance.browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
            self._instances.clear()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser pool stopped")

    async def _warm_pool(self) -> None:
        for _ in range(self._min_size):
            try:
                instance = await self._create_instance()
                async with self._lock:
                    self._instances.append(instance)
            except Exception as e:
                logger.error(f"Failed to warm browser: {e}")

    async def _create_instance(
        self,
        browser_type: str = "chromium",
        proxy: Optional[dict[str, str]] = None,
        user_agent: Optional[str] = None,
    ) -> BrowserInstance:
        if not self._playwright:
            raise RuntimeError("Playwright not started")

        browser_launcher = getattr(self._playwright, browser_type, None)
        if browser_launcher is None:
            raise ValueError(f"Unsupported browser type: {browser_type}")

        options: dict[str, Any] = {
            "headless": settings.browser_headless,
            "args": settings.browser_launch_args,
        }
        if proxy:
            options["proxy"] = proxy

        try:
            browser = await asyncio.wait_for(
                browser_launcher.launch(**options),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f"Browser launch timed out after 30s ({browser_type})")

        context_options: dict[str, Any] = {
            "user_agent": user_agent or settings.default_user_agent,
            "viewport": {
                "width": settings.browser_viewport_width,
                "height": settings.browser_viewport_height,
            },
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }
        if proxy:
            context_options["proxy"] = proxy

        context = await browser.new_context(**context_options)
        metrics_collector.browser_launches.labels(browser_type=browser_type).inc()

        return BrowserInstance(
            browser=browser,
            browser_type=browser_type,
            context=context,
            proxy_url=proxy.get("server") if proxy else None,
            user_agent=user_agent,
        )

    async def acquire(self, proxy: Optional[dict[str, str]] = None) -> BrowserInstance:
        # Try to find an available instance (under lock, brief)
        async with self._lock:
            for instance in self._instances:
                if (
                    instance.is_healthy
                    and instance.use_count < self._max_uses
                    and (proxy is None or instance.proxy_url == proxy.get("server"))
                ):
                    instance.last_used_at = time.time()
                    instance.use_count += 1
                    return instance

        # Need to create a new instance (under create_lock to prevent overshoot)
        async with self._create_lock:
            # Double-check after acquiring create lock
            async with self._lock:
                for instance in self._instances:
                    if (
                        instance.is_healthy
                        and instance.use_count < self._max_uses
                        and (proxy is None or instance.proxy_url == proxy.get("server"))
                    ):
                        instance.last_used_at = time.time()
                        instance.use_count += 1
                        return instance

                if len(self._instances) >= self._max_size:
                    # Pool is full, must wait
                    pass
                else:
                    instance = await self._create_instance(proxy=proxy)
                    self._instances.append(instance)
                    return instance

        # Pool is full - wait for one to become available
        deadline = time.time() + 30
        while time.time() < deadline:
            async with self._lock:
                for instance in self._instances:
                    if instance.is_healthy and instance.use_count < self._max_uses:
                        instance.last_used_at = time.time()
                        instance.use_count += 1
                        return instance
            await asyncio.sleep(0.5)

        raise RuntimeError("No available browser instances in pool (timeout)")

    async def release(self, instance: BrowserInstance, healthy: bool = True) -> None:
        instance.is_healthy = healthy
        instance.last_used_at = time.time()

        if not healthy or instance.use_count >= self._max_uses:
            try:
                await instance.context.close()
                await instance.browser.close()
            except Exception as e:
                logger.warning(f"Error destroying browser: {e}")
            async with self._lock:
                if instance in self._instances:
                    self._instances.remove(instance)

    async def _health_check_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._health_check_interval)
            try:
                await self._check_health()
            except Exception as e:
                logger.error(f"Health check failed: {e}")

    async def _check_health(self) -> None:
        healthy_instances = []
        async with self._lock:
            for instance in self._instances:
                try:
                    page = await instance.context.new_page()
                    await page.goto("about:blank", timeout=10000)
                    await page.close()
                    instance.is_healthy = True
                    healthy_instances.append(instance)
                except Exception:
                    instance.is_healthy = False
                    try:
                        await instance.context.close()
                        await instance.browser.close()
                    except Exception:
                        pass

        # Replenish pool outside the lock to avoid nested acquisitions
        async with self._create_lock:
            async with self._lock:
                self._instances = [i for i in self._instances if i.is_healthy]
                needed = self._min_size - len(self._instances)

            if needed > 0:
                new_instances = []
                for _ in range(needed):
                    try:
                        inst = await self._create_instance()
                        new_instances.append(inst)
                    except Exception as e:
                        logger.error(f"Failed to replenish browser: {e}")
                        break
                async with self._lock:
                    self._instances.extend(new_instances)

        # Update metrics
        async with self._lock:
            metrics_collector.browser_pool_size.labels(status="healthy").set(
                sum(1 for i in self._instances if i.is_healthy)
            )
            metrics_collector.browser_pool_size.labels(status="total").set(len(self._instances))

    @property
    def available_count(self) -> int:
        return sum(1 for i in self._instances if i.is_healthy)

    @property
    def total_count(self) -> int:
        return len(self._instances)
