"""Ambiente de testes isolado da produção.

O .env da raiz é o de produção e era carregado pelos testes: um teste chegou a
fazer um DELETE real na base de dados, e os erros iam para o Sentry de
produção. Aqui, antes de qualquer import da app, os serviços externos apontam
para valores fictícios (load_project_env não sobrepõe variáveis já definidas),
por isso qualquer teste que tente sair para a rede falha de imediato em vez de
mexer em dados reais.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# `pytest` sem `python -m` não põe backend-api no sys.path.
_BACKEND = str(Path(__file__).resolve().parents[1])
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

_ISOLATED = {
    "DIOMIKA_ENV": "development",
    "RUN_EMBEDDED_WORKERS": "false",
    "SUPABASE_URL": "https://ci-placeholder.supabase.co",
    "SUPABASE_KEY": "ci-placeholder-key",
    "DATABASE_URL": "postgresql://ci:ci@127.0.0.1:1/ci",
    "REDIS_URL": "",
    "SENTRY_DSN": "",
    "AXIOM_TOKEN": "",
    "ALERT_WEBHOOK_URL": "",
    "ALERT_WEBHOOK_REQUIRED": "0",
    "MAIL_SERVER": "",
    "IMAP_SERVER": "",
    "CONTACT_NOTIFY_EMAIL": "",
    "DIOMIKA_WARMUP": "0",
}
for key, value in _ISOLATED.items():
    os.environ[key] = value

# Importa a app uma vez, em desenvolvimento, antes de algum teste mudar o
# ambiente (ex.: monkeypatch de DIOMIKA_ENV=production) e deixar o módulo
# meio importado com a configuração errada em cache.
import main  # noqa: E402,F401
