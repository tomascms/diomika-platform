"""Token rotation automática para sessões admin.

Estratégia: a cada 5 minutos, emitir novo token se sessão ativa.
Cliente deve usar novo token na próxima requisição.
Versão anterior é mantida válida por graça de 2 minutos (clock skew).
"""
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("diomika-api")

# Intervalo de rotação em segundos (padrão: 5 minutos)
TOKEN_ROTATION_INTERVAL = int(os.getenv("TOKEN_ROTATION_INTERVAL_SECONDS", "300"))

# Tempo de graça (segundos) — token antigo ainda é válido durante esta janela
TOKEN_GRACE_PERIOD_SECONDS = int(os.getenv("TOKEN_GRACE_PERIOD_SECONDS", "120"))


def should_rotate_token(last_rotation_ts: int) -> bool:
    """Verifica se token deve ser rotacionado baseado no timestamp."""
    if last_rotation_ts <= 0:
        return True

    now = int(time.time())
    elapsed = now - last_rotation_ts

    return elapsed >= TOKEN_ROTATION_INTERVAL


def is_token_within_grace_period(revoked_ts: int) -> bool:
    """Verifica se token revogado ainda está em período de graça."""
    now = int(time.time())
    elapsed = now - revoked_ts

    return elapsed < TOKEN_GRACE_PERIOD_SECONDS


def track_rotation(username: str, jti: str) -> dict:
    """
    Registra rotação de token para auditoria.

    Returns:
    - Dict com metadata de rotação (timestamp, intervalo, etc)
    """
    return {
        "username": username,
        "jti": jti,
        "rotated_at": int(time.time()),
        "interval_seconds": TOKEN_ROTATION_INTERVAL,
    }


def log_rotation_event(username: str, old_jti: str, new_jti: str) -> None:
    """Log auditoria para rotação de token."""
    logger.info(
        f"Token rotation: user={username}, old_jti={old_jti[:8]}..., new_jti={new_jti[:8]}..."
    )


class TokenRotationStrategy:
    """Estratégia de rotação de tokens com diferentes políticas."""

    POLICY_AGGRESSIVE = "aggressive"  # Rotar a cada request
    POLICY_NORMAL = "normal"          # Rotar a cada 5 min
    POLICY_CONSERVATIVE = "conservative"  # Rotar a cada 60 min

    POLICIES = {
        POLICY_AGGRESSIVE: 60,          # 1 min
        POLICY_NORMAL: 300,             # 5 min
        POLICY_CONSERVATIVE: 3600,      # 60 min
    }

    @classmethod
    def get_rotation_interval(cls, policy: str = POLICY_NORMAL) -> int:
        """Retorna intervalo de rotação em segundos baseado na política."""
        return cls.POLICIES.get(policy, cls.POLICIES[cls.POLICY_NORMAL])

    @classmethod
    def get_policy_for_environment(cls, is_production: bool) -> str:
        """Retorna política recomendada para ambiente."""
        # Produção: rotação mais agressiva (5 min)
        # Beta/Dev: mais conservadora (60 min)
        return cls.POLICY_NORMAL if is_production else cls.POLICY_CONSERVATIVE
