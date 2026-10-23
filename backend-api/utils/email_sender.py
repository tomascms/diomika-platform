import logging
import asyncio
import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from core.resilience import async_retry_with_backoff, get_smtp_breaker

logger = logging.getLogger("diomika-api")


async def send_email_async(
    to_email: str,
    subject: str,
    body: str,
    reply_to: str | None = None,
    thread_id: str | None = None,
) -> bool:
    """Envia email via SMTP com retries e circuit breaker.

    thread_id: id estável da conversa; o cliente de email agrupa as respostas.
    """
    mail_server = os.getenv("MAIL_SERVER")
    mail_user = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_from = os.getenv("MAIL_FROM") or mail_user
    mail_port = int(os.getenv("MAIL_PORT", "587"))

    if not all([mail_server, mail_user, mail_password, mail_from]):
        logger.warning(
            "Email nao configurado: defina MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM"
        )
        return False

    def _send() -> None:
        msg = EmailMessage()
        msg["From"] = mail_from
        msg["To"] = to_email
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        domain = (mail_from.rsplit("@", 1)[-1] or "diomika.com").strip(">")
        msg["Message-ID"] = make_msgid(domain=domain)
        if thread_id:
            root = f"<contacto-{thread_id}@{domain}>"
            msg["In-Reply-To"] = root
            msg["References"] = root
        msg.set_content(body, charset="utf-8")

        with smtplib.SMTP(
            mail_server, mail_port, timeout=30, local_hostname="localhost"
        ) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(mail_user, mail_password)
            server.send_message(msg)

    breaker = get_smtp_breaker()

    async def _attempt():
        await asyncio.to_thread(_send)
        return True

    try:
        await async_retry_with_backoff(
            _attempt,
            max_attempts=3,
            base_delay=1.0,
            operation=f"SMTP->{to_email}",
            breaker=breaker,
        )
        logger.info("Email enviado para %s", to_email)
        return True
    except Exception as e:
        logger.error("Erro ao enviar email: %s", e)
        return False
