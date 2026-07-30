import pytest
from dataforge.backend.app.scraping.anti_bot import AntiBotDetector


class TestAntiBotDetector:
    def test_random_user_agent_returns_string(self):
        ua = AntiBotDetector.random_user_agent()
        assert isinstance(ua, str)
        assert len(ua) > 50

    def test_random_viewport_returns_dict(self):
        vp = AntiBotDetector.random_viewport()
        assert "width" in vp
        assert "height" in vp
        assert vp["width"] >= 1280

    def test_random_locale_returns_string(self):
        locale = AntiBotDetector.random_locale()
        assert isinstance(locale, str)
        assert "-" in locale

    def test_random_timezone_returns_string(self):
        tz = AntiBotDetector.random_timezone()
        assert isinstance(tz, str)
        assert "/" in tz

    def test_evasion_script_contains_override(self):
        script = AntiBotDetector.generate_evasion_script()
        assert "webdriver" in script
        assert "navigator" in script

    def test_random_delay_within_range(self):
        delay = AntiBotDetector.get_random_delay(100, 500)
        assert 0.1 <= delay <= 0.5


class TestAntiBotDetectionPatterns:
    @pytest.mark.asyncio
    async def test_captcha_patterns_are_defined(self):
        detector = AntiBotDetector()
        assert len(detector.CAPTCHA_PATTERNS) > 0

    def test_block_patterns_are_defined(self):
        detector = AntiBotDetector()
        assert len(detector.BLOCK_PATTERNS) > 0

    def test_cloudflare_patterns_are_defined(self):
        detector = AntiBotDetector()
        assert len(detector.CLOUDFLARE_PATTERNS) > 0
