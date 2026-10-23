# deploy/ — publicação, verificação e operação

Procedimentos completos em [`docs/runbook.md`](../docs/runbook.md). Nada aqui guarda segredos:
os scripts lêem o `.env` da raiz (produção) ou pedem os valores escondidos no terminal.

## Publicar
| Ficheiro | Função |
|---|---|
| `vm/remote_deploy.sh` | Deploy da API na VM com recuo automático para a imagem anterior (usado pelo `deploy-api.yml` e à mão) |
| `vm_access.py` | `ssh`/`scp` para a VM por gcloud + IAP (a porta 22 não está aberta à internet) |
| `docker-compose.free.yml` | API + Redis + Cloudflare Tunnel na VM (logs com rotação) |
| `create_gcp_vm.py` | Cria a VM e2-micro Always Free |
| `publish_backoffice_update.py` / `fetch_backoffice_release.py` | Feed de actualização automática do backoffice / instaladores para o cliente |
| `set_vm_env.py` | Grava variáveis secretas no `.env` da VM pedindo-as escondidas (passagem de contas) |

A loja publica-se com `npm run build:prod` + `wrangler` ([runbook §1](../docs/runbook.md)).

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
| `vm/backup_db.sh` + `install_db_backups.py` | Backup diário da BD e dos utilizadores do backoffice (cron 03:30 UTC, 14 dias) |
| `vm/restore_test.sh` | Restaura o último backup numa BD descartável e compara contagens |
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
