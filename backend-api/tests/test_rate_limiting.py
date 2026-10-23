"""Tests for rate limiting strategy."""
import pytest
from datetime import datetime, timedelta
from core.rate_limiting import (
    RateLimitChecker,
    RateLimitTier,
    RATE_LIMIT_CONFIGS,
    ClientQuota,
)


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_config_per_second_conversion(self):
        """Convert minute-based limit to per-second."""
        config = RATE_LIMIT_CONFIGS[RateLimitTier.HUMAN]
        assert config.requests_per_minute == 1000
        assert config.requests_per_second == 1000 / 60

    def test_config_burst_size(self):
        """Verify burst size is calculated correctly."""
        # Burst explícito na config para bots agressivos.
        config = RATE_LIMIT_CONFIGS[RateLimitTier.AGGRESSIVE_BOT]
        assert config.burst_size == 3

        # Sem burst explícito, deriva de requests_per_minute / 6.
        from core.rate_limiting import RateLimitConfig

        assert RateLimitConfig(tier=RateLimitTier.HUMAN, requests_per_minute=60).burst_size == 10

        config = RATE_LIMIT_CONFIGS[RateLimitTier.HUMAN]
        assert config.burst_size >= 1

    def test_trusted_tier_unlimited(self):
        """Trusted tier should have high limit."""
        config = RATE_LIMIT_CONFIGS[RateLimitTier.TRUSTED]
        assert config.requests_per_minute == 999999


class TestClientQuota:
    """Tests for client quota tracking."""

    def test_quota_not_blocked_initially(self):
        """New quota should not be blocked."""
        quota = ClientQuota(client_id="test", tier=RateLimitTier.HUMAN)
        assert quota.is_blocked is False
        assert quota.blocked_until is None

    def test_quota_block_and_unblock(self):
        """Block quota and verify it's blocked."""
        quota = ClientQuota(client_id="test", tier=RateLimitTier.HUMAN)
        quota.block_for_seconds(1)
        assert quota.is_blocked is True

        # After time passes, should be unblocked
        quota.blocked_until = datetime.utcnow() - timedelta(seconds=1)
        assert quota.is_blocked is False

    def test_quota_reset_window(self):
        """Reset quota window."""
        quota = ClientQuota(client_id="test", tier=RateLimitTier.HUMAN)
        quota.requests_in_window = 50
        quota.reset_window()

        assert quota.requests_in_window == 0
        assert quota.first_request_at >= datetime.utcnow() - timedelta(seconds=1)


class TestRateLimitChecker:
    """Tests for rate limit checking logic."""

    def test_make_client_id(self):
        """Generate consistent client ID."""
        id1 = RateLimitChecker._make_client_id("192.168.1.1", "Chrome")
        id2 = RateLimitChecker._make_client_id("192.168.1.1", "Chrome")
        assert id1 == id2
        assert len(id1) == 16

    def test_trusted_tier_always_allowed(self):
        """Trusted tier should always be allowed."""
        checker = RateLimitChecker()
        for _ in range(1000):
            allowed, _ = checker.check_limit("trusted_id", RateLimitTier.TRUSTED)
            assert allowed is True

    def test_aggressive_bot_limited_to_10_per_minute(self):
        """Aggressive bot limited to 10 req/min."""
        checker = RateLimitChecker()
        client_id = "aggressive_bot_id"

        # First 10 should be allowed
        for i in range(10):
            allowed, meta = checker.check_limit(client_id, RateLimitTier.AGGRESSIVE_BOT)
            assert allowed is True, f"Request {i+1} should be allowed"

        # 11th should be blocked
        allowed, meta = checker.check_limit(client_id, RateLimitTier.AGGRESSIVE_BOT)
        assert allowed is False
        assert "rate_limit_exceeded" in meta.get("reason", "")

    def test_human_tier_high_limit(self):
        """Human tier allows 1000 req/min."""
        checker = RateLimitChecker()
        client_id = "human_id"

        # 500 should be fine
        for _ in range(500):
            allowed, _ = checker.check_limit(client_id, RateLimitTier.HUMAN)
            assert allowed is True

        # Eventually should exceed limit at 1000+
        for _ in range(500):
            allowed, _ = checker.check_limit(client_id, RateLimitTier.HUMAN)

        # 1001st should be blocked
        allowed, meta = checker.check_limit(client_id, RateLimitTier.HUMAN)
        assert allowed is False

    def test_rate_limit_metadata(self):
        """Verify metadata returned with rate limit check."""
        checker = RateLimitChecker()
        allowed, meta = checker.check_limit("test_id", RateLimitTier.HUMAN)

        assert meta["allowed"] is True
        assert "tier" in meta
        assert "requests_in_window" in meta
        assert "limit" in meta
        assert "requests_remaining" in meta
        assert "window_remaining_seconds" in meta

    def test_window_reset_after_60_seconds(self):
        """Window should reset after 60 seconds."""
        checker = RateLimitChecker()
        client_id = "window_test"

        # Make requests to build up quota
        quota = ClientQuota(client_id=client_id, tier=RateLimitTier.HUMAN)
        quota.requests_in_window = 50
        quota.first_request_at = datetime.utcnow() - timedelta(seconds=61)
        checker.quotas[client_id] = quota

        # Check should reset window
        allowed, meta = checker.check_limit(client_id, RateLimitTier.HUMAN)
        assert allowed is True
        # After reset, should have low request count
        assert meta["requests_in_window"] <= 2

    def test_cleanup_stale_quotas(self):
        """Remove old inactive quotas."""
        checker = RateLimitChecker()

        # Add fresh quota
        checker.check_limit("fresh_id", RateLimitTier.HUMAN)

        # Add stale quota
        stale_quota = ClientQuota(client_id="stale_id", tier=RateLimitTier.HUMAN)
        stale_quota.last_request_at = datetime.utcnow() - timedelta(hours=2)
        checker.quotas["stale_id"] = stale_quota

        assert len(checker.quotas) == 2
        checker.cleanup_stale_quotas(older_than_minutes=60)

        assert len(checker.quotas) == 1
        assert "fresh_id" in checker.quotas

    def test_blocked_client_stays_blocked(self):
        """Blocked client should remain blocked."""
        checker = RateLimitChecker()
        client_id = "blocked_id"

        # Get it blocked
        quota = ClientQuota(client_id=client_id, tier=RateLimitTier.AGGRESSIVE_BOT)
        quota.block_for_seconds(60)
        checker.quotas[client_id] = quota

        # Try multiple times while blocked
        for _ in range(5):
            allowed, meta = checker.check_limit(client_id, RateLimitTier.AGGRESSIVE_BOT)
            assert allowed is False
            assert meta.get("reason") == "client_blocked"

    def test_stats(self):
        """Get rate limiter statistics."""
        checker = RateLimitChecker()

        # Add some quotas
        checker.check_limit("id1", RateLimitTier.HUMAN)
        checker.check_limit("id2", RateLimitTier.AGGRESSIVE_BOT)
        quota = ClientQuota(client_id="id3", tier=RateLimitTier.HUMAN)
        quota.block_for_seconds(60)
        checker.quotas["id3"] = quota

        stats = checker.get_stats()
        assert stats["total_clients"] == 3
        assert stats["active_clients"] == 2
        assert stats["blocked_clients"] == 1
        assert "quotas_by_tier" in stats
