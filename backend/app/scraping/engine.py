from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.monitoring.logger import get_logger
from app.monitoring.metrics import metrics_collector
from app.proxy.manager import ProxyManager
from app.scraping.anti_bot import AntiBotDetector
from app.scraping.browser_pool import BrowserInstance, BrowserPool
from app.scraping.captcha import CAPTCHAHandler

logger = get_logger(__name__)


class ScrapingEngine:
    def __init__(
        self,
        browser_pool: BrowserPool,
        proxy_manager: ProxyManager,
        captcha_handler: CAPTCHAHandler,
    ) -> None:
        self.browser_pool = browser_pool
        self.proxy_manager = proxy_manager
        self.captcha_handler = captcha_handler
        self.anti_bot = AntiBotDetector()

    async def scrape(
        self,
        url: str,
        *,
        timeout_ms: Optional[int] = None,
        wait_for_selector: Optional[str] = None,
        wait_time_ms: int = 0,
        javascript_enabled: bool = True,
        screenshot: bool = False,
        pdf: bool = False,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        user_agent: Optional[str] = None,
        use_proxy: bool = True,
        extract_links: bool = True,
        extract_images: bool = True,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        start_time = time.time()
        result: dict[str, Any] = {
            "url": url,
            "success": False,
            "status_code": None,
            "content": None,
            "cleaned_text": None,
            "title": None,
            "error": None,
            "error_type": None,
            "screenshot_path": None,
            "pdf_path": None,
            "load_time_ms": None,
            "captcha_detected": False,
            "blocked_detected": False,
            "bot_score": None,
            "links": [],
            "images": [],
            "metadata": {},
            "headers": {},
            "proxy_id": None,
        }

        browser_instance: Optional[BrowserInstance] = None
        proxy_config = None
        current_proxy_id = None

        for attempt in range(max_retries):
            try:
                if use_proxy and not proxy_config:
                    proxy = await self.proxy_manager.get_proxy()
                    if proxy:
                        proxy_config = {"server": proxy["url"]}
                        current_proxy_id = proxy.get("id")

                browser_instance = await self.browser_pool.acquire(proxy=proxy_config)
                try:
                    page = await browser_instance.context.new_page()

                    if javascript_enabled:
                        await page.add_init_script(
                            self.anti_bot.generate_evasion_script()
                        )

                    if headers:
                        await page.set_extra_http_headers(headers)

                    if cookies and url:
                        cookie_list = [
                            {"name": k, "value": v, "url": url}
                            for k, v in cookies.items()
                        ]
                        await browser_instance.context.add_cookies(cookie_list)

                    await asyncio.sleep(AntiBotDetector.get_random_delay(1000, 3000))

                    timeout = timeout_ms or settings.default_timeout_ms
                    response = await page.goto(
                        url, timeout=timeout, wait_until="networkidle"
                    )

                    if response:
                        result["status_code"] = response.status
                        result["headers"] = dict(response.headers)

                    if wait_for_selector:
                        await page.wait_for_selector(wait_for_selector, timeout=timeout)
                    if wait_time_ms > 0:
                        await page.wait_for_timeout(wait_time_ms)

                    bot_check = self.anti_bot.check_page(page)
                    result["captcha_detected"] = bot_check.is_captcha
                    result["blocked_detected"] = (
                        bot_check.is_blocked or bot_check.is_cloudflare
                    )
                    result["bot_score"] = int(bot_check.confidence * 100)

                    if bot_check.is_captcha and self.captcha_handler.auto_solve:
                        captcha_info = await self.captcha_handler.detect_captcha(page)
                        if captcha_info:
                            await self.captcha_handler.solve_captcha(
                                page, captcha_info, url
                            )

                    if (
                        bot_check.is_blocked or bot_check.is_cloudflare
                    ) and attempt < max_retries - 1:
                        logger.warning(
                            f"Blocked on {url}, retrying with different proxy",
                            extra={"attempt": attempt, "url": url},
                        )
                        if current_proxy_id:
                            await self.proxy_manager.report_failure(current_proxy_id)
                            current_proxy_id = None
                            proxy_config = None
                        await page.close()
                        await self.browser_pool.release(browser_instance, healthy=False)
                        browser_instance = None
                        continue

                    result["title"] = await page.title()
                    result["content"] = await page.content()

                    result["cleaned_text"] = await page.evaluate("""() => {
                        const clone = document.body.cloneNode(true);
                        const selectors = ['script', 'style', 'noscript', 'iframe', 'svg', 'nav', 'footer', 'header'];
                        selectors.forEach(s => clone.querySelectorAll(s).forEach(el => el.remove()));
                        return clone.innerText;
                    }""")

                    if screenshot:
                        screenshot_bytes = await page.screenshot(
                            full_page=True, type="png"
                        )
                        screenshot_hash = hashlib.sha256(screenshot_bytes).hexdigest()[
                            :16
                        ]
                        screenshots_dir = (
                            Path(settings.storage_local_path) / "screenshots"
                        )
                        screenshots_dir.mkdir(parents=True, exist_ok=True)
                        screenshot_path = screenshots_dir / f"{screenshot_hash}.png"
                        screenshot_path.write_bytes(screenshot_bytes)
                        result["screenshot_path"] = str(screenshot_path)

                    if pdf:
                        pdf_bytes = await page.pdf(format="A4")
                        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()[:16]
                        pdfs_dir = Path(settings.storage_local_path) / "pdfs"
                        pdfs_dir.mkdir(parents=True, exist_ok=True)
                        pdf_path = pdfs_dir / f"{pdf_hash}.pdf"
                        pdf_path.write_bytes(pdf_bytes)
                        result["pdf_path"] = str(pdf_path)

                    if extract_links:
                        result["links"] = await page.evaluate("""() =>
                            Array.from(document.querySelectorAll('a[href]'), a => ({
                                href: a.href,
                                text: a.innerText.trim().slice(0, 200),
                                title: a.title || null,
                            })).filter(l => l.href.startsWith('http'))
                        """)

                    if extract_images:
                        result["images"] = await page.evaluate("""() =>
                            Array.from(document.querySelectorAll('img[src]'), img => ({
                                src: img.src,
                                alt: img.alt || null,
                                width: img.naturalWidth || null,
                                height: img.naturalHeight || null,
                            }))
                        """)

                    perf = await page.evaluate("""() => {
                        const nav = performance.getEntriesByType('navigation')[0];
                        return {
                            domContentLoaded: nav ? nav.domContentLoaded : null,
                            loadComplete: nav ? nav.loadEventEnd : null,
                            ttfb: nav ? nav.responseStart : null,
                        };
                    }""")
                    result["load_time_ms"] = perf.get("loadComplete", 0)
                    result["ttfb_ms"] = perf.get("ttfb", 0)
                    result["dom_content_loaded_ms"] = perf.get("domContentLoaded", 0)
                    result["proxy_id"] = current_proxy_id

                    await page.close()
                    result["success"] = True

                    if current_proxy_id:
                        await self.proxy_manager.report_success(current_proxy_id)
                    break

                finally:
                    if browser_instance:
                        await self.browser_pool.release(
                            browser_instance, healthy=result["success"]
                        )

            except Exception as e:
                error_type = type(e).__name__
                logger.error(
                    f"Scrape attempt {attempt + 1} failed for {url}",
                    extra={
                        "error": str(e),
                        "error_type": error_type,
                        "attempt": attempt,
                        "url": url,
                    },
                )
                if current_proxy_id:
                    await self.proxy_manager.report_failure(current_proxy_id)
                    proxy_config = None
                    current_proxy_id = None

                if attempt < max_retries - 1:
                    wait = settings.queue_retry_delay_seconds * (
                        settings.queue_retry_backoff_multiplier**attempt
                    )
                    await asyncio.sleep(wait)
                else:
                    result["error"] = str(e)
                    result["error_type"] = error_type

        duration_ms = (time.time() - start_time) * 1000
        result["duration_ms"] = int(duration_ms)
        metrics_collector.observe_scrape(
            status="completed" if result["success"] else "failed",
            duration_ms=duration_ms,
        )

        return result
