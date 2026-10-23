#!/usr/bin/env python3
"""Garante CSP da loja sem unsafe-inline / unsafe-eval."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ROOT / "frontend-web" / "public" / "_headers"
INDEX = ROOT / "frontend-web" / "index.html"
FORBIDDEN = ("'unsafe-inline'", "'unsafe-eval'", "data:text/html")


def main() -> int:
    text = HEADERS.read_text(encoding="utf-8")
    m = re.search(r"Content-Security-Policy:\s*(.+)", text)
    if not m:
        print("FAIL: Content-Security-Policy em falta em frontend-web/public/_headers")
        return 1
    csp = m.group(1).strip()
    bad = [tok for tok in FORBIDDEN if tok in csp]
    if bad:
        print(f"FAIL: CSP contém {', '.join(bad)}")
        return 1
    if "style-src 'self'" not in csp and "style-src 'self';" not in csp:
        # allow style-src 'self' ... with more sources after
        if not re.search(r"style-src\s+'self'", csp):
            print("FAIL: style-src deve incluir 'self' sem unsafe-inline")
            return 1
    if "fonts.googleapis.com" in csp or "fonts.gstatic.com" in csp:
        print("FAIL: CSP ainda aponta para Google Fonts — usa font self-host")
        return 1

    # O middleware do Pages sobrepõe-se ao _headers: tem de servir a mesma CSP.
    mw = (ROOT / "frontend-web" / "functions" / "_middleware.js").read_text(encoding="utf-8")
    m_mw = re.search(r'const CSP =\s*"([^"]+)"', mw)
    prod = re.search(r"Content-Security-Policy:\s*(.+)", (ROOT / "frontend-web" / "public" / "_headers.production").read_text(encoding="utf-8"))
    if not m_mw or not prod or m_mw.group(1).strip() != prod.group(1).strip():
        print("FAIL: CSP de functions/_middleware.js diferente de public/_headers.production")
        return 1
    if "https://challenges.cloudflare.com" not in m_mw.group(1).split("script-src", 1)[1].split(";")[0]:
        print("FAIL: script-src sem challenges.cloudflare.com — o Turnstile fica bloqueado")
        return 1

    idx = INDEX.read_text(encoding="utf-8")
    if "fonts.googleapis.com" in idx or "fonts.gstatic.com" in idx:
        print("FAIL: index.html ainda carrega Google Fonts (quebra CSP sem unsafe-inline)")
        return 1

    src = ROOT / "frontend-web" / "src"
    for path in src.rglob("*.vue"):
        body = path.read_text(encoding="utf-8")
        if re.search(r'\sstyle\s*=\s*"', body) or re.search(r":style\s*=", body):
            print(f"FAIL: estilo inline em {path.relative_to(ROOT)} — usa classes CSS")
            return 1
        if "v-html" in body:
            print(f"FAIL: v-html em {path.relative_to(ROOT)}")
            return 1

    print("OK: CSP sem unsafe-inline/eval; sem Google Fonts; sem style/v-html inline no Vue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
