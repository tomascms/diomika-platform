"""
API FastAPI da Diomika (catálogo, orçamentos, contacto, admin local-only).

Arranque local (dev): porta 8001. Docker compose / VM: :8000. Backoffice cliente → https://api.diomika.com.
Produção: GCP e2-micro + Cloudflare Tunnel → api.diomika.com
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core.env_loader import load_project_env

load_project_env()

from core.auth import require_ops
from core.local_only import admin_must_be_local
from core.config import get_settings
from core.health import build_health
from core.public_meta import ROBOTS_TXT, STATUS_PAGE, security_txt_body
from core.middleware import (
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    GlobalRateLimitMiddleware,
    CatalogCacheHeadersMiddleware,
    BodySizeLimitMiddleware,
    LatencyAlertMiddleware,
    BotDefenseMiddleware,
    ALLOWED_CORS_HEADERS,
)
from core.auth_token_middleware import AdminTokenRotationMiddleware
from core.path_guard import PrivilegedPathMiddleware
from core.rate_limiting import RateLimitingMiddleware
from core.version import VERSION
from routes import (
    desktop_updates,
    categories,
    system,
    contact,
    admin,
    orcamentos,
    encomendas,
    catalog_generic,
    admin_crud,
    admin_form,
    admin_auth,
    privacy,
    ops_analytics,
)

from core.log_safe import install_log_redaction
from core.structured_logging import configure_structured_logging
from core.error_tracking import init_error_tracking, capture_exception

# Produção: JSON on por default. Dev: texto, a menos que LOG_FORMAT=json.
if not (os.getenv("LOG_FORMAT") or "").strip():
    if (os.getenv("DIOMIKA_ENV") or "").strip().lower() == "production":
        os.environ["LOG_FORMAT"] = "json"
configure_structured_logging()
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

install_log_redaction()
_error_mode = init_error_tracking()

logger = logging.getLogger("diomika-api")
logger.info("Error tracking mode=%s", _error_mode)

settings = get_settings()
settings.validate_startup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.background_workers import start_background_workers, stop_background_workers

    # O esquema deixou de ser auto-migrado no arranque (ALTER TABLE/CREATE
    # TABLE em produção a cada boot era frágil e arriscado — ver auditoria).
    # Migrações são agora ficheiros SQL versionados em db/migrations/,
    # aplicados manualmente no Supabase SQL Editor (ver o RUNBOOK em sql/),
    # nunca automaticamente aqui.
    from core.cache import invalidate_prefix
    from core.cache_warmup import warm_catalog_cache

    # O Redis persiste (sessões); dados de catálogo de uma versão anterior da API não.
    for prefix in ("catalog:", "categories:", "admin:merged:"):
        await asyncio.to_thread(invalidate_prefix, prefix)
    await asyncio.to_thread(warm_catalog_cache)
    if settings.is_production:
        from core.cache_warmup import warm_model_details_in_background

        warm_model_details_in_background()  # não atrasa o arranque
    start_background_workers()
    yield
    stop_background_workers()


app = FastAPI(
    title="Diomika API",
    version=VERSION,
    description="API Diomika — catálogo schema-driven, sagas, Supabase",
    docs_url="/api/docs" if settings.docs_enabled else None,
    redoc_url="/api/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan,
)

# Ordem: path guard primeiro (outermost = last add) — Starlette inverte
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(AdminTokenRotationMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(BotDefenseMiddleware)
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(LatencyAlertMiddleware)
app.add_middleware(CatalogCacheHeadersMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(PrivilegedPathMiddleware)
if settings.is_production:
    allowed_hosts = [h.strip() for h in (os.getenv("ALLOWED_HOSTS") or "").split(",") if h.strip()]
    # Fail-closed: sem hosts → middleware com lista vazia rejeita tudo (validate_startup já exige)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts or ["invalid.invalid"])
    if settings.is_beta:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https://.*\.(trycloudflare\.com|pages\.dev)$",
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=ALLOWED_CORS_HEADERS,
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=ALLOWED_CORS_HEADERS,
        )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["*"],
        allow_headers=["*"],
    )

if not settings.api_secret_key and not settings.is_production:
    logger.warning("API_SECRET_KEY não definido — endpoints admin abertos apenas em dev local.")

from core.admin_users import ensure_bootstrap

ensure_bootstrap()

app.include_router(admin_auth.router)
app.include_router(privacy.router)
app.include_router(catalog_generic.router)
app.include_router(categories.router)
app.include_router(system.router)
app.include_router(contact.router)
app.include_router(orcamentos.router)
app.include_router(encomendas.router)
app.include_router(admin_crud.router)
app.include_router(admin_form.router)
app.include_router(admin.router)
app.include_router(ops_analytics.router)
app.include_router(desktop_updates.router)


@app.exception_handler(Exception)
async def _unhandled_exception(request, exc):  # type: ignore[no-untyped-def]
    """Em produção não devolve stack traces ao cliente."""
    from fastapi.responses import JSONResponse

    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    try:
        capture_exception(
            exc,
            path=str(request.url.path),
            request_id=getattr(request.state, "request_id", None),
        )
    except Exception:
        pass
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "Erro interno"})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/")
def api_root():
    return {"service": "diomika-api", "health": "/health", "status": STATUS_PAGE}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    return PlainTextResponse(ROBOTS_TXT, media_type="text/plain; charset=utf-8")


@app.get("/.well-known/security.txt", response_class=PlainTextResponse)
def security_txt():
    return PlainTextResponse(security_txt_body(), media_type="text/plain; charset=utf-8")


@app.api_route("/health", methods=["GET", "HEAD"])  # HEAD: UptimeRobot
def health_check():
    return build_health(detailed=False)


@app.api_route("/health/ready", methods=["GET", "HEAD"])  # HEAD: UptimeRobot
def health_ready():
    body = build_health(ready=True)
    if not body.get("database"):
        # 503 para load balancers — não é excepção de aplicação (Sentry filtra /health).
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content=body)
    return body


@app.get(
    "/health/detail",
    dependencies=[Depends(admin_must_be_local), Depends(require_ops)],
)
def health_detail():
    """Detalhe ops — só localhost em produção final (público: /health e /health/ready)."""
    return build_health(detailed=True)


@app.get(
    "/metrics",
    dependencies=[Depends(admin_must_be_local), Depends(require_ops)],
    response_class=PlainTextResponse,
)
def metrics_endpoint():
    """Prometheus (texto). Mesma protecção que /health/detail: localhost + chave ops/admin."""
    from core.metrics import render

    return PlainTextResponse(render(), media_type="text/plain; version=0.0.4")


@app.api_route("/health/live", methods=["GET", "HEAD"])  # HEAD: UptimeRobot
def health_live():
    """Liveness: o processo responde (sem tocar na BD)."""
    return {"status": "alive"}


if __name__ == "__main__":
    import uvicorn

    # Local Windows / Tunnel → 8001. Override: DIOMIKA_API_PORT=8000
    _port = int(os.getenv("DIOMIKA_API_PORT") or "8001")
    uvicorn.run(app, host="127.0.0.1", port=_port)
