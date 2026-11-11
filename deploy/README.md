# deploy/ — publicação, verificação e operação

Procedimentos completos em [`docs/runbook.md`](../docs/runbook.md). Nada aqui guarda segredos:
os scripts lêem o `.env` da raiz (produção) ou pedem os valores escondidos no terminal.

## Publicar
| Ficheiro | Função |
|---|---|
| `render_setup.py` | `env NOME`: grava segredos no Render, sem eco, e reinicia a API |
| `gmail_autorizar.py` | Autoriza o envio de email pela Gmail API e grava `GMAIL_*` no Render |
| `watchdog/` | Cron da Cloudflare de 10 em 10 min: mantém o Render acordado e avisa por ntfy se a API ou a loja caírem |

A API publica-se sozinha no Render a cada push na `main`. A loja publica-se pelo Actions (*Deploy loja*) a cada push em
`frontend-web/` ([runbook §1](../docs/runbook.md)). O backoffice entrega-se com o instalador (pasta `cliente-backoffice/`, fora do git).

## Verificar (CI e pós-deploy)
| Ficheiro | Garante |
|---|---|
| `verify_csp.py` | CSP sem `unsafe-*`, igual no `_headers` e no middleware (falhou uma vez: formulários partidos) |
| `verify_bundle_secrets.py` | Nenhum segredo de servidor no bundle da loja |
| `verify_route_guards.py` | Todas as rotas admin têm `Depends` de autorização |
| `verify_ssrf_coverage.py` | Saídas HTTP só por `ssrf_guard` ou hosts fixos |
| `verify_rls.py` | A chave anon do Supabase não lê tabelas sensíveis |
| `verify_env_separation.py` | Regras de separação entre ambientes |
| `validate_sensitive_routes.py` | Inventário de rotas sensíveis |
| `security_gate.py` | Corre o conjunto acima como portão único |
| `security_test.py`, `smoke_test.py`, `verify_production.py`, `uptime_check.py`, `monitor_check.py` | Testes HTTP contra a API/loja em execução |
| `check.py` | Verificação pré-deploy do código e do build |

## Operar
| Ficheiro | Função |
|---|---|
| `../.github/workflows/db-backup.yml` | Backup diário da BD (03:30 UTC, artefacto 14 dias) |
| `backfill_thumbnails.py` | Gera miniaturas 480/960 px em falta no Storage |
| `storage_orphans.py` | Lista/apaga imagens sem referência na BD (copia antes de apagar) |
| `seed_catalog_demo.py` | Dados de demonstração `[TESTE]` |
| `cloudflare/waf_rules.json` | Regras WAF e de rate limiting a recriar numa conta nova |

## Desenvolvimento e carga
| Ficheiro | Função |
|---|---|
| `dev.ps1`, `start_local_api.py` | Arranque local (loja + backoffice; API local em `127.0.0.1:8001`) |
| `load/` | Baseline de latência, teste de carga Python e cenários k6 |
| `launch_lib.py`, `test_http.py` | Bibliotecas partilhadas pelos scripts acima |
