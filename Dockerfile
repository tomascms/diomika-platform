# Imagem partilhada para API e workers (Railway, VPS, etc.)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend-api/ ./backend-api/

ENV PYTHONPATH=/app/backend-api
ENV UVICORN_WORKERS=1
# Acima disto o uvicorn responde 503 logo, em vez de esgotar a RAM da e2-micro sob ataque.
ENV UVICORN_LIMIT_CONCURRENCY=100
WORKDIR /app/backend-api

# Multi-worker — escala horizontal por CPU (VM produção)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-1} --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY:-100} --timeout-keep-alive 5"]
