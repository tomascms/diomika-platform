#!/usr/bin/env bash
# Backup diário da base de dados (Supabase) para o disco da VM.
#
# - pg_dump num contentor postgres:17 descartável (mesma versão do servidor);
# - credenciais tiradas da própria config da API (nada novo guardado);
# - pooler IPv4 da Supabase em modo sessão (o host directo é só IPv6 e a VM
#   não tem IPv6);
# - formato custom (-Fc), verificado com pg_restore --list;
# - guarda 14 dias em ~/backups/db (só o utilizador lê: umask 077);
# - se existir ~/.config/diomika-r2.env, envia também para o Cloudflare R2
#   (cópia fora da VM; a retenção lá é uma regra de ciclo de vida do bucket).
#
# Instalado em cron por deploy/install_db_backups.py. Restaurar:
#   docker run --rm -i -e PGPASSWORD=... postgres:17-alpine \
#     pg_restore --clean --if-exists -h <host> -U <user> -d postgres < ficheiro.dump
set -euo pipefail
umask 077

POOLER_HOST="${POOLER_HOST:-aws-0-eu-west-1.pooler.supabase.com}"
KEEP_DAYS="${KEEP_DAYS:-14}"
DEST="${HOME}/backups/db"
LOG="${DEST}/backup.log"
mkdir -p "$DEST"

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

read -r REF PASS < <(sudo docker exec -w /app/backend-api deploy-api-1 python -c "
import os
from urllib.parse import urlparse
from core.database_url import get_database_url
ref = urlparse(os.environ['SUPABASE_URL']).hostname.split('.')[0]
print(ref, urlparse(get_database_url()).password)
")

STAMP="$(date -u +%Y-%m-%d)"
OUT="${DEST}/diomika-${STAMP}.dump"
TMP="${OUT}.partial"

log "início backup -> ${OUT}"
sudo docker run --rm -e PGPASSWORD="$PASS" postgres:17-alpine \
  pg_dump -h "$POOLER_HOST" -p 5432 -U "postgres.${REF}" -d postgres \
  -Fc --no-owner --no-privileges --schema=public > "$TMP"

# Valida que o ficheiro é um dump legível antes de o aceitar.
TABLES=$(sudo docker run --rm -i postgres:17-alpine pg_restore --list < "$TMP" | grep -c " TABLE DATA " || true)
if [ "${TABLES:-0}" -lt 5 ]; then
  log "ERRO: dump inválido (${TABLES} tabelas) — mantido como ${TMP}"
  exit 1
fi
mv -f "$TMP" "$OUT"
log "ok: $(du -h "$OUT" | cut -f1), ${TABLES} tabelas com dados"

# Utilizadores do backoffice vivem num ficheiro na VM, não na BD.
USERS="${HOME}/diomika/backend-api/data/admin_users.json"
if sudo test -f "$USERS"; then
  sudo cat "$USERS" > "${DEST}/admin_users-${STAMP}.json"  # o contentor grava-o como root
else
  log "aviso: ${USERS} não existe"
fi

find "$DEST" \( -name 'diomika-*.dump' -o -name 'admin_users-*.json' \) -mtime +"$KEEP_DAYS" -print -delete | sed 's/^/removido /' >> "$LOG" || true

# Cópia fora da VM (R2, API S3). Ficheiro criado à mão na VM, chmod 600, com:
#   R2_ACCOUNT_ID=...  R2_BUCKET=...  AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...
# (formato KEY=valor, sem aspas: é lido pelo shell e pelo docker --env-file)
R2_ENV="${HOME}/.config/diomika-r2.env"
if [ -f "$R2_ENV" ]; then
  for f in "$OUT" "${DEST}/admin_users-${STAMP}.json"; do
    [ -f "$f" ] || continue
    # shellcheck disable=SC1090
    if ( . "$R2_ENV"
         sudo docker run --rm -v "${DEST}:/data:ro" --env-file "$R2_ENV" \
           -e AWS_DEFAULT_REGION=auto amazon/aws-cli:2.17.0 \
           s3 cp "/data/$(basename "$f")" "s3://${R2_BUCKET}/db/$(basename "$f")" \
           --endpoint-url "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com" --only-show-errors ); then
      log "r2 ok: $(basename "$f")"
    else
      log "ERRO: envio para R2 falhou: $(basename "$f")"
      R2_FAIL=1
    fi
  done
  [ -z "${R2_FAIL:-}" ] || exit 2
else
  log "aviso: sem ${R2_ENV} — cópia só na VM"
fi
