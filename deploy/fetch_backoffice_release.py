#!/usr/bin/env python3
"""Descarrega instaladores do GitHub Release e prepara pasta cliente limpa."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = "backoffice-cliente-latest"
BASE = f"https://github.com/tomascms/diomika/releases/download/{TAG}"
VERSION = "1.0.0"
FILES = [
    f"Diomika-Backoffice-{VERSION}-windows.zip",
    f"Diomika-Backoffice-{VERSION}-mac.dmg",
    f"Diomika-Backoffice-{VERSION}-linux.AppImage",
]
DEST_DIRS = [
    ROOT / "cliente-backoffice",
    ROOT.parent / "cliente-backoffice",
]


def download(url: str) -> bytes:
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": "diomika-fetch-release"})
    with urlopen(req, timeout=300) as resp:
        return resp.read()


def main() -> int:
    ok = 0
    for name in FILES:
        url = f"{BASE}/{name}"
        print(f"Descarregar {name} …")
        try:
            data = download(url)
        except Exception as exc:
            print(f"  AVISO: {exc}")
            continue
        for dest in DEST_DIRS:
            dest.mkdir(parents=True, exist_ok=True)
            out = dest / name
            out.write_bytes(data)
            print(f"  OK {out} ({len(data)} bytes)")
        ok += 1

    prep = ROOT / "backoffice-desktop" / "scripts" / "prepare-cliente-pack.cjs"
    if prep.is_file():
        print("\nA preparar pacote cliente (limpeza + atalhos)…")
        subprocess.run(["node", str(prep)], cwd=prep.parent.parent, check=False)

    if ok == 0:
        print("ERRO: nenhum ficheiro descarregado — aguarda o workflow Backoffice release.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
