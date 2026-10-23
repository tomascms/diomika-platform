# API (FastAPI)

Python 3.12, FastAPI, Supabase (PostgREST + Storage), Redis. Corre em Docker com 1 worker uvicorn
numa VM e2-micro, atrás de Cloudflare Tunnel.

## Rotas (`routes/`)
| Módulo | Público | Função |
|---|---|---|
| `categories.py`, `catalog_generic.py` | sim | Catálogo da loja (categorias, listas, detalhe por slug, pesquisa, versão) |
| `contact.py`, `orcamentos.py` | sim (POST) | Formulário de contacto e pedido de orçamento (Turnstile, idempotência) |
| `admin_auth.py` | backoffice | Login, MFA, sessões |
| `admin_crud*.py`, `admin_form.py`, `admin.py` | backoffice | CRUD do catálogo orientado por esquema, upload de imagens, import/export CSV |
| `encomendas.py`, `privacy.py`, `ops_analytics.py`, `system.py`, `desktop_updates.py` | backoffice/ops | Encomendas internas, apagar dados (RGPD), métricas de negócio, feed de actualizações |

## Núcleo (`core/`)
- **Pedido HTTP:** `middleware.py` (request ID, cabeçalhos de segurança, latência, métricas),
  `rate_limit.py`/`rate_limiting.py` (Redis), `bot_defense.py`, `path_guard.py`, limite de tamanho do corpo.
- **Autenticação:** `session_tokens.py` (tokens HMAC, uma sessão por utilizador, expiração absoluta
  e por inactividade, revogação em Redis), `auth.py` (papéis admin/catalog/pedidos/mensagens/ops).
- **Catálogo:** `catalog_service.py`, `catalog_storefront.py`, `catalog_search.py` + `models/`
  (esquema unificado: uma família nova é uma entrada em `CATEGORY_ATTRIBUTE_SCHEMAS`).
- **Cache:** `cache.py` (Redis com fallback em memória, invalidação cirúrgica, versão do catálogo
  para o edge), `cache_warmup.py` (pré-aquecimento dos detalhes).
- **Fiabilidade:** `saga/` (envio de formulários: BD → email → *outbox* se falhar), `outbox.py`,
  `idempotency.py`, `resilience.py`, `background_workers.py` (email IMAP, outbox, manutenção).
- **Observabilidade:** `structured_logging.py` (JSON + Axiom em thread própria), `log_safe.py`
  (redacção de segredos e emails), `metrics.py` (`/metrics`), `sentry_init.py`, `health.py`.
- **Segurança de saída:** `ssrf_guard.py`; `audit.py` (registo de acções de admin na BD).

## Testes
```bash
python -m pytest tests -q          # 252 testes; tests/conftest.py isola BD, Redis, email, Sentry
python -m pytest tests -q --cov=.  # o CI exige o mínimo definido em .github/workflows/ci.yml
```
Cada defeito corrigido tem teste de regressão (ex.: `test_event_loop_not_blocked.py`,
`test_cache_warmup.py`, `test_thumbnails.py`).
