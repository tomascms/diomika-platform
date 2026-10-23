"""Testes para rotação de tokens automática."""
import time

import pytest

from core.token_rotation import (
    should_rotate_token,
    is_token_within_grace_period,
    track_rotation,
    TokenRotationStrategy,
)


class TestTokenRotationLogic:
    """Testes da lógica de rotação de tokens."""

    def test_should_rotate_token_old_timestamp(self):
        """Token com timestamp antigo (>5 min) deve ser rotacionado."""
        old_timestamp = int(time.time()) - 600  # 10 minutos atrás
        assert should_rotate_token(old_timestamp) is True

    def test_should_rotate_token_recent_timestamp(self):
        """Token com timestamp recente (<5 min) não deve ser rotacionado."""
        recent_timestamp = int(time.time()) - 60  # 1 minuto atrás
        assert should_rotate_token(recent_timestamp) is False

    def test_should_rotate_token_zero_timestamp(self):
        """Timestamp zero é considerado antigo e deve rotar."""
        assert should_rotate_token(0) is True

    def test_should_rotate_token_negative_timestamp(self):
        """Timestamp negativo deve rotar."""
        assert should_rotate_token(-1) is True

    def test_should_rotate_token_boundary(self):
        """Token exatamente no intervalo deve rotar."""
        boundary_timestamp = int(time.time()) - 300  # Exatamente 5 min
        assert should_rotate_token(boundary_timestamp) is True


class TestGracePeriod:
    """Testes do período de graça para tokens revogados."""

    def test_token_in_grace_period(self):
        """Token revogado recentemente está em período de graça."""
        revoked_ts = int(time.time()) - 30  # 30 segundos atrás
        assert is_token_within_grace_period(revoked_ts) is True

    def test_token_outside_grace_period(self):
        """Token revogado há muito tempo está fora de período de graça."""
        revoked_ts = int(time.time()) - 300  # 5 minutos atrás
        assert is_token_within_grace_period(revoked_ts) is False

    def test_token_just_expired_grace_period(self):
        """Token que expirou período de graça (120s)."""
        revoked_ts = int(time.time()) - 121  # 121 segundos atrás
        assert is_token_within_grace_period(revoked_ts) is False

    def test_token_just_revoked(self):
        """Token revogado agora está em período de graça."""
        revoked_ts = int(time.time())
        assert is_token_within_grace_period(revoked_ts) is True


class TestTrackRotation:
    """Testes de tracking de rotação."""

    def test_track_rotation_creates_metadata(self):
        """track_rotation deve criar dict com metadata."""
        username = "test_user"
        jti = "abc123"

        meta = track_rotation(username, jti)

        assert meta["username"] == username
        assert meta["jti"] == jti
        assert "rotated_at" in meta
        assert meta["interval_seconds"] == 300  # 5 minutos

    def test_track_rotation_timestamp_recent(self):
        """Timestamp de rotação deve ser recente."""
        meta = track_rotation("user", "jti")

        now = int(time.time())
        rotated = meta["rotated_at"]

        assert abs(now - rotated) < 2  # Diferença < 2 segundos


class TestRotationStrategies:
    """Testes de diferentes estratégias de rotação."""

    def test_policy_aggressive(self):
        """Política agressiva: rotar a cada 60s."""
        interval = TokenRotationStrategy.get_rotation_interval(
            TokenRotationStrategy.POLICY_AGGRESSIVE
        )
        assert interval == 60

    def test_policy_normal(self):
        """Política normal: rotar a cada 300s (5 min)."""
        interval = TokenRotationStrategy.get_rotation_interval(
            TokenRotationStrategy.POLICY_NORMAL
        )
        assert interval == 300

    def test_policy_conservative(self):
        """Política conservadora: rotar a cada 3600s (60 min)."""
        interval = TokenRotationStrategy.get_rotation_interval(
            TokenRotationStrategy.POLICY_CONSERVATIVE
        )
        assert interval == 3600

    def test_invalid_policy_defaults_to_normal(self):
        """Política inválida retorna padrão."""
        interval = TokenRotationStrategy.get_rotation_interval("invalid_policy")
        assert interval == 300  # Normal = padrão

    def test_policy_for_production(self):
        """Produção usa política normal (5 min)."""
        policy = TokenRotationStrategy.get_policy_for_environment(is_production=True)
        assert policy == TokenRotationStrategy.POLICY_NORMAL

    def test_policy_for_development(self):
        """Desenvolvimento usa política conservadora (60 min)."""
        policy = TokenRotationStrategy.get_policy_for_environment(is_production=False)
        assert policy == TokenRotationStrategy.POLICY_CONSERVATIVE
