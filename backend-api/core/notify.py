"""Email de notificação interna (contacto, orçamentos)."""
from __future__ import annotations

import os


def contact_notify_email() -> str | None:
    return (
        os.getenv("CONTACT_EMAIL")
        or os.getenv("CONTACT_NOTIFY_EMAIL")
        or os.getenv("MAIL_FROM")
        or os.getenv("MAIL_USERNAME")
    )
