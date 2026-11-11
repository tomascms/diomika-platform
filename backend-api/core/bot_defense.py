"""Bot defense: User-Agent blocking e comportamento suspeito."""
import logging
import re
from typing import Optional

logger = logging.getLogger("diomika-api")

# Ferramentas reais de scraping/varrimento; o resto fica para a WAF da Cloudflare (API-11)
BLOCKED_BOT_PATTERNS = [
    # Automação de browsers e scrapers
    "scrapy",
    "selenium",
    "puppeteer",
    "playwright",
    "phantomjs",
    "headless",
    # Descarregadores de sites e clientes genéricos de scripts
    "httrack",
    "blackwidow",
    "80legs",
    "wget",
    "curl",
    "python-urllib",
    "libwww-perl",
    # Scanners de vulnerabilidades
    "sqlmap",
    "nikto",
    "masscan",
]


# Whitelist de bots conhecidos (crawlers respeitáveis)
ALLOWED_BOT_PATTERNS = [
    "googlebot",
    "bingbot",
    "slurp",  # Yahoo
    "baiduspider",
    "yandexbot",
    "duckduckbot",
    "slarp",
    "facebookexternalhit",
    "twitterbot",
    "linkedinbot",
    "whatsapp",
    "telegrambot",
    "discordbot",
    "slackbot",
    "applebot",
    "naver",
    "daum",
    "sogou",
    # Monitores de uptime (o UptimeRobot é o monitor deste projecto)
    "uptimerobot",
    "betteruptime",
    "pingdom",
    "statuscake",
]

# Cada padrão só conta no início de um "token" do User-Agent. Com substring
# simples, "obot" apanhava "UptimeRobot" e "lcc"/"pex"/"query" apanhavam texto
# inocente; "HeadlessChrome" e "curl/8.5" continuam bloqueados.
_BLOCKED_RE = re.compile(
    r"(?<![a-z0-9])(?:" + "|".join(re.escape(p) for p in BLOCKED_BOT_PATTERNS) + r")"
)


def is_bot_user_agent(user_agent: Optional[str]) -> bool:
    """
    Detecta se User-Agent é bot bloqueado.

    Retorna:
    - True se é bot bloqueado (deve rejeitar)
    - False se é bot permitido ou cliente normal
    """
    if not user_agent:
        return False

    ua_lower = str(user_agent).lower()

    # Whitelist first (bots respeitáveis são permitidos)
    if any(pattern in ua_lower for pattern in ALLOWED_BOT_PATTERNS):
        return False

    # Blacklist (bots agressivos)
    return _BLOCKED_RE.search(ua_lower) is not None


def log_bot_attempt(ip: str, user_agent: str, endpoint: str) -> None:
    """Log bot attempt para auditoria."""
    logger.warning(
        f"Bot attempt blocked: IP={ip}, UA={user_agent[:100]}, endpoint={endpoint}"
    )
