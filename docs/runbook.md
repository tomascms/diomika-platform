# Runbook de operação

Regra geral: tudo o que muda produção passa por um PR com o CI verde. Depois de cada deploy,
verificar o site live (secção 6).

## 1. Loja (Cloudflare Pages)
- **Deploy:** automático no merge para a `main` de qualquer alteração em `frontend-web/`
  (`deploy-loja.yml`). Também se lança à mão em Actions → *Deploy loja* → Run workflow.
- **Rollback:** Cloudflare → Workers & Pages → `diomika-loja` → Deployments → deploy anterior
  → **Rollback to this deployment**. Imediato, sem rebuild.
- **Sem GitHub Actions:** `npm run build:prod` em `frontend-web/` e
  `npx wrangler pages deploy dist --project-name diomika-loja --branch production`.
- Segredos de build: secrets do repositório `VITE_*`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.

## 2. API (VM GCP)
- **Acesso à VM:** só por IAP (a firewall fecha a porta 22 ao resto da internet):
  `gcloud compute ssh diomika-api --zone us-west1-a --project diomika --tunnel-through-iap`.
- **Deploy:** Actions → *Deploy API* → Run workflow → `deploy`. Envia o código da `main`,
  reconstrói a imagem e espera 2 min por `/health/live`; se falhar, repõe a imagem anterior
  sozinho. Configuração necessária no cabeçalho de `ops/workflows/deploy-api.yml`.
- **Rollback:** o mesmo workflow com `rollback` (repõe a última imagem `deploy-api:rollback-*`).
- **Logs:** na VM, `sudo docker logs --since 1h deploy-api-1`. Erros também no Sentry.
- **Alterar uma variável de produção:** editar `~/diomika/.env` na VM e
  `sudo docker compose --env-file .env -f deploy/docker-compose.free.yml --profile tunnel up -d api`.
- **Contenção de incidente:** `SECURITY_LOCKDOWN=1` no `.env` da VM e reiniciar a API.
- **Sem GitHub Actions** (ex.: minutos esgotados), com `gcloud` autenticado:
  ```bash
  tar --force-local -cf deploy.tar --exclude=__pycache__ --exclude=backend-api/data --exclude=backend-api/logs backend-api requirements.txt Dockerfile .dockerignore deploy/docker-compose.free.yml
  gcloud compute scp deploy.tar deploy/vm/remote_deploy.sh diomika-api:/tmp/ --zone us-west1-a --project diomika --tunnel-through-iap
  gcloud compute ssh diomika-api --zone us-west1-a --project diomika --tunnel-through-iap --command 'mv /tmp/deploy.tar /tmp/diomika-deploy.tar; nohup bash -c "bash /tmp/remote_deploy.sh; echo EXIT=\$?" > /tmp/deploy.log 2>&1 < /dev/null &'
  ```
  O build demora ~25 min na e2-micro; acompanhar com `tail /tmp/deploy.log` (termina em `EXIT`).

## 3. Base de dados (Supabase)
- SQL em `db/` (ver `db/README.md`). Aplicar no SQL Editor, primeiro em staging.
- **Backup diário:** cron na VM às 03:30 UTC (`deploy/vm/backup_db.sh`, instalado por
  `python deploy/install_db_backups.py`): `pg_dump` do schema `public` e cópia de
  `admin_users.json` para `~/backups/db`, 14 dias.
- **Restaurar** (só para uma BD de teste, nunca directo em produção sem decisão):
  ```bash
  docker run --rm -i -e PGPASSWORD=... postgres:17-alpine \
    pg_restore --clean --if-exists -h <host> -U <user> -d postgres < diomika-AAAA-MM-DD.dump
  ```
- Imagens: bucket `product-images` público. A 2026-10-21 os URLs assinados (expirados) de
  `categories.imagem` e `product_model_colors.imagem` passaram a URL pública; os valores antigos
  estão em `backup.image_urls_20261021` (schema não exposto pela API). Apagar essa tabela quando
  já não for precisa.
- O plano Free não tem backups descarregáveis nem PITR, e pausa o projecto ao fim de 7 dias sem
  pedidos (o tráfego normal da loja evita isso).

## 4. Backoffice
- **Nova versão:** subir `version` em `backoffice-desktop/package.json`, merge, e criar a tag
  `backoffice-vX.Y.Z` (ou Actions → *Backoffice release* → Run workflow).
- **Publicar a actualização automática:** descarregar os artefactos do run e
  `python deploy/publish_backoffice_update.py --extra-dir <pasta>`.
- **Sem GitHub Actions (Windows):** em `backoffice-desktop/`, `npm run dist:win` (lê o gate do
  `.env`) e depois `python deploy/publish_backoffice_update.py`. O script envia o instalador antes
  do `latest.yml` e confirma o feed; os PCs actualizam-se sozinhos no arranque.
- **Utilizadores:** guardados em `backend-api/data/admin_users.json` na VM. O utilizador inicial
  vem de `ADMIN_BOOTSTRAP_USER` / `ADMIN_BOOTSTRAP_PASSWORD`.
- **Família de produto nova:** [adicionar-familia.md](adicionar-familia.md).

## 5. Email
- Envio por SMTP e leitura das respostas por IMAP (`MAIL_*`, `IMAP_*` no `.env` da VM).
- Respostas do backoffice levam `In-Reply-To`/`References`; o worker liga as respostas do cliente
  à conversa pelo `[Ref: #xxxxxxxx]` no assunto.

## 6. Verificação depois de cada deploy
```bash
for u in https://www.diomika.com/ https://www.diomika.com/categorias https://www.diomika.com/contacto \
         https://www.diomika.com/api/categorias https://api.diomika.com/health/live https://api.diomika.com/health; do
  curl -s -o /dev/null -w "%{http_code} $u\n" -A "Mozilla/5.0 (DiomikaDeployCheck)" "$u"
done
```
Todos 200. Na VM, `sudo docker logs --since 15m deploy-api-1 | grep -c " 5[0-9][0-9] "` deve dar 0.

## 7. Rodar chaves
Ordem para não haver falhas: criar a chave nova no serviço → actualizar o `.env` da VM e/ou o
secret do GitHub → reiniciar a API ou re-publicar a loja → verificar (secção 6) → revogar a antiga.
`API_SECRET_KEY_PREVIOUS` permite aceitar a chave antiga durante a transição.

| Variável | Onde se cria | Onde se usa |
|---|---|---|
| `SUPABASE_KEY`, `SUPABASE_DB_PASSWORD` | Supabase → Settings | `.env` VM |
| `VITE_SUPABASE_ANON_KEY` | Supabase → API | secret GitHub |
| `TURNSTILE_SECRET_KEY` / `VITE_TURNSTILE_SITE_KEY` | Cloudflare → Turnstile | `.env` VM / secret GitHub |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare → Zero Trust → Tunnels | `.env` VM |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → API Tokens | secret GitHub |
| `MAIL_PASSWORD` | conta de email (app password) | `.env` VM |
| `API_*_KEY`, `DIOMIKA_DESKTOP_GATE` | gerar (`python -c "import secrets;print(secrets.token_urlsafe(32))"`) | `.env` VM; o gate também no secret GitHub e exige nova versão do backoffice |
| `SENTRY_*`, `AXIOM_TOKEN`, `POSTHOG_*`, `UPTIMEROBOT_API_KEY` | cada serviço | `.env` VM / secrets |

## 8. Vigilância
- UptimeRobot: API e loja (alerta por email).
- Sentry: erros da API.
- Status público: https://www.diomika.com/status.html
