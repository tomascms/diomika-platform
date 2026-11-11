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
- **Um modelo ou categoria publicado no backoffice não pede deploy:** abre pelo link directo (a Function
  `_middleware.js` confirma na API que existe e serve a loja) e entra no `sitemap.xml` (a Function `sitemap.xml.js`
  gera-o da API a cada pedido). O deploy só refaz as páginas pré-geradas, com o título, a descrição e o conteúdo sem
  JavaScript para o Google e as pré-visualizações do WhatsApp; vale a pena lançá-lo depois de publicar vários modelos.
- **Quem invoca as Functions:** `public/_routes.json` manda para as Functions todos os pedidos de páginas, `/api` e
  `/sitemap.xml`, e deixa de fora os ficheiros estáticos (`/assets/*`, `/brand/*`, ícones, `robots.txt`…). Antes cada
  página gastava ~30 invocações (o plano grátis dá 100 000 por dia e por conta, partilhadas com outros Workers). Um
  ficheiro novo na raiz de `frontend-web/public/` que não seja uma página tem de entrar em `exclude`
  (`functions-test/config.test.js` falha se faltar). Esses ficheiros levam os cabeçalhos de segurança de
  `public/_headers.production`, que têm de dizer o mesmo que o middleware (o mesmo teste verifica).
- **A versão do catálogo na cache da Cloudflare** (a que dá a frescura a `/api`) renova-se em segundo plano: depois de um
  período sem visitas, o primeiro pedido ainda vê o catálogo antigo e o seguinte já vê o publicado. Se for preciso
  ver a mudança já, recarregar a página uma vez.
- **O build falha se a API não responder** (ou o catálogo vier vazio): é de propósito, para não publicar o site sem as
  páginas de catálogo. Repetir o workflow quando a API estiver de pé.
- Um endereço `/categoria/...` que não existe dá HTTP 404 (com `404.html`); uma categoria que existe mas não tem
  modelos abre, sem indexar. As categorias vazias não aparecem na loja.

## 2. API (Render, plano free)
- **Serviço:** `diomika-api` no Render (Frankfurt, Docker, plano free, sem cartão: não cobra), com o Key Value
  `diomika-redis` (free). `api.diomika.com` é um CNAME com proxy da Cloudflare para `diomika-api.onrender.com`.
  Criado a 2026-11-03, quando a API saiu da VM da Google (o script da migração está no histórico do git).
- **Deploy:** automático a cada push na `main` (o Render constrói o `Dockerfile` e só troca quando `/health/live`
  responde). À mão: painel do Render → *Manual Deploy*.
- **Rollback:** painel → *Events* → *Rollback* no deploy anterior.
- **Logs:** painel → *Logs* (não ficam guardados muito tempo). Erros também no Sentry.
- **Alterar uma variável de produção:** painel → *Environment* (o serviço reinicia sozinho). O `.env` da raiz do PC é
  a cópia de referência; manter os dois iguais.
- **Limites do free:** 512 MB, 0,1 CPU, 750 h/mês. O vigia (`deploy/watchdog`, cron da Cloudflare de 10 em 10 min)
  chama `/health/live` para o serviço nunca adormecer (744 h/mês). O disco apaga-se a cada arranque: os utilizadores do
  backoffice e o estado do email ficam no Supabase (`STATE_STORE=supabase`, tabela `app_state`); as sessões e os logs não
  sobrevivem a um reinício. A actualização automática do backoffice não é servida (os instaladores passam dos 50 MB do
  Storage grátis): instalar as versões novas à mão.
- **Limite por IP:** quem chamar `diomika-api.onrender.com` directamente, sem passar pela Cloudflare, pode escolher o
  `CF-Connecting-IP` e fugir ao limite por IP (`TRUSTED_PROXY_IPS=10.0.0.0/8`).
- **Contenção de incidente:** `SECURITY_LOCKDOWN=1` em *Environment*. Se houver dados pessoais
  envolvidos (acesso indevido, chave exposta, dados perdidos), avisar logo o responsável da Diomika: a lei dá 72
  horas, desde que se sabe, para notificar a CNPD se houver risco (RGPD, art. 33.º).

## 3. Base de dados (Supabase)
- SQL em `db/` (ver `db/README.md`). Aplicar cada ficheiro de `db/migrations/` com `apply_migration` (fica no histórico), por ordem do nome, antes da API. Não há staging: ensaiar numa BD nova criada com a baseline.
- **Backup diário:** GitHub Actions *Backup da base de dados* (`.github/workflows/db-backup.yml`) às 03:30 UTC:
  `pg_dump -Fc` verificado com `pg_restore --list`, guardado como artefacto do run durante 14 dias (Actions → run →
  *Artifacts*). Secret `DB_BACKUP_URL` (pooler, porta 5432). Inclui `app_state` (utilizadores do backoffice e estado
  do email).
- **Restaurar** (só para uma BD de teste, nunca directo em produção sem decisão):
  ```bash
  docker run --rm -i -e PGPASSWORD=... postgres:17-alpine \
    pg_restore --clean --if-exists -h <host> -U <user> -d postgres < diomika-AAAA-MM-DD.dump
  ```
- **Depois de restaurar uma cópia** para servir o site: as cópias guardam-se 14 dias, por isso um apagamento só chega a
  elas ao fim desse prazo. Antes de a BD voltar a servir o site, voltar a apagar o que foi apagado depois da data da
  cópia (pedidos de apagamento RGPD e o que a retenção já tinha apagado).
- Imagens: bucket `product-images` público. A 2026-10-21 os URLs assinados (expirados) de
  `categories.imagem` e `product_model_colors.imagem` passaram a URL pública; os valores antigos
  estão em `backup.image_urls_20261021` (schema não exposto pela API). Apagar essa tabela quando
  já não for precisa.
- O plano Free não tem backups descarregáveis nem PITR, e pausa o projecto ao fim de 7 dias sem
  pedidos (o tráfego normal da loja evita isso).

## 4. Backoffice
- **Nova versão:** subir `version` em `backoffice-desktop/package.json`, merge, e criar a tag
  `backoffice-vX.Y.Z` (ou Actions → *Backoffice release* → Run workflow).
- **Instaladores:** Windows com `npm run dist:win` em `backoffice-desktop/` (lê o gate do `.env`); Mac com Actions →
  *Backoffice Mac build* → Run workflow, descarregar o artefacto e apagá-lo logo. Os dois vão para `cliente-backoffice/`
  (fora do git) e entregam-se em mão. Nunca publicar: o instalador leva o gate, que é a chave de administração.
- **Actualização automática:** desligada no Render (o disco apaga-se a cada arranque); instalar cada versão à mão. O
  publicador do feed está no histórico do git.
- **Assinatura das actualizações (SEG-16):** cada `latest*.yml` publicado leva um `.sig` Ed25519. A chave privada
  está só no PC de quem publica, fora do repositório (`~/.diomika/update-signing-ed25519.pem`, ou o caminho em
  `DIOMIKA_UPDATE_SIGNING_KEY_FILE`), cifrada com senha (`DIOMIKA_UPDATE_KEY_PASSPHRASE` ou pergunta no terminal;
  uma chave antiga sem senha cifra-se com `python deploy/update_signing.py protect <ficheiro>`); copie-a e a senha para o cofre. A pública está em
  `backoffice-desktop/electron/update-key.cjs`. A versão 1.4.0 é a primeira que verifica: quem estiver na 1.3.0 recebe
  a 1.4.0 sem verificação e, daí em diante, só instala o que estiver assinado. Perder a chave obriga a reinstalar
  à mão uma versão com a chave nova. Antes de cada release: `npm audit --omit=dev` no backoffice.
- **Utilizadores:** guardados no Supabase, tabela `app_state`, chave `admin_users`. O utilizador inicial
  vem de `ADMIN_BOOTSTRAP_USER` / `ADMIN_BOOTSTRAP_PASSWORD`.
- **Backoffice sem palavra-passe (desde 1.5.0, decisão do dono):** com `ADMIN_DESKTOP_AUTOLOGIN=1` no Render, o
  gate `DIOMIKA_DESKTOP_GATE` do instalador basta para entrar como admin (actor `backoffice`). Instalador perdido:
  apagar `ADMIN_DESKTOP_AUTOLOGIN` (volta o login com palavra-passe) ou rodar o gate e reinstalar. Sem auto-update:
  cada versão instala-se à mão a partir de `backoffice-desktop/release/`.
- **Família de produto nova:** [adicionar-familia.md](adicionar-familia.md).

## 5. Email
- Envio pela Gmail API (`GMAIL_*`; o Render grátis bloqueia o SMTP) e leitura das respostas por IMAP (`IMAP_*`).
  Autorizar de novo, se a Google retirar o acesso: `python deploy/gmail_autorizar.py`.
- Respostas do backoffice levam `In-Reply-To`/`References`; o worker liga as respostas do cliente
  à conversa pelo `[Ref: #xxxxxxxx]` no assunto.

### Zona `diomika.com` e email (estado a 2026-11-10, na conta Cloudflare do cliente)
- **Sem email público e sem `@diomika.com`** até o cliente indicar um (ficha do cliente, Parte D, item 2); o contacto
  electrónico é o formulário. Por isso a zona **não envia nem recebe** email: SPF `v=spf1 -all`, MX nulo (`0 .`),
  `_dmarc` `v=DMARC1; p=reject; adkim=s; aspf=s`. Se passar a haver email próprio, rever os três antes de o activar.
- CAA: `letsencrypt.org`, `pki.goog` e `ssl.com`. DNSSEC ligado.
- Apex `diomika.com` e `www`: CNAME (com proxy) para `diomika-loja-3xx.pages.dev`; sem eles a loja cai (aconteceu a
  2026-11-10). Apex: domínio personalizado do Pages, e redirecção 301
  para `https://www.diomika.com/` com caminho e parâmetros mantidos. Verificar: `curl -sI http://diomika.com/x?y=1`.
- Early Hints e Tiered Cache (smart) ligados. Registo de novos utilizadores no Supabase Auth desligado (a app não o usa).

## 6. Verificação depois de cada deploy
```bash
for u in https://www.diomika.com/ https://www.diomika.com/categorias https://www.diomika.com/contacto \
         https://www.diomika.com/api/categorias https://api.diomika.com/health/live https://api.diomika.com/health; do
  curl -s -o /dev/null -w "%{http_code} $u\n" -A "Mozilla/5.0 (DiomikaDeployCheck)" "$u"
done
```
Todos 200. Nos *Logs* do Render, nenhum 5xx nos últimos 15 minutos.
O workflow *Deploy loja* também confirma o catálogo: o `sitemap.xml` tem pelo menos 30 `<loc>`, um modelo do mapa abre
(200) e `/categoria/nao-existe-deploy-check` dá 404.

## 7. Rodar chaves
Ordem para não haver falhas: criar a chave nova no serviço → actualizar o *Environment* do Render (e o `.env` do PC) e/ou o
secret do GitHub → reiniciar a API ou re-publicar a loja → verificar (secção 6) → revogar a antiga.
`API_SECRET_KEY_PREVIOUS` permite aceitar a chave antiga durante a transição.

| Variável | Onde se cria | Onde se usa |
|---|---|---|
| `SUPABASE_KEY`, `SUPABASE_DB_PASSWORD` | Supabase → Settings | Render (*Environment*) |
| `VITE_SUPABASE_ANON_KEY` | Supabase → API | secret GitHub |
| `TURNSTILE_SECRET_KEY` / `VITE_TURNSTILE_SITE_KEY` | Cloudflare → Turnstile | Render (*Environment*) / secret GitHub |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → API Tokens | secret GitHub |
| `RENDER_API_KEY` | Render → Account Settings → API Keys | `.env` do PC (`deploy/render_setup.py`) |
| `DB_BACKUP_URL` | a partir de `SUPABASE_DB_PASSWORD` | secret GitHub |
| `MAIL_PASSWORD` | conta de email (app password) | Render (*Environment*) |
| `API_*_KEY`, `DIOMIKA_DESKTOP_GATE` | gerar (`python -c "import secrets;print(secrets.token_urlsafe(32))"`) | Render (*Environment*); o gate também no secret GitHub e exige nova versão do backoffice |
| `SENTRY_*`, `AXIOM_TOKEN`, `POSTHOG_*`, `UPTIMEROBOT_API_KEY` | cada serviço | Render (*Environment*) / secrets |

## 8. Vigilância
- UptimeRobot: API e loja (alerta por email).
- Vigia da Cloudflare (`deploy/watchdog`): `/health/live` e `www.diomika.com` de 10 em 10 min, alerta por ntfy no máximo uma vez por hora.
- Sentry: erros da API.
- Status público: https://www.diomika.com/status.html

## 8b. Recuperação (backups e cenários de perda)
**Objectivos que 0 € permite:** RPO 24 h para a BD (dump diário às 03:30 UTC; o Supabase Free não tem PITR) e 7 dias
para as fotos; RTO da API 2 h com a pessoa disponível (o catálogo continua a servir pelo edge entretanto: a loja
aguenta-se, só contacto e orçamento ficam em baixo).

**Onde estão as cópias:** artefactos do workflow *Backup da base de dados* (14 dias). Uma falha aparece como run
vermelho no GitHub (aviso por email). As fotografias já não têm cópia automática desde que a VM parou: copiar à mão
quando o catálogo mudar muito.

**Ensaio da reposição (mensal):** repor o dump num Postgres descartável (`docker run -d -e POSTGRES_PASSWORD=x -p
5433:5432 postgres:17-alpine`, depois o `pg_restore` da secção 3 para `localhost:5433`) e contar as tabelas principais. Registar aqui a data, o tempo e as contagens (têm de bater com a produção):

| Data | Dump | Tempo | Contagens | Resultado |
|---|---|---|---|---|
| (por registar: o primeiro ensaio depois desta versão) | | | | |

**1. Serviço do Render perdido.** No painel do Render: *New* → *Key Value* `diomika-redis` (free, Frankfurt) e *Web
Service* do repositório (Docker, free, Frankfurt, *Health Check* `/health/live`), com as variáveis do `.env`. Depois,
*Custom Domains* → `api.diomika.com` e o CNAME `api` na Cloudflare para o host novo. Os utilizadores do backoffice estão no Supabase (`app_state`).
Verificar `/health/ready` e entrar no backoffice.

**2. Supabase perdido ou em pausa.** Em pausa: retomar no painel (os dados mantêm-se 90 dias). Perdido: criar projecto
novo (Free), aplicar `db/migrations/` pela ordem do `db/README.md` e repor o dump mais recente com `pg_restore
--clean --if-exists --no-owner`; carregar as fotografias da cópia manual para o bucket `product-images` com o mesmo
caminho; correr `deploy/backfill_thumbnails.py --apply`; trocar
`SUPABASE_URL`/`SUPABASE_KEY`/`SUPABASE_DB_PASSWORD` no *Environment* do Render e nos secrets `VITE_SUPABASE_*`; republicar loja e API.

**3. Conta Cloudflare ou domínio perdidos.** O domínio recupera-se no registador. Numa conta nova: adicionar a zona,
recriar os registos (apex e `www` para o Pages, `api` em CNAME para `diomika-api.onrender.com`, SPF `-all`, MX nulo, DMARC `reject`, CAA; §«Zona»
e `docs/entrega/migracao-contas.md`), o projecto Pages `diomika-loja` (secção 1), as regras de `deploy/cloudflare/`
e apontar o CNAME `api` para `diomika-api.onrender.com`.

**4. Chaves comprometidas em massa.** Rodar tudo pela ordem do §7 (Supabase, Turnstile, Render, chave da API,
`ADMIN_*`), invalidar as sessões (reiniciar o Redis) e reler `admin_audit_log`. A chave de assinatura das
actualizações do backoffice (§4) só se troca com uma versão nova assinada pela antiga.

## 9. Continuidade (se quem mantém o site não estiver disponível)
Objectivo: quem assumir a manutenção consegue publicar, rodar chaves e recuperar sem depender da memória de ninguém.

**Onde está cada coisa**

| O quê | Onde |
|---|---|
| Código | Repositório Git, ramo `main`; os secrets do Actions estão nele |
| Loja e DNS | Cloudflare: projecto Pages `diomika-loja`, zona `diomika.com`, regras em `deploy/cloudflare/waf_rules.json` |
| API | Render: serviço `diomika-api` e Key Value `diomika-redis` (Frankfurt, free) |
| Variáveis de produção | Render → *Environment* (cópia no `.env` da raiz do PC; nomes na secção 7) |
| Utilizadores do backoffice | Supabase, tabela `app_state` |
| Backups | Artefactos do workflow `db-backup.yml` (03:30 UTC, 14 dias) |
| BD e imagens | Supabase; bucket `product-images` |
| Email | A caixa configurada em `MAIL_*` e `IMAP_*` no `.env` |
| Vigilância | UptimeRobot, vigia da Cloudflare, Sentry, Axiom, PostHog e ntfy |

**Segredos e cofre.** Os valores de produção existem só no *Environment* do Render, no do computador de quem mantém (o `.env` da raiz
do repositório é o de produção) e nos secrets do GitHub; nada no repositório. Para uma segunda pessoa conseguir recuperar,
**uma cópia do `.env` de produção e os códigos de recuperação do 2FA de cada conta ficam num cofre de palavras-passe do
cliente** (por exemplo Bitwarden, gratuito), nunca por email, chat ou repositório. Quando o `.env` mudar (secção
7), actualizar a cópia do cofre no mesmo dia.

**Quem assume**
1. O cliente abre o cofre e convida a pessoa nova, com o papel mínimo: Cloudflare (*Members*, *Administrator*),
   Supabase (*Team*, *Developer*), Render (membro do *workspace*) e acesso ao código.
2. No Render, confirmar que `diomika-api` está *Live*; no GitHub, que o último *Backup da base de dados* é de hoje
   ou de ontem.
3. Comparar os nomes das variáveis do `.env` do cofre com o *Environment* do Render (nomes, nunca valores).
4. Rodar as chaves que a pessoa anterior conheceu (secção 7), `DIOMIKA_DESKTOP_GATE` por último.
5. Publicar pelas secções 1 e 2 e verificar com a secção 6.
6. Retirar o acesso da pessoa anterior, se for o caso, e actualizar este quadro.
