# Auditoria de requisitos não funcionais — 2026-10-22

Âmbito: `backend-api/` (FastAPI, 1 worker uvicorn numa e2-micro), `frontend-web/` (Vue + Pages
Functions), `backoffice-desktop/` (Electron). Correcções nos commits `74310a5`, `20bcb35`, `3effcff`;
testes: 249 passaram.

**Não aplicável:** não há pagamentos, cupões, frete nem checkout com dinheiro (a loja só recebe
pedidos de orçamento), por isso PCI-DSS e circuit breakers de gateway não se aplicam.

## Corrigido

### 1. I/O síncrono dentro de `async def` — bloqueava a API inteira (crítico)
- **[ARQUIVO/LINHA]** `core/saga/contact_saga.py:27`, `core/saga/orcamento_saga.py:50`,
  `routes/contact.py:214` (`reply_to_message`), `routes/admin.py:112` (`import_csv`).
- **[DIAGNÓSTICO]** O cliente Supabase é síncrono. Chamado dentro de `async def`, corre no event loop.
  Com 1 worker, cada submissão de contacto (~7 idas à BD EUA→Irlanda, ~1 s) parava *todos* os
  pedidos, incluindo `/health`. Um CSV de 500 linhas congelava a API mais de 1 min. Uma rajada de
  formulários bastava para o healthcheck falhar e o Docker reiniciar o contentor.
- **[RESOLUÇÃO]**
  ```diff
  -    db.table("contact_messages").insert(payload).execute()
  +    await asyncio.to_thread(lambda: db.table("contact_messages").insert(payload).execute())
  -    saga_log(saga_id, ...)
  +    await saga_log_async(saga_id, ...)   # core/saga/logging.py: asyncio.to_thread(saga_log, ...)
  ```
  Teste: `tests/test_event_loop_not_blocked.py` (o loop continua a correr durante a saga).

### 2. Sessões do backoffice com 30 dias e sem expiração por inactividade (alto)
- **[ARQUIVO/LINHA]** `core/session_tokens.py:20`
- **[DIAGNÓSTICO]** Token válido 30 dias e, com «manter sessão», guardado em `localStorage` do
  Electron. Um token roubado (PC partilhado, XSS no backoffice) dava acesso de admin durante um mês.
- **[RESOLUÇÃO]**
  ```diff
  -SESSION_TTL_SECONDS = int(os.getenv("ADMIN_SESSION_TTL_MINUTES") or "43200") * 60
  -SESSION_IDLE_SECONDS = int(_idle_raw) * 60 if _idle_raw else 0
  +SESSION_TTL_SECONDS = int(os.getenv("ADMIN_SESSION_TTL_MINUTES") or "10080") * 60
  +SESSION_IDLE_SECONDS = int((os.getenv("ADMIN_SESSION_IDLE_MINUTES") or "720").strip()) * 60
  ```

### 3. Nomes de filtro da query string no caminho PostgREST (médio)
- **[ARQUIVO/LINHA]** `core/catalog_storefront.py:217` (`query.eq(f"attributes->>{field}", value)`)
- **[DIAGNÓSTICO]** `filter_<nome>` vem do visitante e entra no nome da coluna. Os valores são
  parametrizados, mas o nome permitia sintaxe PostgREST (`->`, vírgulas, parênteses).
- **[RESOLUÇÃO]**
  ```diff
  +_SAFE_ATTR = re.compile(r"[a-z][a-z0-9_]{0,39}")
  +        if not _SAFE_ATTR.fullmatch(field):
  +            continue
  ```

### 4. Paginação sem tecto na rota pública (médio)
- **[ARQUIVO/LINHA]** `routes/catalog_generic.py:123` (`list_storefront_catalog`)
- **[DIAGNÓSTICO]** `?limit=`/`?offset=` arbitrários geravam uma entrada de cache por valor
  (o serviço interno já limitava a query a `MAX_PAGE_LIMIT`).
- **[RESOLUÇÃO]**
  ```diff
  +    limit = min(max(limit, 1), DEFAULT_PAGE_LIMIT)
  +    offset = max(offset, 0)
  ```

### 5. Erros engolidos sem rasto (médio)
- **[ARQUIVO/LINHA]** `workers/email_worker.py:138`, `core/cache.py:95`, `core/saga/logging.py:24`,
  `workers/email_worker.py` (`logger.error` sem stack trace).
- **[DIAGNÓSTICO]** Resposta de cliente por ligar à conversa, cache por invalidar (loja com dados
  antigos) ou estado de saga perdido — tudo sem log visível (`pass` / `debug`).
- **[RESOLUÇÃO]** `logger.warning(..., exc_info=True)` nos três pontos; `logger.exception` no worker.

### 6. Resposta a cliente: email enviado mas pedido devolvia 500 (médio, atomicidade)
- **[ARQUIVO/LINHA]** `routes/contact.py:249-258`
- **[DIAGNÓSTICO]** Se o registo na BD falhasse depois do envio, o backoffice recebia 500 e o
  utilizador reenviava — o cliente recebia o email duas vezes.
- **[RESOLUÇÃO]** Registo em `asyncio.to_thread`; falha depois do envio fica em `logger.exception`
  e o pedido devolve sucesso.

### 7. Logs perdidos no encerramento (baixo)
- **[ARQUIVO/LINHA]** `core/structured_logging.py:123`
- **[DIAGNÓSTICO]** A fila para o Axiom não era esvaziada no SIGTERM (cada deploy perdia os últimos logs).
- **[RESOLUÇÃO]** `atexit.register(...)` que pára o `QueueListener` (esvazia a fila).

## Verificado e em ordem
- **Injecção SQL:** todo o acesso à BD é pelo construtor PostgREST (parametrizado); SQL cru só em
  `core/health.py`/`core/db_verify.py`, sem input do utilizador.
- **XSS:** sem `v-html` na loja nem no backoffice; CSP sem `unsafe-inline`/`unsafe-eval`
  (`deploy/verify_csp.py`).
- **Cabeçalhos:** HSTS (preload), CSP, X-Frame-Options DENY, nosniff, COOP/CORP, Permissions-Policy.
- **Rate limiting:** no código (`core/rate_limit.py`, Redis) para formulários e login; Turnstile;
  regra Cloudflare `forms-burst-limit` no edge.
- **Cookies:** não há cookies de sessão (o backoffice usa bearer token); a loja não tem login.
- **Dados no browser da loja:** carrinho e rascunho do formulário em `localStorage`, por decisão
  do utilizador e indicado no formulário; sem tokens.
- **Cache:** catálogo em Redis (`get_or_set`) e no edge (versão + `stale-if-error`).
- **Índices:** advisor de performance da Supabase sem índices em falta (os «não usados» só o são
  porque as tabelas são pequenas).
- **Timeouts de terceiros:** Supabase 15 s (connect 3 s), SMTP 30 s, Turnstile 10 s; edge 2 s / 8 s.
- **Graceful shutdown:** uvicorn trata SIGTERM; `lifespan` pára os workers (`join` de 5 s).
- **Correlação:** `X-Request-ID` no middleware, incluído nos logs e no Sentry.
- **Concorrência:** `--limit-concurrency 100` (503 em vez de esgotar a RAM).

## Fica por decidir (sem custo, mas muda comportamento)
- Token do backoffice em `safeStorage` do Electron (cifrado pelo sistema) em vez de `localStorage`
  — exige nova versão do backoffice.
- Redis sem persistência: cada deploy termina as sessões do backoffice (é preciso voltar a entrar).

## Depois do deploy de `1f4e233`
O aviso novo do ponto 5 revelou mais um defeito: `workers/email_worker.py` procurava a conversa
com `LIKE` numa coluna `uuid` (`operator does not exist: uuid ~~ unknown`). Falhava sempre e caía
no plano B (varrer as 500 mensagens mais recentes), por isso as respostas eram ligadas, mas com uma
ida à BD perdida e sem funcionar para conversas mais antigas. Corrigido em `95ec3a3` (intervalo na
chave primária), publicado a 2026-10-22: 0 falhas nos logs depois do deploy.

O estado do worker de email (`.email_worker_state.json`) ficava fora do volume `data/` e perdia-se
a cada deploy (reprocessava ~100 emails). Corrigido em `cd16ab6`/`e7292c6`, publicado a 2026-10-23: estado em `data/`, 0 duplicados.
