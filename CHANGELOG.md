# Changelog

Versão única do ecossistema em `backend-api/core/version.py`. Backoffice com versão própria
em `backoffice-desktop/package.json`.

## [Por versionar] — 2026-10-22/23 (em produção: loja `f314882`, API `aa8a9b0`)

### Desempenho (medido em produção, telemóvel)
- LCP da página de produto nunca visitada 3,9 s → 1,0–1,7 s: *preload* da imagem principal no HTML
  pré-renderizado e detalhes dos 26 modelos pré-aquecidos em Redis no arranque e após escritas.
- CLS 0,9 → 0 (rodapé abaixo da dobra) e 0,15 → 0 nas categorias (barra de filtros sempre presente).
- Página inicial: imagem principal 435 KB → 22 KB; miniaturas 960 px para ecrãs 2–3×.
- Edge: timeouts (2 s/8 s) e última versão do catálogo conhecida — a loja continua a servir o
  catálogo com a API em baixo.

### Corrigido (auditoria de requisitos não funcionais)
- Formulários de contacto/orçamento, respostas e importação CSV bloqueavam o event loop (1 worker:
  a API inteira parava ~1 s por envio). I/O síncrono passou para `asyncio.to_thread`.
- Procura da conversa de cada resposta por email usava `LIKE` numa coluna `uuid` (falhava sempre).
- Estado do worker de email fora do volume: reprocessava ~100 emails a cada deploy.
- Resposta a cliente devolvia 500 depois de o email já ter saído (reenvio em duplicado).
- Página de produto com scroll horizontal a 320 px.

### Segurança e privacidade
- Sessões do backoffice: 7 dias no máximo e 12 h sem uso (antes 30 dias, sem inactividade).
- Login: 5 tentativas/min por IP. Regra de rate limiting na Cloudflare para os formulários.
- Nomes de filtro da query string validados antes de entrarem no caminho PostgREST.
- CSP limitada ao host Supabase do projecto; `Access-Control-Allow-Origin: *` retirado das páginas.
- A loja deixou de guardar nome/email/telefone no `localStorage` (e limpa o que versões antigas guardaram).

### Operação e observabilidade
- `/metrics` Prometheus (localhost + chave ops/admin); logs JSON com `service` e `env`;
  falhas antes engolidas passam a ser registadas; fila de logs esvaziada no SIGTERM.
- uvicorn com `--limit-concurrency`; logs do Docker com rotação; deploy limpa imagens e cache de
  build (disco 69 % → 57 %); `deploy-api.yml` corre o mesmo `remote_deploy.sh`.
- Tabelas `legacy_*` apagadas (dump guardado); pasta da VM limpa; imagens órfãs do Storage
  removidas com cópia local.
- CI falha se a cobertura de testes descer abaixo de 56 %.
- Passagem de contas: `deploy/set_vm_env.py` (segredos escritos escondidos, directamente na VM)
  e lista de passagem para o cliente.

## [2.5.0] — 2026-10-21 (preparação da entrega)

### Incidente corrigido (loja publicada a 2026-10-21)
- Os formulários de contacto e orçamento falhavam desde o deploy de 2026-10-13: a CSP do
  `functions/_middleware.js` bloqueava o Turnstile e a API recusava os pedidos sem token.
  O middleware usa agora a CSP de `_headers.production`; `verify_csp.py` falha se divergirem.

### Performance
- Miniaturas WebP de 480 px para listas e cartões (antes: fotos até 1500 px para 90 px no ecrã);
  `deploy/backfill_thumbnails.py` gera as das imagens existentes.
- Loja sem Supabase Realtime (era a query mais pesada da BD; supabase-js já não carrega em todas as visitas).
- API: envio de logs para o Axiom fora do event loop (bloqueava todos os pedidos e coincidia
  com 31 reinícios do worker numa semana); logs do httpx em WARNING; 1 worker uvicorn.
- Removido o framework genérico de sagas e a thread que o sondava a cada 10 s.
- `HEAD /health` responde 200 (o monitor de uptime recebia 405).

### Segurança e operação (2026-10-21)
- VM: SSH/RDP deixaram de estar abertos à internet; acesso só por IAP (`deploy/vm_access.py`).
- Identidade de deploy GitHub → GCP por Workload Identity Federation (sem chaves).
- Storage `product-images` público; URLs de imagem na BD passaram a públicos (backup em `backup.image_urls_20261021`).
- Trigger de variantes com `search_path` fixo (advisor de segurança do Supabase sem avisos).
- Backup diário inclui os utilizadores do backoffice; teste de restauro (`deploy/vm/restore_test.sh`) feito.
- Deploys substituem `backend-api/` por inteiro (antes ficavam módulos apagados na imagem).
- Formulários: autocomplete, `type=tel`, erros anunciados a leitores de ecrã.

### Corrigido
- CI voltou a verde: `Dockerfile` reposto (tinha sido apagado e partia o deploy da API), teste
  partido, gitleaks com permissões e sem upload de artefactos.
- Rotas do catálogo: `/categoriasX` deixou de contar como catálogo (comportamento anterior reposto).
- Uma família de produto nova precisa só da entrada em `CATEGORY_ATTRIBUTE_SCHEMAS` (antes dava
  `KeyError` sem um segundo registo manual).
- Vulnerabilidades altas do npm (DOMPurify, vue, source-map-js).

### Segurança e RGPD
- Emails mascarados em todos os logs (`j***@dominio`).
- Testes e2e deixaram de poder apontar para produção (precisam de `E2E_API_URL`).
- Removido `scripts/seed_database.py`, que escrevia na BD do `.env` (produção).
- Política de privacidade com responsável, subcontratantes, transferências e CNPD.
- Turnstile aceita `TURNSTILE_SECRET_KEY_PREVIOUS` durante a troca de widget.

### Email
- Respostas do backoffice com `Message-ID`, `In-Reply-To` e `References`: ficam no mesmo fio no
  email do cliente.

### Operação
- Workflow `deploy-api.yml` (manual, com recuo automático e acção de rollback).
- Backup diário inclui `admin_users.json`.
- SQL reunido em `db/` com índice; ficheiros legados separados.
- Lint do backoffice no CI.
- Minutos do Actions: uptime e release do backoffice só a pedido; artefactos 7 dias.
- Removido código morto (health runner e camada de exceções sem uso) e scripts sem uso;
  Makefile só com alvos reais.

### Documentação
- Novos: guia do cliente, runbook, adicionar família, estado final, ficha e migração de contas.
- Removidos documentos desactualizados ou inventados (`RELATORIO_TECNICO.md`, `INSTRUCOES.md`,
  `DISASTER_RECOVERY.md`, `GITHUB_ACTIONS_SECRETS.md`, `CACHE_INVALIDATION_INTEGRATION.md`).

## [2.4.0] — 2026-10-03
- Catálogo unificado (3 tabelas físicas para todas as famílias); tabelas antigas renomeadas `legacy_*`.
- Loja publicada pelo GitHub; páginas SEO pré-geradas; cache no edge por versão do catálogo.
- Backoffice 1.2.1 com actualização automática (Windows e Linux).
- Backup diário da BD na VM.
