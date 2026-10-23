"""Configuração centralizada e validação de ambiente."""
from __future__ import annotations

import os
import sys
from functools import lru_cache


@lru_cache
def get_settings():
    return Settings()


class Settings:
    def __init__(self) -> None:
        self.env = (os.getenv("DIOMIKA_ENV") or "development").strip().lower()
        self.api_secret_key = os.getenv("API_SECRET_KEY")
        self.api_base_url = (os.getenv("API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.cors_origins = [
            o.strip()
            for o in (
                os.getenv("CORS_ORIGINS")
                or "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
            ).split(",")
            if o.strip()
        ]
        self.is_production = self.env == "production"
        self.is_beta = (os.getenv("DIOMIKA_BETA") or "").strip().lower() in ("1", "true", "yes")

    @property
    def docs_enabled(self) -> bool:
        """Swagger/OpenAPI: nunca em produção; nunca com API_BASE_URL https (túnel público)."""
        if self.is_production:
            return False
        if self.api_base_url.startswith("https://"):
            return False
        flag = (os.getenv("DIOMIKA_ENABLE_DOCS") or "").strip().lower()
        if flag in ("0", "false", "no"):
            return False
        if flag in ("1", "true", "yes"):
            return True
        # development local (http) — docs ligados por defeito
        return True

    TURNSTILE_TEST_KEYS = frozenset({
        "1x0000000000000000000000000000000aa",
        "1x00000000000000000000aa",
        "2x0000000000000000000000000000000aa",
        "3x0000000000000000000000000000000ff",
    })

    @property
    def api_key_required(self) -> bool:
        return self.is_production or self.is_beta or bool(self.api_secret_key)

    def _turnstile_is_test_key(self) -> bool:
        secret = (os.getenv("TURNSTILE_SECRET_KEY") or "").strip().lower()
        site = (os.getenv("VITE_TURNSTILE_SITE_KEY") or "").strip().lower()
        return secret in self.TURNSTILE_TEST_KEYS or site in self.TURNSTILE_TEST_KEYS

    def validate_startup(self) -> None:
        if not self.is_production:
            return
        missing = []
        if not self.api_secret_key:
            missing.append("API_SECRET_KEY")
        if not os.getenv("SUPABASE_URL"):
            missing.append("SUPABASE_URL")
        if not os.getenv("SUPABASE_KEY"):
            missing.append("SUPABASE_KEY")
        if not (os.getenv("TURNSTILE_SECRET_KEY") or "").strip():
            missing.append("TURNSTILE_SECRET_KEY")
        if not (os.getenv("ALLOWED_HOSTS") or "").strip():
            missing.append("ALLOWED_HOSTS (domínio da API)")
        if not self.is_beta and (
            not self.cors_origins
            or any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origins)
        ):
            missing.append("CORS_ORIGINS (domínios de produção)")
        if missing:
            print("ERRO: DIOMIKA_ENV=production exige:", ", ".join(missing), file=sys.stderr)
            sys.exit(1)
        if self._turnstile_is_test_key() and not self.is_beta:
            print(
                "ERRO: Turnstile usa chaves de teste — producao exige chaves reais.\n"
                "  Define TURNSTILE_SECRET_KEY real (Cloudflare Turnstile).",
                file=sys.stderr,
            )
            sys.exit(1)
        if not self.is_beta and not self.api_base_url.startswith("https://"):
            print("ERRO: API_BASE_URL deve ser https:// em producao.", file=sys.stderr)
            sys.exit(1)
        ssl_insecure = (os.getenv("DIOMIKA_SSL_INSECURE") or "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if ssl_insecure and not self.is_beta:
            print(
                "ERRO: DIOMIKA_SSL_INSECURE=1 proibido em producao final.\n"
                "  Remova a flag — API usa certifi.\n"
                "  Scripts deploy usam DEPLOY_TLS_INSECURE=1 (so CLI, nao a API).",
                file=sys.stderr,
            )
            sys.exit(1)
        if ssl_insecure and self.is_beta:
            print(
                "AVISO: DIOMIKA_SSL_INSECURE=1 em beta — TLS desactivado na API.\n"
                "  Remova na VM / domain day. Scripts CLI devem usar DEPLOY_TLS_INSECURE.",
                file=sys.stderr,
            )
        if self.api_secret_key and len(self.api_secret_key) < 32:
            print("ERRO: API_SECRET_KEY deve ter pelo menos 32 caracteres.", file=sys.stderr)
            sys.exit(1)
        if not self.is_beta and (os.getenv("ADMIN_ALLOW_REMOTE") or "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            print(
                "ERRO: ADMIN_ALLOW_REMOTE foi removido — remova a variável do .env.\n"
                "  Admin/system é sempre localhost-only em produção final.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not self.is_beta and (os.getenv("TRUST_PROXY") or "").strip().lower() in ("1", "true", "yes"):
            peers = (os.getenv("TRUSTED_PROXY_IPS") or "").strip()
            if not peers:
                print(
                    "ERRO: TRUST_PROXY=1 exige TRUSTED_PROXY_IPS "
                    "(ex: 127.0.0.1,::1 ou CIDR do proxy).",
                    file=sys.stderr,
                )
                sys.exit(1)
        if not self.is_beta and not (os.getenv("REDIS_URL") or "").strip():
            print(
                "ERRO: REDIS_URL obrigatorio em producao final "
                "(rate limit + sessões partilhadas entre workers).",
                file=sys.stderr,
            )
            sys.exit(1)
        # Storage público é permitido: as fotos do catálogo são conteúdo público e
        # servidas sem assinatura ficam em cache na CDN e no browser.
        if not self.is_beta and (os.getenv("SECURITY_LOCKDOWN") or "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            print(
                "AVISO: SECURITY_LOCKDOWN=1 — API em modo incidente "
                "(só /health;/health/ready).",
                file=sys.stderr,
            )
        # Produção final: webhook de alertas recomendado (aviso) / obrigatório se ALERT_WEBHOOK_REQUIRED=1
        if not self.is_beta:
            from core.alerts import webhook_configured

            if not webhook_configured():
                req = (os.getenv("ALERT_WEBHOOK_REQUIRED") or "1").strip().lower() in (
                    "1",
                    "true",
                    "yes",
                )
                msg = (
                    "ALERT_WEBHOOK_URL em falta — alertas só em deploy/alerts.log.\n"
                    "  Defina ALERT_WEBHOOK_URL (ex: https://hooks.slack.com/...) "
                    "ou ALERT_WEBHOOK_REQUIRED=0 para aviso apenas."
                )
                if req:
                    print("ERRO: " + msg, file=sys.stderr)
                    sys.exit(1)
                print("AVISO: " + msg, file=sys.stderr)
