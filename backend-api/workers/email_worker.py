import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import time
import os
import re
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from core.env_loader import load_project_env
from core.database import get_db
from core import state_store
from paths import BACKEND_ROOT, heartbeat_path
from utils.email_body import strip_email_quotes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("email-worker")

load_project_env()

IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = (os.getenv("MAIL_FROM") or MAIL_USERNAME or "").lower()

REF_PATTERN = re.compile(r"\[Ref:\s*#(\w+)\]", re.IGNORECASE)
# Em data/ (volume): fora dele perdia-se a cada deploy e os últimos 50 emails de cada pasta eram
# reprocessados (o _is_duplicate evitava duplicados, mas com ~100 consultas à BD desnecessárias).
STATE_FILE = BACKEND_ROOT / "data" / ".email_worker_state.json"

supabase = get_db()


def _load_state() -> set[str]:
    if state_store._supabase():
        return set(state_store.load("email_worker_state", {}).get("processed_keys", []))
    if not STATE_FILE.exists():
        return set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("processed_keys", []))
    except Exception:
        return set()


def _save_state(keys: set[str]) -> None:
    trimmed = sorted(keys)[-5000:]
    if state_store._supabase():
        state_store.save("email_worker_state", {"processed_keys": trimmed})
        return
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"processed_keys": trimmed}, indent=2),
        encoding="utf-8",
    )


def _decode_header(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        raw = payload.decode(charset, errors="replace")
                        body = re.sub(r"<[^>]+>", " ", raw)
                        break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")

    body = strip_email_quotes(body)
    return body


def _find_ref(subject: str, body: str) -> str | None:
    for text in (subject or "", body or ""):
        match = REF_PATTERN.search(text)
        if match:
            return match.group(1)
    return None


def _parse_sender(from_addr: str) -> str:
    from_addr = from_addr or ""
    m = re.search(r"<([^>]+)>", from_addr)
    return (m.group(1) if m else from_addr.split()[-1]).strip().lower()


def _find_sent_folder(mail) -> str | None:
    for raw in mail.list()[1]:
        line = raw.decode() if isinstance(raw, bytes) else raw
        if "\\Sent" in line:
            m = re.search(r'"([^"]+)"\s*$', line)
            if m:
                return m.group(1)
    return None


def _resolve_message_id(ref_prefix: str) -> str | None:
    ref_prefix = ref_prefix.lower()
    # `id` é uuid: LIKE não existe para uuid (falhava sempre). O prefixo [Ref: #xxxxxxxx]
    # são os primeiros 8 hex, por isso um intervalo na chave primária dá a mesma resposta.
    try:
        if not re.fullmatch(r"[0-9a-f]{8}", ref_prefix):
            return _scan_recent(ref_prefix)
        res = (
            supabase.table("contact_messages")
            .select("id")
            .gte("id", f"{ref_prefix}-0000-0000-0000-000000000000")
            .lte("id", f"{ref_prefix}-ffff-ffff-ffff-ffffffffffff")
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]
    except Exception:
        # Sem isto a resposta do cliente ficava por ligar à conversa sem rasto.
        logger.warning("Falha a procurar a conversa %s", ref_prefix, exc_info=True)
    return _scan_recent(ref_prefix)


def _scan_recent(ref_prefix: str) -> str | None:
    res = (
        supabase.table("contact_messages")
        .select("id")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    for row in res.data or []:
        if str(row["id"]).lower().startswith(ref_prefix):
            return row["id"]
    return None


def _is_duplicate(message_id: str, sender_email: str, body: str) -> bool:
    res = (
        supabase.table("message_history")
        .select("body")
        .eq("message_id", message_id)
        .eq("sender_email", sender_email)
        .execute()
    )
    snippet = body.strip()[:500]
    for row in res.data or []:
        if (row.get("body") or "").strip()[:500] == snippet:
            return True
    return False


def _is_vendor(sender_email: str) -> bool:
    mine = parseaddr(MAIL_FROM)[1].lower()
    return bool(mine) and parseaddr(sender_email)[1].lower() == mine


def _sender_allowed(message_id: str, sender_email: str) -> bool:
    """Só o email do próprio contacto ou o nosso remetente entram na conversa."""
    if _is_vendor(sender_email):
        return True
    res = supabase.table("contact_messages").select("email").eq("id", message_id).limit(1).execute()
    contact = ((res.data or [{}])[0].get("email") or "").strip().lower()
    return bool(contact) and parseaddr(sender_email)[1].lower() == contact


def _record_message(
    message_id: str,
    sender_email: str,
    body: str,
    state_key: str,
    processed: set[str],
) -> bool:
    if not body or _is_duplicate(message_id, sender_email, body):
        processed.add(state_key)
        return False
    if not _sender_allowed(message_id, sender_email):
        # Um [Ref: #xxxxxxxx] adivinhado não dá a um estranho voz na conversa (SEG-20).
        logger.warning("Resposta ignorada: remetente alheio à conversa %s", message_id[:8])
        processed.add(state_key)
        return False

    supabase.table("message_history").insert(
        {
            "message_id": message_id,
            "sender_email": sender_email,
            "body": body,
        }
    ).execute()

    last_sender = "vendor" if _is_vendor(sender_email) else "client"
    supabase.table("contact_messages").update(
        {
            "last_sender": last_sender,
            "status": "Em conversa",
            "lida": False,
        }
    ).eq("id", message_id).execute()

    processed.add(state_key)
    logger.info(
        "Mensagem registada (%s) conversa %s de %s",
        last_sender,
        message_id[:8],
        sender_email,
    )
    return True


def _search_ref_uids(mail) -> list[str]:
    """UIDs (estáveis entre sessões) das mensagens com «Ref: #» — a pesquisa corre no servidor."""
    status, data = mail.uid("SEARCH", None, "TEXT", '"Ref: #"')
    if status == "OK" and data and data[0]:
        return [u.decode() if isinstance(u, bytes) else str(u) for u in data[0].split()]
    return []


def _process_folder(mail, folder: str, processed: set[str]) -> int:
    status, _ = mail.select(f'"{folder}"', readonly=False)
    if status != "OK":
        logger.warning("Nao foi possivel abrir pasta %s", folder)
        return 0

    uids = _search_ref_uids(mail)
    if not uids:
        return 0

    recorded = 0
    for uid in uids[-50:]:
        state_key = f"{folder}:{uid}"
        # Antes do download: o ciclo de 30 s descarregava as últimas 50 mensagens de cada pasta
        # (~2 GB/dia, perto do limite IMAP do Gmail e com tráfego de saída pago na VM).
        if state_key in processed:
            continue

        # BODY.PEEK[]: RFC822 marca \Seen ao descarregar e apagava o «não lido» das notificações do dono (API-06).
        status, data = mail.uid("FETCH", uid, "(BODY.PEEK[])")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            continue

        msg = email.message_from_bytes(data[0][1])
        subject = _decode_header(msg.get("Subject", ""))
        body = _extract_body(msg)
        ref_prefix = _find_ref(subject, body)
        if not ref_prefix:
            processed.add(state_key)  # sem referência válida: não voltar a descarregar
            continue

        message_id = _resolve_message_id(ref_prefix)
        if not message_id:
            logger.warning("Conversa nao encontrada para Ref #%s", ref_prefix)
            processed.add(state_key)
            continue

        sender_email = _parse_sender(msg.get("From", ""))

        if subject.startswith("[Diomika]") and not subject.lower().startswith("re:"):
            processed.add(state_key)
            continue

        reply_body = body
        if not reply_body and subject.lower().startswith("re:"):
            reply_body = subject

        if _record_message(message_id, sender_email, reply_body, state_key, processed):
            recorded += 1
            mail.uid("STORE", uid, "+FLAGS", r"\Seen")

    return recorded


def process_inbox():
    if not all([IMAP_SERVER, MAIL_USERNAME, MAIL_PASSWORD]):
        logger.warning("IMAP nao configurado — worker em espera.")
        return

    processed = _load_state()
    mail = None
    try:
        # Sem timeout, uma leitura num socket meio-morto bloqueava a thread para sempre (API-01);
        # com ele a excepção cai no except abaixo e o ciclo seguinte volta a ligar.
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        mail.login(MAIL_USERNAME, MAIL_PASSWORD)

        total = 0
        total += _process_folder(mail, "INBOX", processed)

        sent_folder = _find_sent_folder(mail)
        if sent_folder:
            total += _process_folder(mail, sent_folder, processed)
        else:
            logger.warning("Pasta de enviados nao encontrada")

        _save_state(processed)

        heartbeat = heartbeat_path(BACKEND_ROOT)
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        heartbeat.write_text(
            json.dumps({"last_poll": datetime.now(timezone.utc).isoformat(), "recorded": total}),
            encoding="utf-8",
        )

        if total:
            logger.info("%d mensagem(ns) nova(s) registada(s)", total)
    except (imaplib.IMAP4.abort, imaplib.IMAP4.error, ConnectionResetError, OSError, TimeoutError) as e:
        logger.warning("IMAP ligação perdida (reconecta no próximo ciclo): %s", e)
    except Exception as e:
        msg = str(e).lower()
        if "socket error" in msg or "eof" in msg or "broken pipe" in msg:
            logger.warning("IMAP ligação perdida (reconecta no próximo ciclo): %s", e)
        else:
            logger.exception("Erro ao processar email: %s", e)
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass


if __name__ == "__main__":
    logger.info("Email Worker ativo — INBOX + Enviados, a cada 30 segundos")
    while True:
        process_inbox()
        time.sleep(30)
