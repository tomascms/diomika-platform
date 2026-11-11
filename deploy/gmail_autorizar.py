"""Autoriza o site a enviar email pela conta Gmail do cliente (Gmail API, só envio). Faz-se uma vez.

    python deploy/gmail_autorizar.py

1. Pede, sem eco, o ID e o segredo do cliente OAuth do projecto Google «diomika-email» (só na primeira vez;
   ficam no .env da raiz).
2. Abre o browser: o cliente entra no Gmail dele e carrega em «Permitir».
3. Confirma que a conta é a do MAIL_FROM do Render e grava GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET e
   GMAIL_REFRESH_TOKEN no Render, sem os mostrar, e reinicia a API.

Volta a correr-se só se a autorização cair (ex.: o cliente mudou a palavra-passe Google): o alerta diz-o.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import http.server
import json
import secrets
import sys
import urllib.parse
import webbrowser
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_setup as rs  # noqa: E402

SCOPES = "openid email https://www.googleapis.com/auth/gmail.send"
ENV_FILE = rs.ROOT / ".env"


def client_creds() -> tuple[str, str]:
    cid, secret = rs.ENV.get("GMAIL_CLIENT_ID"), rs.ENV.get("GMAIL_CLIENT_SECRET")
    if cid and secret:
        return cid, secret
    print("O ID e o segredo estão em https://console.cloud.google.com/auth/clients?project=diomika-email → «site»\n"
          "(conta Google do Tomás). Se o segredo não aparecer: «Add secret» e usar o novo.")
    cid = getpass.getpass("GMAIL_CLIENT_ID (não aparece): ").strip()
    secret = getpass.getpass("GMAIL_CLIENT_SECRET (não aparece): ").strip()
    if not cid or not secret:
        sys.exit("Vazio: nada mudou.")
    with ENV_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\nGMAIL_CLIENT_ID={cid}\nGMAIL_CLIENT_SECRET={secret}\n")
    return cid, secret


def authorize(cid: str, secret: str, expected: str) -> str:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    got: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if q.get("state") == state:
                got.update(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Pode fechar esta janela e voltar ao Claude.".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent", "login_hint": expected, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    print("A abrir o browser: o cliente entra no Gmail dele e carrega em «Permitir».")
    webbrowser.open(url)
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if "error" in got:
        sys.exit(f"Autorização recusada: {got['error']}")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": cid, "client_secret": secret, "code": got["code"], "code_verifier": verifier,
        "redirect_uri": redirect, "grant_type": "authorization_code",
    }, timeout=30)
    r.raise_for_status()
    body = r.json()
    payload = body["id_token"].split(".")[1]
    email = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["email"].lower()
    if email != expected:
        sys.exit(f"Entrou com {email}, mas o site envia de {expected}. Nada foi gravado: repetir com a conta certa.")
    if "refresh_token" not in body:
        sys.exit("A Google não devolveu refresh token. Retirar o acesso em myaccount.google.com/permissions e repetir.")
    return body["refresh_token"]


def main() -> None:
    svc = rs.service() or sys.exit("Não há serviço no Render.")
    current = {v["envVar"]["key"]: v["envVar"].get("value", "") for v in rs.render(
        "GET", f"/services/{svc['id']}/env-vars?limit=100")}
    expected = (current.get("MAIL_FROM") or current.get("MAIL_USERNAME") or "").lower()
    if not expected:
        sys.exit("MAIL_FROM vazio no Render.")
    cid, secret = client_creds()
    token = authorize(cid, secret, expected)
    for name, value in (("GMAIL_CLIENT_ID", cid), ("GMAIL_CLIENT_SECRET", secret), ("GMAIL_REFRESH_TOKEN", token)):
        rs.render("PUT", f"/services/{svc['id']}/env-vars/{name}", json={"value": value})
    rs.render("POST", f"/services/{svc['id']}/deploys", json={})
    print(f"Autorizado ({expected}). A API reinicia em uns minutos e passa a enviar pela Gmail API.")


if __name__ == "__main__":
    main()
