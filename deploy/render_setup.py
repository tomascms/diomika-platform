"""Variáveis da API no Render (plano free).

  python deploy/render_setup.py env NOME [NOME...]   # escreve segredos escondidos no Render e reinicia a API

Precisa de RENDER_API_KEY no .env (Render → Account Settings → API Keys). O valor pede-se sem eco e vai directo para o
Render: nunca é impresso. A migração da VM da Google para o Render (create/cutover) foi feita a 2026-11-03 e saiu
daqui; está no histórico do git.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV = dotenv_values(ROOT / ".env")
API = "https://api.render.com/v1"
NAME = "diomika-api"


def render(method: str, path: str, **kw):
    r = requests.request(method, API + path, headers={"Authorization": f"Bearer {ENV['RENDER_API_KEY']}"},
                         timeout=60, **kw)
    if r.status_code >= 400:
        sys.exit(f"Render {method} {path}: {r.status_code} {r.text[:300]}")
    return r.json() if r.text else None


def service():
    found = [s["service"] for s in render("GET", f"/services?name={NAME}&limit=5")]
    return found[0] if found else None


def set_env(names: list[str]) -> None:
    """Quem tem o segredo cola-o aqui, sem eco: não passa por chat, ficheiros nem histórico do terminal."""
    if not names:
        sys.exit("Indicar o nome da variável, ex.: env MAIL_PASSWORD")
    svc = service() or sys.exit("Não há serviço no Render.")
    for name in names:
        value = getpass.getpass(f"{name} (não aparece ao escrever): ").strip()
        if not value:
            sys.exit(f"{name} vazio: nada mudou.")
        render("PUT", f"/services/{svc['id']}/env-vars/{name}", json={"value": value})
        print(f"{name} gravado.")
    render("POST", f"/services/{svc['id']}/deploys", json={})
    print("A API reinicia com os valores novos (uns minutos).")


if __name__ == "__main__":
    if sys.argv[1:2] == ["env"]:
        set_env(sys.argv[2:])
    else:
        sys.exit(__doc__)
