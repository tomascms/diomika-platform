#!/usr/bin/env bash
# Deploy da API na VM: único sítio com estes passos (o deploy-api.yml envia e corre este script).
# Espera /tmp/diomika-deploy.tar. Uso manual: docs/runbook.md secção 2.
# backend-api é substituído por inteiro (o tar não apaga ficheiros removidos); data/ fica.
set -uo pipefail
D="${1:-/home/deploy/diomika}"
cd "$D" || exit 1
sudo mkdir -p "$D/backend-api"
sudo find "$D/backend-api" -mindepth 1 -maxdepth 1 ! -name data -exec rm -rf {} +
sudo tar -xf /tmp/diomika-deploy.tar -C "$D" && rm -f /tmp/diomika-deploy.tar
COMPOSE="sudo docker compose --env-file .env -f deploy/docker-compose.free.yml --profile tunnel"
TAG=rollback-$(date +%Y%m%d-%H%M%S); HAVE_ROLLBACK=0
if sudo docker image inspect deploy-api:latest >/dev/null 2>&1; then
  sudo docker tag deploy-api:latest deploy-api:$TAG && HAVE_ROLLBACK=1 && echo "rollback: deploy-api:$TAG"
fi
# Todos os serviços: aplica também mudanças de config ao redis/cloudflared (só recria o que mudou).
$COMPOSE up -d --build 2>&1 | tail -5 || exit 2
for i in $(seq 1 30); do
  if curl -sf -A DiomikaHealthcheck/1.0 http://127.0.0.1:8000/health/live >/dev/null; then
    curl -s -A DiomikaHealthcheck/1.0 http://127.0.0.1:8000/health; echo
    sudo docker images deploy-api --format '{{.Tag}}' | grep '^rollback-' | sort -r | tail -n +4 | xargs -r -I{} sudo docker rmi deploy-api:{} >/dev/null 2>&1
    # Disco da e2-micro (30 GB): imagens sem tag e cache de build acima de 3 GB enchiam-no a cada deploy.
    sudo docker image prune -f >/dev/null 2>&1
    sudo docker builder prune -f --keep-storage 3GB >/dev/null 2>&1
    df -h / | tail -1
    exit 0
  fi
  sleep 4
done
echo "ERRO: a API nova não respondeu em 2 min — a repor a versão anterior"
if [ $HAVE_ROLLBACK = 1 ]; then sudo docker tag deploy-api:$TAG deploy-api:latest && $COMPOSE up -d --no-build api; fi
exit 3
