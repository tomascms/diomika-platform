#!/usr/bin/env python3
"""Portão de CI local (DEVOPS-07): os mesmos passos do .github/workflows/ci.yml, sem `make` e sem GitHub.

    python scripts/ci_local.py            # tudo (o que o hook pre-push corre)
    python scripts/ci_local.py api        # só a API (também: loja, backoffice)
    python scripts/ci_local.py --fast     # sem os e2e da loja

O plano gratuito do GitHub não protege ramos de repositórios privados; este portão é a regra.
Nenhum passo toca em produção: os testes isolam-se (tests/conftest.py) e o e2e usa a API simulada.
Fora daqui ficam o Trivy e o build da imagem Docker (precisam de Docker; correm no ci.yml).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NPX = shutil.which("npx") or "npx"
NPM = shutil.which("npm") or "npm"
NODE = shutil.which("node") or "node"
PY = sys.executable

# Mínimo de cobertura real (sem contar os testes). Só sobe: 62,9 % medido a 2026-11-02 (API-10).
COV_MIN = 62


def api_steps():
    # Sem `-p no:cacheprovider`/addopts do pytest.ini: igual ao ci.yml.
    return [
        ("API: bandit", [PY, "-m", "bandit", "-q", "-r", "backend-api", "-lll", "-iii", "-x", "backend-api/tests"], ROOT),
        (
            f"API: testes e cobertura >= {COV_MIN}%",
            [PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", "-o", "addopts=", "--cov=.", f"--cov-fail-under={COV_MIN}"],
            ROOT / "backend-api",
        ),
    ]


def loja_steps(e2e: bool):
    fw = ROOT / "frontend-web"
    steps = [
        ("Loja: oxlint", [NPX, "oxlint", "src", "functions"], fw),
        ("Loja: eslint", [NPX, "eslint", "src", "functions"], fw),
        ("Loja: testes (node --test)", [NPM, "test"], fw),
        (
            "Loja: build de produção",
            [NPM, "run", "build"],
            fw,
            {"VITE_API_BASE_URL": "https://api.diomika.com", "VITE_IMAGE_TRANSFORM": "0"},
        ),
        ("Loja: sem secrets no bundle", [PY, "deploy/verify_bundle_secrets.py"], ROOT),
        ("Loja: CSP", [PY, "deploy/verify_csp.py"], ROOT),
    ]
    if e2e:
        steps.append(("Loja: e2e local (API simulada)", [NPM, "run", "test:e2e:local"], fw))
    return steps


def backoffice_steps():
    bo = ROOT / "backoffice-desktop"
    node_check = [
        (f"Backoffice: node --check {p.name}", [NODE, "--check", str(p)], bo)
        for p in sorted([*(bo / "electron").glob("*.cjs"), *(bo / "scripts").glob("*.cjs")])
    ]
    return [
        ("Backoffice: build", [NPX, "vite", "build"], bo),
        ("Backoffice: oxlint", [NPX, "--yes", "oxlint@1.60.0", "src", "electron", "scripts"], bo),
        ("Backoffice: testes (node --test)", [NPM, "test"], bo),
        *node_check,
    ]


def run(step) -> bool:
    name, cmd, cwd, *extra = step
    env = {**os.environ, **(extra[0] if extra else {})}
    # O .env da raiz é de produção: nenhum passo recebe a URL da API real.
    env.pop("API_BASE_URL", None)
    print(f"\n=== {name}", flush=True)
    t = time.time()
    # shell=True no Windows para os .cmd do npm/npx; os argumentos são fixos acima.
    code = subprocess.call(cmd, cwd=cwd, env=env, shell=(os.name == "nt"))  # nosec B602
    print(f"--- {name}: {'ok' if code == 0 else 'FALHOU'} ({time.time() - t:.0f}s)", flush=True)
    return code == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parts", nargs="*", choices=["api", "loja", "backoffice"])
    ap.add_argument("--fast", action="store_true", help="sem os e2e da loja")
    args = ap.parse_args()
    parts = args.parts or ["api", "loja", "backoffice"]
    steps = []
    if "api" in parts:
        steps += api_steps()
    if "loja" in parts:
        steps += loja_steps(e2e=not args.fast)
    if "backoffice" in parts:
        steps += backoffice_steps()
    failed = [s[0] for s in steps if not run(s)]
    print("\n" + ("CI local: tudo verde." if not failed else "CI local FALHOU: " + "; ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
