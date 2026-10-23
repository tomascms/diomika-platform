"""Testes para defesa contra bots."""
import pytest
from core.bot_defense import is_bot_user_agent, log_bot_attempt


class TestBotDetection:
    """Testes de detecção de bots."""

    def test_blocked_bot_scrapy(self):
        """Scrapy deve ser bloqueado."""
        assert is_bot_user_agent("Mozilla/5.0 (Scrapy/2.0)") is True

    def test_blocked_bot_selenium(self):
        """Selenium deve ser bloqueado."""
        assert is_bot_user_agent("Mozilla/5.0 (Selenium/4.0)") is True

    def test_blocked_bot_playwright(self):
        """Playwright deve ser bloqueado."""
        assert is_bot_user_agent("Mozilla/5.0 (Playwright/1.0)") is True

    def test_blocked_bot_curl(self):
        """curl deve ser bloqueado (genérico)."""
        assert is_bot_user_agent("curl/7.68.0") is True

    def test_allowed_bot_googlebot(self):
        """Googlebot é permitido."""
        assert is_bot_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)") is False

    def test_allowed_bot_bingbot(self):
        """Bingbot é permitido."""
        assert is_bot_user_agent("Mozilla/5.0 (compatible; Bingbot/2.0)") is False

    def test_allowed_bot_yandexbot(self):
        """Yandexbot é permitido."""
        assert is_bot_user_agent("Mozilla/5.0 (compatible; YandexBot/3.0)") is False

    def test_normal_browser_chrome(self):
        """Chrome normal não deve ser bloqueado."""
        assert is_bot_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ) is False

    def test_normal_browser_firefox(self):
        """Firefox normal não deve ser bloqueado."""
        assert is_bot_user_agent(
            "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ) is False

    def test_normal_browser_safari(self):
        """Safari normal não deve ser bloqueado."""
        assert is_bot_user_agent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        ) is False

    def test_empty_user_agent(self):
        """User-Agent vazio não bloqueia."""
        assert is_bot_user_agent("") is False
        assert is_bot_user_agent(None) is False

    def test_case_insensitive(self):
        """Detecção deve ser case-insensitive."""
        assert is_bot_user_agent("SCRAPY/2.0") is True
        assert is_bot_user_agent("Scrapy/2.0") is True
        assert is_bot_user_agent("scrapy/2.0") is True

    def test_blocked_bot_in_string(self):
        """Detecta bot mesmo em strings longas."""
        ua = "Mozilla/5.0 (X11; Linux) AppleWebKit/537.36 scrapy/2.0 Safari/537.36"
        assert is_bot_user_agent(ua) is True

    def test_allowed_facebook_external_hit(self):
        """FacebookExternalHit é permitido (link preview)."""
        assert is_bot_user_agent("facebookexternalhit/1.1") is False

    def test_allowed_twitter_bot(self):
        """TwitterBot é permitido (link preview)."""
        assert is_bot_user_agent("Twitterbot/1.0") is False

    def test_allowed_discord_bot(self):
        """Discord bot é permitido (link preview)."""
        assert is_bot_user_agent("Discordbot/2.0") is False

    def test_blocked_80legs(self):
        """80legs deve ser bloqueado."""
        assert is_bot_user_agent("80legs") is True

    def test_blocked_blackwidow(self):
        """Blackwidow deve ser bloqueado."""
        assert is_bot_user_agent("blackwidow") is True

    def test_blocked_headless(self):
        """Headless deve ser bloqueado (headless chrome/firefox)."""
        assert is_bot_user_agent("HeadlessChrome/91.0") is True
