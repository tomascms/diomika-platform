"""Respostas públicas estáticas (robots, security.txt)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

SECURITY_CONTACT = "https://www.diomika.com/contacto"
SECURITY_POLICY = "https://www.diomika.com/privacidade"
STATUS_PAGE = "https://www.diomika.com/status.html"


def security_txt_body() -> str:
    expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT23:59:59.000Z")
    return (
        f"Contact: {SECURITY_CONTACT}\n"
        f"Expires: {expires}\n"
        "Preferred-Languages: pt, en\n"
        "Canonical: https://www.diomika.com/.well-known/security.txt\n"
        f"Policy: {SECURITY_POLICY}\n"
    )


ROBOTS_TXT = "User-agent: *\nDisallow: /\n"
