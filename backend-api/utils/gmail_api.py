"""Envio pela Gmail API (HTTPS). O Render grátis bloqueia as portas SMTP, a 443 não.

Precisa de GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET e GMAIL_REFRESH_TOKEN (âmbito gmail.send), obtidos uma vez com
`python deploy/gmail_autorizar.py`. Sem eles, `email_sender` continua a usar SMTP.
"""
from __future__ import annotations

import base64
import os
import threading
import time
from email.message import EmailMessage

import httpx

from core.alerts import send_alert

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

_lock = threading.Lock()
_cache: dict[str, float | str] = {"token": "", "expires": 0.0}


class GmailAuthError(RuntimeError):
    """A autorização foi retirada ou caducou (ex.: mudança da palavra-passe Google). Precisa de novo «Permitir»."""


def configured() -> bool:
    return all(os.getenv(k) for k in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"))


def access_token(force: bool = False) -> str:
    """Token de acesso válido; renova com o refresh token quando falta menos de 1 minuto (ou `force`)."""
    with _lock:
        if not force and _cache["token"] and float(_cache["expires"]) - time.time() > 60:
            return str(_cache["token"])
        r = httpx.post(
            TOKEN_URL,
            data={
                "client_id": os.getenv("GMAIL_CLIENT_ID", ""),
                "client_secret": os.getenv("GMAIL_CLIENT_SECRET", ""),
                "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN", ""),
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        if r.status_code == 400 and r.json().get("error") == "invalid_grant":
            send_alert(
                "Email do site parado: a autorização Gmail caducou. Correr deploy/gmail_autorizar.py com o cliente.",
                severity="critical",
            )
            raise GmailAuthError("invalid_grant")
        r.raise_for_status()
        body = r.json()
        _cache["token"] = body["access_token"]
        _cache["expires"] = time.time() + int(body.get("expires_in", 3600))
        return str(_cache["token"])


def send(msg: EmailMessage) -> None:
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    r = httpx.post(SEND_URL, headers={"Authorization": f"Bearer {access_token()}"}, json={"raw": raw}, timeout=30)
    if r.status_code == 401:  # token revogado entre renovações: uma nova tentativa com token novo
        r = httpx.post(
            SEND_URL, headers={"Authorization": f"Bearer {access_token(force=True)}"}, json={"raw": raw}, timeout=30
        )
    r.raise_for_status()


_last_keepalive = 0.0


def keepalive(every_seconds: float = 86400) -> None:
    """Renova a autorização uma vez por dia: um refresh token sem uso 6 meses deixa de valer."""
    global _last_keepalive
    if not configured() or time.time() - _last_keepalive < every_seconds:
        return
    _last_keepalive = time.time()
    try:
        access_token(force=True)
    except Exception:  # o alerta já saiu em access_token; não pára o ciclo do email
        pass
