#!/usr/bin/env python3
"""Garante fronteiras de segurança: Depends nos routers + middleware path-level."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / "backend-api" / "routes"
MAIN = ROOT / "backend-api" / "main.py"
PATH_GUARD = ROOT / "backend-api" / "core" / "path_guard.py"

MUST_MENTION_AUTH = {
    "admin.py": ("require_admin", "admin_must_be_local"),
    "admin_crud.py": ("require_", "admin_must_be_local"),
    "admin_auth.py": ("admin_must_be_local",),
    "system.py": ("require_", "admin_must_be_local"),
    "encomendas.py": ("require_pedidos", "admin_must_be_local"),
    "contact.py": ("require_mensagens", "admin_must_be_local", "verify_turnstile"),
    "orcamentos.py": ("require_pedidos", "admin_must_be_local", "verify_turnstile"),
    "privacy.py": ("require_admin", "admin_must_be_local", "erase"),
}

# Routers sensíveis: APIRouter(...) deve declarar dependencies com admin_must_be_local
ROUTER_MUST_HAVE_LOCAL_DEP = {
    "admin.py",
    "admin_crud.py",
    "admin_auth.py",
    "system.py",
    "encomendas.py",
    "privacy.py",
}


def _router_has_local_dep(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "APIRouter":
            continue
        for kw in node.keywords:
            if kw.arg != "dependencies":
                continue
            src = ast.unparse(kw.value) if hasattr(ast, "unparse") else ""
            if "admin_must_be_local" in src:
                return True
    return False


def main() -> int:
    failed: list[str] = []

    if not PATH_GUARD.is_file():
        failed.append("core/path_guard.py em falta")
    main_txt = MAIN.read_text(encoding="utf-8") if MAIN.is_file() else ""
    if "PrivilegedPathMiddleware" not in main_txt:
        failed.append("main.py: falta PrivilegedPathMiddleware (fail-closed path-level)")
    if "SECURITY_LOCKDOWN" not in (PATH_GUARD.read_text(encoding="utf-8") if PATH_GUARD.is_file() else ""):
        failed.append("path_guard.py: falta SECURITY_LOCKDOWN")

    for name, needles in MUST_MENTION_AUTH.items():
        path = ROUTES / name
        if not path.is_file():
            failed.append(f"em falta: {name}")
            continue
        text = path.read_text(encoding="utf-8")
        for n in needles:
            if n not in text:
                failed.append(f"{name}: falta '{n}'")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            failed.append(f"{name}: syntax {exc}")
            continue
        if name in ROUTER_MUST_HAVE_LOCAL_DEP and not _router_has_local_dep(tree):
            failed.append(f"{name}: APIRouter sem dependencies=[Depends(admin_must_be_local)]")

    # Nenhum ADMIN_ALLOW_REMOTE como escape activo em local_only
    local_only = (ROOT / "backend-api" / "core" / "local_only.py").read_text(encoding="utf-8")
    if "ADMIN_ALLOW_REMOTE" in local_only and "os.getenv(\"ADMIN_ALLOW_REMOTE\")" in local_only:
        failed.append("local_only.py: ADMIN_ALLOW_REMOTE ainda é lido como escape")

    if failed:
        print("FAIL route guards:")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("OK — route guards + path middleware + sem escape remoto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
