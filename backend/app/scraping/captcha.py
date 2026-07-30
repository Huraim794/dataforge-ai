from __future__ import annotations

import asyncio
from typing import Optional

import httpx
from playwright.async_api import Page

from app.core.config import settings
from app.monitoring.logger import get_logger

logger = get_logger(__name__)


class CAPTCHAHandler:
    def __init__(self) -> None:
        self.api_key = settings.captcha_service_api_key
        self.service_url = settings.captcha_service_url
        self.auto_solve = settings.captcha_auto_solve
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def detect_captcha(self, page: Page) -> Optional[dict]:
        captcha_types = []

        recaptcha_v2 = await page.query_selector(".g-recaptcha")
        if recaptcha_v2:
            sitekey = await recaptcha_v2.get_attribute("data-sitekey")
            captcha_types.append(
                {
                    "type": "recaptcha_v2",
                    "sitekey": sitekey,
                    "selector": ".g-recaptcha",
                }
            )

        recaptcha_v3 = await page.query_selector("[data-callback]")
        if recaptcha_v3:
            sitekey = await recaptcha_v3.get_attribute("data-sitekey")
            if not sitekey:
                sitekey = await recaptcha_v3.get_attribute("data-key")
            captcha_types.append(
                {
                    "type": "recaptcha_v3",
                    "sitekey": sitekey,
                    "selector": "[data-callback]",
                }
            )

        hcaptcha = await page.query_selector(".h-captcha")
        if hcaptcha:
            sitekey = await hcaptcha.get_attribute("data-sitekey")
            captcha_types.append(
                {
                    "type": "hcaptcha",
                    "sitekey": sitekey,
                    "selector": ".h-captcha",
                }
            )

        turnstile = await page.query_selector(".cf-turnstile")
        if turnstile:
            sitekey = await turnstile.get_attribute("data-sitekey")
            captcha_types.append(
                {
                    "type": "turnstile",
                    "sitekey": sitekey,
                    "selector": ".cf-turnstile",
                }
            )

        if captcha_types:
            logger.info(f"CAPTCHA detected: {[c['type'] for c in captcha_types]}")
            return captcha_types[0]

        return None

    async def solve_captcha(
        self,
        page: Page,
        captcha_info: dict,
        page_url: str,
    ) -> Optional[str]:
        if not self.auto_solve or not self.api_key:
            logger.warning("Auto-solve disabled or no API key configured")
            return None

        captcha_type = captcha_info.get("type")
        sitekey = captcha_info.get("sitekey")

        if captcha_type in ("recaptcha_v2", "hcaptcha", "turnstile"):
            if sitekey is None:
                return None
            return await self._solve_standard(page, captcha_type, sitekey, page_url)
        elif captcha_type == "recaptcha_v3":
            logger.info("reCAPTCHA v3 detected - no action needed (invisible)")
            return None
        elif captcha_type == "image":
            return await self._solve_image(page, captcha_info)
        else:
            logger.warning(f"Unknown CAPTCHA type: {captcha_type}")
            return None

    async def _solve_standard(
        self,
        page: Page,
        captcha_type: str,
        sitekey: str,
        page_url: str,
    ) -> Optional[str]:
        client = await self._get_client()

        method_map = {
            "recaptcha_v2": "userrecaptcha",
            "hcaptcha": "hcaptcha",
            "turnstile": "turnstile",
        }
        method = method_map.get(captcha_type)
        if not method:
            return None

        try:
            resp = await client.post(
                f"{self.service_url}/in.php",
                data={
                    "key": self.api_key,
                    "method": method,
                    "googlekey": sitekey,
                    "pageurl": page_url,
                    "json": 1,
                },
            )
            result = resp.json()
            if result.get("status") != 1:
                logger.error(f"CAPTCHA submit failed: {result}")
                return None

            task_id = result.get("request")
            for _ in range(30):
                await asyncio.sleep(5)
                res = await client.get(
                    f"{self.service_url}/res.php",
                    params={
                        "key": self.api_key,
                        "action": "get",
                        "id": task_id,
                        "json": 1,
                    },
                )
                res_json = res.json()
                if res_json.get("status") == 1:
                    token = res_json.get("request")
                    await page.evaluate(f"""() => {{
                        const ta = document.getElementById('g-recaptcha-response');
                        if (ta) ta.innerHTML = '{token}';
                        const ta2 = document.querySelector('[name="g-recaptcha-response"]');
                        if (ta2) ta2.innerHTML = '{token}';
                    }}""")
                    logger.info("CAPTCHA solved successfully")
                    return token
                elif res_json.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                    logger.error("CAPTCHA unsolvable")
                    return None

            logger.error("CAPTCHA solve timeout")
            return None

        except Exception as e:
            logger.error(f"CAPTCHA solve failed: {e}")
            return None

    async def _solve_image(self, page: Page, captcha_info: dict) -> Optional[str]:
        client = await self._get_client()
        image_selector = captcha_info.get("selector", "img[src*='captcha']")

        try:
            img_element = await page.query_selector(image_selector)
            if not img_element:
                return None

            src = await img_element.get_attribute("src")
            if not src:
                return None

            if src.startswith("data:image"):
                img_data = src.split(",")[1]
            else:
                img_data = await page.evaluate(f"""async () => {{
                    try {{
                        const resp = await fetch('{src}');
                        const blob = await resp.blob();
                        return await new Promise((resolve) => {{
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result.split(',')[1]);
                            reader.readAsDataURL(blob);
                        }});
                    }} catch(e) {{
                        return null;
                    }}
                }}""")
                if not img_data:
                    return None

            resp = await client.post(
                f"{self.service_url}/in.php",
                data={
                    "key": self.api_key,
                    "method": "base64",
                    "body": img_data,
                    "json": 1,
                },
            )
            result = resp.json()
            if result.get("status") != 1:
                return None

            task_id = result.get("request")
            for _ in range(30):
                await asyncio.sleep(5)
                res = await client.get(
                    f"{self.service_url}/res.php",
                    params={
                        "key": self.api_key,
                        "action": "get",
                        "id": task_id,
                        "json": 1,
                    },
                )
                res_json = res.json()
                if res_json.get("status") == 1:
                    return res_json.get("request")
                elif res_json.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                    return None

            return None

        except Exception as e:
            logger.error(f"Image CAPTCHA solve failed: {e}")
            return None
