from __future__ import annotations

import time
from typing import Any, Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from dataforge.backend.app.core.config import settings
from dataforge.backend.app.monitoring.logger import get_logger

logger = get_logger(__name__)


class PlaywrightManager:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._browser_type: str = "chromium"

    async def launch(
        self,
        browser_type: str = "chromium",
        headless: Optional[bool] = None,
        proxy: Optional[dict[str, str]] = None,
        launch_args: Optional[list[str]] = None,
    ) -> Browser:
        self._browser_type = browser_type
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        browser_launcher = getattr(self._playwright, browser_type, None)
        if browser_launcher is None:
            raise ValueError(f"Unsupported browser type: {browser_type}")

        args = launch_args or settings.browser_launch_args
        options: dict[str, Any] = {
            "headless": headless if headless is not None else settings.browser_headless,
            "args": args,
        }
        if proxy:
            options["proxy"] = proxy

        self._browser = await browser_launcher.launch(**options)
        logger.info(
            "Browser launched",
            extra={
                "browser_type": browser_type,
                "headless": options["headless"],
                "has_proxy": proxy is not None,
            },
        )
        return self._browser

    async def create_context(
        self,
        browser: Optional[Browser] = None,
        user_agent: Optional[str] = None,
        viewport: Optional[dict[str, int]] = None,
        locale: Optional[str] = None,
        timezone_id: Optional[str] = None,
        proxy: Optional[dict[str, str]] = None,
        storage_state: Optional[dict] = None,
        extra_http_headers: Optional[dict[str, str]] = None,
    ) -> BrowserContext:
        b = browser or self._browser
        if b is None:
            raise RuntimeError("No browser available. Call launch() first.")

        context_options: dict[str, Any] = {
            "user_agent": user_agent or settings.default_user_agent,
            "viewport": viewport or {
                "width": settings.browser_viewport_width,
                "height": settings.browser_viewport_height,
            },
            "locale": locale or "en-US",
            "timezone_id": timezone_id or "America/New_York",
            "no_viewport": False,
        }
        if proxy:
            context_options["proxy"] = proxy
        if storage_state:
            context_options["storage_state"] = storage_state
        if extra_http_headers:
            context_options["extra_http_headers"] = extra_http_headers

        context = await b.new_context(**context_options)
        return context

    async def navigate(
        self,
        page: Page,
        url: str,
        timeout_ms: Optional[int] = None,
        wait_until: str = "networkidle",
        wait_for_selector: Optional[str] = None,
        wait_time_ms: int = 0,
    ) -> dict[str, Any]:
        timeout = timeout_ms or settings.default_timeout_ms
        metrics: dict[str, Any] = {"url": url}

        try:
            start_time = time.time()

            response = await page.goto(url, timeout=timeout, wait_until=wait_until)
            metrics["status_code"] = response.status if response else None
            metrics["final_url"] = page.url
            metrics["total_time_ms"] = (time.time() - start_time) * 1000

            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=timeout)
            if wait_time_ms > 0:
                await page.wait_for_timeout(wait_time_ms)

            metrics["title"] = await page.title()
            metrics["url"] = page.url

            perf = await page.evaluate("""() => {
                const perf = performance;
                return {
                    domContentLoaded: perf.getEntriesByType('navigation')[0]?.domContentLoaded || 0,
                    loadComplete: perf.getEntriesByType('navigation')[0]?.loadEventEnd || 0,
                    ttfb: perf.getEntriesByType('navigation')[0]?.responseStart || 0,
                }
            }""")
            metrics.update(perf)

            return metrics

        except Exception as e:
            logger.error(f"Navigation failed for {url}", extra={"error": str(e), "url": url})
            raise

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright manager closed")
