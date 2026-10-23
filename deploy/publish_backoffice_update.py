#!/usr/bin/env python3
"""Publica uma versão do backoffice no feed de actualizações automáticas.

Copia de backoffice-desktop/release/ (e de pastas extra, ex. artefactos do CI)
para a VM, em backend-api/data/desktop-updates/ — servido pela API em
https://api.diomika.com/system/desktop-updates/ (só com o gate desktop).

Os manifestos (latest*.yml) são enviados no fim, para nenhum cliente ver um
manifesto a apontar para um instalador ainda a meio do envio. Mantém a versão
anterior (as actualizações diferenciais usam o .blockmap dela).

Uso:
  python deploy/publish_backoffice_update.py
  python deploy/publish_backoffice_update.py --extra-dir C:/caminho/artefactos-ci
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_access  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "backoffice-desktop" / "release"
# Relativo à home: o scp (SFTP) não expande $HOME; o ssh começa na home.
REMOTE_DIR = "diomika/backend-api/data/desktop-updates"
FEED = "https://api.diomika.com/system/desktop-updates"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
        if m:
            env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return env


def collect(version: str, dirs: list[Path]) -> tuple[list[Path], list[Path]]:
    binaries: dict[str, Path] = {}
    manifests: dict[str, Path] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            if p.name in ("latest.yml", "latest-linux.yml", "latest-mac.yml"):
                if f"version: {version}" in p.read_text(encoding="utf-8", errors="ignore"):
                    manifests.setdefault(p.name, p)
            elif p.name.startswith(f"Diomika-Backoffice-{version}-") and p.suffix in (".exe", ".blockmap", ".AppImage", ".dmg", ".zip"):
                if "-windows." in p.name and p.suffix in (".exe", ".zip"):
                    continue  # portátil/zip não são usados pelo actualizador
                binaries.setdefault(p.name, p)
    return list(binaries.values()), list(manifests.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra-dir", action="append", default=[], help="pasta extra com artefactos (ex. do CI)")
    args = parser.parse_args()

    version = json.loads((ROOT / "backoffice-desktop" / "package.json").read_text(encoding="utf-8"))["version"]
    binaries, manifests = collect(version, [RELEASE, *map(Path, args.extra_dir)])
    if not manifests:
        print(f"ERRO: nenhum latest*.yml da versão {version} — faça o build primeiro (npm run dist:win).")
        return 1
    for m in manifests:
        for ref in re.findall(r"^\s*(?:-\s*)?(?:url|path):\s*(\S+)", m.read_text(encoding="utf-8"), re.M):
            if ref not in {b.name for b in binaries}:
                print(f"ERRO: {m.name} refere {ref}, que não foi encontrado.")
                return 1

    env = load_env()
    gate = env.get("DIOMIKA_DESKTOP_GATE", "").strip()
    if not gate:
        print("ERRO: DIOMIKA_DESKTOP_GATE é necessário no .env")
        return 1

    prep = f"set -e; sudo mkdir -p {REMOTE_DIR}; sudo chown $(id -u):$(id -g) {REMOTE_DIR}; mkdir -p {REMOTE_DIR}/.incoming"
    if subprocess.run(vm_access.ssh(prep)).returncode != 0:
        return 1

    for group, label in ((binaries, "binários"), (manifests, "manifestos")):
        print(f"=== A enviar {label}: {', '.join(p.name for p in group)}")
        if group and subprocess.run(vm_access.scp([str(p) for p in group], f"{REMOTE_DIR}/.incoming/")).returncode != 0:
            return 1
        names = " ".join(p.name for p in group)
        move = f"set -e; cd {REMOTE_DIR}; for f in {names}; do mv -f .incoming/$f $f; done"
        if group and subprocess.run(vm_access.ssh(move)).returncode != 0:
            return 1

    # Limpa versões com mais de uma geração (mantém a actual e a anterior).
    prune = (
        f"cd {REMOTE_DIR}; "
        "ls Diomika-Backoffice-*-* 2>/dev/null | sed -E 's/^Diomika-Backoffice-([0-9.]+)-.*/\\1/' | sort -uV | head -n -2 "
        "| while read v; do rm -f Diomika-Backoffice-$v-*; echo \"removida versão $v\"; done; rmdir .incoming 2>/dev/null; ls -la"
    )
    subprocess.run(vm_access.ssh(prune))

    req = urllib.request.Request(
        f"{FEED}/{manifests[0].name}",
        headers={"x-diomika-desktop": gate, "User-Agent": f"DiomikaBackoffice/{version}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    ok = f"version: {version}" in body
    print(f"Feed público ({manifests[0].name}): {'OK' if ok else 'INESPERADO'} — versão {version}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
