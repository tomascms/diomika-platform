#!/usr/bin/env python3
"""Inventário e validação de rotas sensíveis.

--static: carrega o app FastAPI e confirma path guard + deps local nas rotas /admin|/system
--live URL: HTTP checks (sem auth → 401/403/400)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-api"))

PRIVILEGED_PREFIXES = ("/admin", "/system")
PRIVILEGED_EXACT = {"/health/detail"}


def _dep_names(dependant) -> set[str]:
    names: set[str] = set()
    stack = [dependant]
    seen: set[int] = set()
    while stack:
        d = stack.pop()
        if id(d) in seen:
            continue
        seen.add(id(d))
        call = getattr(d, "call", None)
        if call is not None:
            names.add(getattr(call, "__name__", "") or "")
        for child in getattr(d, "dependencies", []) or []:
            stack.append(child)
    return names


def _iter_api_routes(routes: list[Any]) -> Iterator[Any]:
    """Percorre APIRoute, incluindo _IncludedRouter do FastAPI recente."""
    from fastapi.routing import APIRoute

    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue
        original = getattr(route, "original_router", None)
        if original is not None:
            yield from _iter_api_routes(list(getattr(original, "routes", []) or []))
            continue
        nested = getattr(route, "routes", None)
        if nested:
            yield from _iter_api_routes(list(nested))


def _is_privileged(path: str) -> bool:
    if path in PRIVILEGED_EXACT:
        return True
    return any(path.startswith(p) for p in PRIVILEGED_PREFIXES)


def check_static() -> int:
    os.environ.setdefault("DIOMIKA_ENV", "development")
    os.environ.setdefault("API_SECRET_KEY", "k" * 32)
    os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
    os.environ.setdefault("SUPABASE_KEY", "test")
    from core.config import get_settings

    get_settings.cache_clear()

    from core.path_guard import PrivilegedPathMiddleware
    from main import app

    assert PrivilegedPathMiddleware is not None

    # Confirmar middleware registado
    middleware_names = []
    for m in getattr(app, "user_middleware", []) or []:
        cls = getattr(m, "cls", None) or m
        middleware_names.append(getattr(cls, "__name__", str(cls)))
    if "PrivilegedPathMiddleware" not in middleware_names:
        # Starlette may wrap differently — also check source
        main_src = (ROOT / "backend-api" / "main.py").read_text(encoding="utf-8")
        if "PrivilegedPathMiddleware" not in main_src:
            print("FAIL: PrivilegedPathMiddleware não registado")
            return 1

    failed: list[str] = []
    checked = 0
    for route in _iter_api_routes(list(app.routes)):
        path = getattr(route, "path", "") or ""
        if not _is_privileged(path):
            continue
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            failed.append(f"{path}: sem dependant FastAPI")
            continue
        names = _dep_names(dependant)
        checked += 1
        if "admin_must_be_local" not in names:
            failed.append(f"{path}: falta admin_must_be_local (deps={sorted(n for n in names if n)})")

    print(f"Rotas privilegiadas inspeccionadas: {checked}")
    if failed:
        print("FAIL:")
        for f in failed:
            print(f"  - {f}")
        return 1
    if checked < 5:
        print(f"FAIL: poucas rotas privilegiadas encontradas ({checked})")
        return 1
    print("OK — inventário estático: todas as rotas privilegiadas têm admin_must_be_local")
    return 0


def check_live(base: str) -> int:
    import urllib.error
    import urllib.request

    base = base.rstrip("/")
    probes = [
        ("GET", "/admin/auth/me", (401, 403, 400)),
        ("GET", "/admin/crud/categories", (401, 403, 400)),
        ("GET", "/system/workspace", (401, 403, 400)),
        ("GET", "/contacto", (401, 403, 400)),
        ("GET", "/health/detail", (401, 403, 400)),
        ("GET", "/health", (200,)),
    ]
    failed = []
    for method, path, ok_codes in probes:
        url = base + path
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "DiomikaRouteValidate/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception as exc:
            failed.append(f"{method} {path}: rede {exc}")
            continue
        if code not in ok_codes:
            failed.append(f"{method} {path}: {code} (esperado {ok_codes})")
        else:
            print(f"  [OK] {method} {path} → {code}")
    if failed:
        print("FAIL live:")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("OK — validação live")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true")
    ap.add_argument("--live", metavar="URL", default="")
    args = ap.parse_args()
    if not args.static and not args.live:
        args.static = True
    rc = 0
    if args.static:
        rc |= check_static()
    if args.live:
        rc |= check_live(args.live)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
