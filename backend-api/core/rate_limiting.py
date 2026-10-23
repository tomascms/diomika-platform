"""Rate limiting strategy — per User-Agent, IP, and endpoint basis.

Protects API against:
- Bot scraping (aggressive crawlers)
- Brute force attacks (login attempts)
- Resource exhaustion (expensive operations)
- API abuse (high-volume requests)

Strategies:
1. AGGRESSIVE_BOT: 10 req/min per IP (blocked immediately after threshold)
2. NORMAL_BOT: 100 req/min per IP (allowed, but rate-limited)
3. HUMAN: 1000 req/min per IP (generous limit, practically unlimited for normal use)
4. TRUSTED: Unlimited (internal services, monitoring tools)
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("diomika-api")



def _utcnow() -> datetime:
    """UTC naive (como antes do utcnow ser depreciado)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class RateLimitTier(str, Enum):
    """Rate limiting tiers based on User-Agent classification."""
    AGGRESSIVE_BOT = "aggressive_bot"     # 10 req/min
    NORMAL_BOT = "normal_bot"              # 100 req/min
    HUMAN = "human"                        # 1000 req/min
    TRUSTED = "trusted"                    # Unlimited


@dataclass
class RateLimitConfig:
    """Rate limit configuration per tier."""
    tier: RateLimitTier
    requests_per_minute: int
    burst_size: int = None  # Allow temporary bursts above rate

    def __post_init__(self):
        if self.burst_size is None:
            self.burst_size = max(int(self.requests_per_minute / 6), 1)

    @property
    def requests_per_second(self) -> float:
        """Convert minute-based limit to per-second."""
        return self.requests_per_minute / 60.0


# Default configs per tier
RATE_LIMIT_CONFIGS = {
    RateLimitTier.AGGRESSIVE_BOT: RateLimitConfig(
        tier=RateLimitTier.AGGRESSIVE_BOT,
        requests_per_minute=10,
        burst_size=3,
    ),
    RateLimitTier.NORMAL_BOT: RateLimitConfig(
        tier=RateLimitTier.NORMAL_BOT,
        requests_per_minute=100,
        burst_size=20,
    ),
    RateLimitTier.HUMAN: RateLimitConfig(
        tier=RateLimitTier.HUMAN,
        requests_per_minute=1000,
        burst_size=100,
    ),
    RateLimitTier.TRUSTED: RateLimitConfig(
        tier=RateLimitTier.TRUSTED,
        requests_per_minute=999999,  # Effectively unlimited
        burst_size=999999,
    ),
}


@dataclass
class ClientQuota:
    """Track quota consumption for a client (IP/User-Agent)."""
    client_id: str
    tier: RateLimitTier
    requests_in_window: int = 0
    first_request_at: datetime = field(default_factory=_utcnow)
    last_request_at: datetime = field(default_factory=_utcnow)
    blocked_until: Optional[datetime] = None

    @property
    def is_blocked(self) -> bool:
        """Check if client is currently blocked."""
        if self.blocked_until is None:
            return False
        return _utcnow() < self.blocked_until

    def reset_window(self):
        """Reset request counter for new minute window."""
        self.requests_in_window = 0
        self.first_request_at = _utcnow()

    def block_for_seconds(self, seconds: int = 60):
        """Block client for specified seconds."""
        self.blocked_until = _utcnow() + timedelta(seconds=seconds)


class RateLimitChecker:
    """Check if a request should be rate limited."""

    def __init__(self):
        self.quotas: dict[str, ClientQuota] = {}
        self.window_start = time.time()

    @staticmethod
    def _make_client_id(ip: str, user_agent: str) -> str:
        """Create unique client identifier from IP and User-Agent."""
        data = f"{ip}:{user_agent}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def check_limit(
        self,
        client_id: str,
        tier: RateLimitTier,
        endpoint: str = "",
    ) -> tuple[bool, dict]:
        """
        Check if request should be allowed.

        Returns:
        - (allowed: bool, metadata: dict with limit info)
        """
        config = RATE_LIMIT_CONFIGS.get(tier)
        if config.tier == RateLimitTier.TRUSTED:
            return True, {"allowed": True, "reason": "trusted_tier"}

        quota = self.quotas.get(client_id)
        if quota is None:
            quota = ClientQuota(client_id=client_id, tier=tier)
            self.quotas[client_id] = quota

        # Check if blocked
        if quota.is_blocked:
            return False, {
                "allowed": False,
                "reason": "client_blocked",
                "blocked_until": quota.blocked_until.isoformat(),
                "tier": tier.value,
            }

        # Check if window expired
        window_age = (_utcnow() - quota.first_request_at).total_seconds()
        if window_age >= 60:
            quota.reset_window()

        # Increment request count
        quota.requests_in_window += 1
        quota.last_request_at = _utcnow()

        # Check if exceeds limit
        if quota.requests_in_window > config.requests_per_minute:
            quota.block_for_seconds(60)
            logger.warning(
                f"Rate limit exceeded: {client_id} (tier={tier.value}, endpoint={endpoint}), "
                f"blocking for 60s"
            )
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "limit": config.requests_per_minute,
                "requests_in_window": quota.requests_in_window,
                "tier": tier.value,
                "blocked_for_seconds": 60,
            }

        # Check burst limit
        if quota.requests_in_window > config.burst_size:
            logger.debug(
                f"Burst limit warning: {client_id} (tier={tier.value}), "
                f"at {quota.requests_in_window}/{config.burst_size}"
            )

        # Allowed
        window_remaining = max(0, 60 - window_age)
        requests_remaining = max(0, config.requests_per_minute - quota.requests_in_window)

        return True, {
            "allowed": True,
            "tier": tier.value,
            "requests_in_window": quota.requests_in_window,
            "limit": config.requests_per_minute,
            "requests_remaining": requests_remaining,
            "window_remaining_seconds": int(window_remaining),
        }

    def cleanup_stale_quotas(self, older_than_minutes: int = 60):
        """Remove inactive quotas to free memory."""
        cutoff = _utcnow() - timedelta(minutes=older_than_minutes)
        stale = [
            cid for cid, quota in self.quotas.items()
            if quota.last_request_at < cutoff
        ]
        for cid in stale:
            del self.quotas[cid]
        if stale:
            logger.debug(f"Cleaned up {len(stale)} stale rate limit quotas")

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        active = sum(1 for q in self.quotas.values() if not q.is_blocked)
        blocked = len(self.quotas) - active
        return {
            "total_clients": len(self.quotas),
            "active_clients": active,
            "blocked_clients": blocked,
            "quotas_by_tier": {
                tier.value: sum(1 for q in self.quotas.values() if q.tier == tier)
                for tier in RateLimitTier
            },
        }


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limiting per User-Agent.

    O limite é verificado ANTES de chamar a rota (antes corria a rota e só
    depois decidia), e o IP vem de core.rate_limit.get_client_ip, que só
    confia em X-Forwarded-For atrás de um proxy de confiança — ler o header
    directamente deixava qualquer cliente escolher o próprio IP.
    """

    def __init__(self, app):
        super().__init__(app)
        self.checker = RateLimitChecker()
        self.cleanup_counter = 0
        self.cleanup_interval = 1000  # Cleanup every N requests

    async def dispatch(self, request: Request, call_next):
        from core.bot_defense import is_bot_user_agent
        from core.rate_limit import get_client_ip

        ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        endpoint = f"{request.method} {request.url.path}"

        if is_bot_user_agent(user_agent):
            tier = RateLimitTier.AGGRESSIVE_BOT
        elif user_agent.startswith("DiomikaMonitor/") or user_agent.startswith("Uptime"):
            tier = RateLimitTier.TRUSTED
        else:
            tier = RateLimitTier.HUMAN

        client_id = self.checker._make_client_id(ip, user_agent)
        allowed, metadata = self.checker.check_limit(client_id, tier, endpoint)

        self.cleanup_counter += 1
        if self.cleanup_counter >= self.cleanup_interval:
            self.checker.cleanup_stale_quotas()
            self.cleanup_counter = 0

        if not allowed:
            retry_after = int(metadata.get("blocked_for_seconds", 60))
            return JSONResponse(
                status_code=429,
                content={"detail": "Demasiados pedidos. Tente novamente dentro de instantes."},
                headers={"Retry-After": str(retry_after), "X-RateLimit-Tier": tier.value},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Tier"] = tier.value
        response.headers["X-RateLimit-Remaining"] = str(metadata.get("requests_remaining", -1))
        response.headers["X-RateLimit-Reset"] = str(int(metadata.get("window_remaining_seconds", 0)))
        return response


# Global instance
_checker: Optional[RateLimitChecker] = None


def get_rate_limit_checker() -> RateLimitChecker:
    """Get or create global rate limit checker."""
    global _checker
    if _checker is None:
        _checker = RateLimitChecker()
    return _checker
