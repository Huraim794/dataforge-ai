from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from playwright.async_api import Page

from dataforge.backend.app.monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BotDetectionResult:
    is_bot_detected: bool = False
    is_captcha: bool = False
    is_cloudflare: bool = False
    is_blocked: bool = False
    is_rate_limited: bool = False
    confidence: float = 0.0
    detector: str = ""
    details: dict = field(default_factory=dict)


class AntiBotDetector:
    CAPTCHA_PATTERNS = [
        r"captcha",
        r"recaptcha",
        r"hcaptcha",
        r"turnstile",
        r"verify.*human",
        r"are you a robot",
        r"robot.*check",
        r"security.*check",
        r"cf-challenge",
        r"challenge-platform",
        r"g-recaptcha",
        r"data-sitekey",
        r"api\.js\?render=",
    ]

    BLOCK_PATTERNS = [
        r"access denied",
        r"blocked",
        r"forbidden",
        r"404 not found",
        r"rate limit",
        r"too many requests",
        r"please wait",
        r"checking your browser",
        r"browser integrity check",
        r"cf-browser-verification",
        r"attention required",
        r"automated access",
        r"unusual traffic",
    ]

    CLOUDFLARE_PATTERNS = [
        r"cloudflare",
        r"cf-ray",
        r"__cfduid",
        r"cf_email",
        r"cdn-cgi",
    ]

    @staticmethod
    def random_user_agent() -> str:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
        return random.choice(user_agents)

    @staticmethod
    def random_viewport() -> dict[str, int]:
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
            {"width": 2560, "height": 1440},
        ]
        return random.choice(viewports)

    @staticmethod
    def random_locale() -> str:
        locales = ["en-US", "en-GB", "en-CA", "en-AU", "en-IN"]
        return random.choice(locales)

    @staticmethod
    def random_timezone() -> str:
        timezones = [
            "America/New_York",
            "America/Chicago",
            "America/Los_Angeles",
            "America/Denver",
            "Europe/London",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Australia/Sydney",
            "UTC",
        ]
        return random.choice(timezones)

    async def check_page(self, page: Page) -> BotDetectionResult:
        result = BotDetectionResult()

        try:
            page_content = await page.content()

            try:
                await page.evaluate("() => document.readyState")
            except Exception:
                pass

            title = await page.title()

            # Check for captcha
            for pattern in self.CAPTCHA_PATTERNS:
                if re.search(pattern, page_content, re.IGNORECASE) or re.search(
                    pattern, title, re.IGNORECASE
                ):
                    result.is_captcha = True
                    result.is_bot_detected = True
                    result.confidence = max(result.confidence, 0.8)
                    result.detector = "captcha_pattern"
                    result.details["pattern"] = pattern
                    break

            # Check for blocks
            for pattern in self.BLOCK_PATTERNS:
                if re.search(pattern, page_content, re.IGNORECASE) or re.search(
                    pattern, title, re.IGNORECASE
                ):
                    if "rate limit" in pattern.lower() or "too many" in pattern.lower():
                        result.is_rate_limited = True
                    else:
                        result.is_blocked = True
                    result.is_bot_detected = True
                    result.confidence = max(result.confidence, 0.7)
                    result.detector = "block_pattern"
                    result.details["pattern"] = pattern
                    break

            # Check for Cloudflare
            for pattern in self.CLOUDFLARE_PATTERNS:
                if re.search(pattern, page_content, re.IGNORECASE):
                    result.is_cloudflare = True
                    result.is_bot_detected = True
                    result.confidence = max(result.confidence, 0.9)
                    result.detector = "cloudflare"
                    break

            # Check for challenge iframe
            challenge_iframes = await page.query_selector_all(
                "iframe[src*='challenge'], iframe[src*='captcha'], iframe[src*='recaptcha']"
            )
            if challenge_iframes:
                result.is_captcha = True
                result.is_bot_detected = True
                result.confidence = max(result.confidence, 0.95)
                result.detector = "challenge_iframe"

        except Exception as e:
            logger.warning(f"Anti-bot check failed: {e}")

        return result

    @staticmethod
    def generate_evasion_script() -> str:
        return """
        // Override navigator properties to avoid detection
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        // Override chrome runtime
        window.chrome = { runtime: {} };
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """

    @staticmethod
    def get_random_delay(min_ms: int = 500, max_ms: int = 3000) -> float:
        return random.uniform(min_ms, max_ms) / 1000
