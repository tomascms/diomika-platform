# Imagem partilhada para API e workers (Railway, VPS, etc.)
# Imagem base por digest (SEG-06): actualizar de propósito (docker buildx imagetools inspect python:3.12-slim).
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# requirements.lock fixa também as transitivas: o que corre é o que os testes viram (API-05).
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -r requirements.txt -c requirements.lock

# Sem root (SEG-07): uid fixo, dono de data/ e logs/.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app     && mkdir -p /app/backend-api/data /app/backend-api/logs     && chown -R app:app /app/backend-api/data /app/backend-api/logs

COPY backend-api/ ./backend-api/

# Commit em produção: `docker compose build --build-arg`/GIT_SHA no ambiente do deploy; visível em /health/detail
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
ENV PYTHONPATH=/app/backend-api
ENV UVICORN_WORKERS=1
# Acima disto o uvicorn responde 503 logo, em vez de esgotar a RAM da e2-micro sob ataque.
ENV UVICORN_LIMIT_CONCURRENCY=100
WORKDIR /app/backend-api
USER app

# Multi-worker — escala horizontal por CPU (VM produção)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-1} --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY:-100} --timeout-keep-alive 5"]
