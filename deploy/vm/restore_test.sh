#!/usr/bin/env bash
# Teste de restauro: último dump → Postgres descartável → contagens.
set -u
D=$(ls -t ~/backups/db/diomika-*.dump | head -1)
echo "dump: $(basename "$D")"
sudo docker rm -f restore-test >/dev/null 2>&1 || true
sudo docker run -d --name restore-test -e POSTGRES_PASSWORD=x -m 256m postgres:17-alpine >/dev/null
for i in $(seq 1 30); do sudo docker exec restore-test pg_isready -U postgres >/dev/null 2>&1 && break; sleep 2; done
sudo docker exec restore-test psql -U postgres -qc "create role anon; create role authenticated; create role service_role;" >/dev/null 2>&1
sudo docker exec -i restore-test pg_restore -U postgres -d postgres --no-owner --no-privileges < "$D" > /tmp/restore.log 2>&1
echo "avisos do pg_restore: $(grep -c ERROR /tmp/restore.log)"
grep ERROR /tmp/restore.log | grep -vE "already exists|schema \"public\"" | head -3
cat > /tmp/counts.sql <<'SQL'
select 'categories', count(*) from public.categories
union all select 'product_models', count(*) from public.product_models
union all select 'product_variants', count(*) from public.product_variants
union all select 'product_model_colors', count(*) from public.product_model_colors
union all select 'contact_messages', count(*) from public.contact_messages
union all select 'pedidos_orcamento', count(*) from public.pedidos_orcamento;
SQL
sudo docker exec -i restore-test psql -U postgres -tA -F= < /tmp/counts.sql | tr '\n' ' '; echo
sudo docker rm -f restore-test >/dev/null && echo "contentor removido"
