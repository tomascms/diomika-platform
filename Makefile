# Atalhos locais. Nenhum alvo toca em produção.
.PHONY: install test lint build-loja build-backoffice ci hooks

install:
	pip install -r requirements-dev.txt
	cd frontend-web && npm ci
	cd backoffice-desktop && npm ci

# tests/conftest.py isola tudo; os e2e só correm com E2E_API_URL definida.
test:
	cd backend-api && python -m pytest tests -q

lint:
	bandit -q -r backend-api -lll -iii -x backend-api/tests
	cd frontend-web && npx oxlint src functions && npx eslint src functions

build-loja:
	cd frontend-web && npm run build

build-backoffice:
	cd backoffice-desktop && npx vite build

# O portão: os mesmos passos do CI (scripts/ci_local.py, também corre sem `make`). Inclui os e2e da loja.
ci:
	python scripts/ci_local.py

# Uma vez por clone: liga o hook pre-push (.githooks/pre-push corre o portão sem os e2e).
hooks:
	git config core.hooksPath .githooks
