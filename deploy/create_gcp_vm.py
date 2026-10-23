#!/usr/bin/env python3
"""
Cria VM GCP Always Free (e2-micro, us-central1) para a API Diomika.

Requisitos:
  1) Google Cloud SDK instalado (gcloud)
  2) gcloud auth login
  3) Chave SSH em %USERPROFILE%\\.ssh\\id_ed25519.pub

Uso:
  python deploy/create_gcp_vm.py
  python deploy/create_gcp_vm.py --project diomika --zone us-central1-a
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBKEY = Path.home() / ".ssh" / "id_ed25519.pub"


def find_gcloud() -> str:
    exe = shutil.which("gcloud")
    if exe:
        return exe
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "google-cloud-sdk" / "bin" / "gcloud.cmd",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Cloud SDK" / "google-cloud-sdk" / "bin" / "gcloud.cmd",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Google" / "Cloud SDK" / "google-cloud-sdk" / "bin" / "gcloud.cmd",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    raise SystemExit(
        "ERRO: gcloud nao encontrado.\n"
        "  winget install -e --id Google.CloudSDK --source winget\n"
        "  Depois: gcloud auth login && gcloud config set project diomika"
    )


def run(gcloud: str, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = [gcloud, *args]
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT") or "diomika")
    parser.add_argument("--zone", default="us-central1-a")
    parser.add_argument("--name", default="diomika-api")
    parser.add_argument("--user", default=os.getenv("USERNAME") or "diomika")
    args = parser.parse_args()

    if not PUBKEY.is_file():
        raise SystemExit(f"ERRO: falta chave publica {PUBKEY}")

    pubkey = PUBKEY.read_text(encoding="utf-8").strip()
    gcloud = find_gcloud()

    # Projeto + APIs
    run(gcloud, ["config", "set", "project", args.project])
    run(gcloud, ["services", "enable", "compute.googleapis.com"], check=False)

    # Já existe?
    listed = run(
        gcloud,
        [
            "compute",
            "instances",
            "list",
            f"--project={args.project}",
            f"--filter=name={args.name}",
            "--format=json",
        ],
        check=False,
    )
    existing = []
    try:
        existing = json.loads(listed.stdout or "[]")
    except json.JSONDecodeError:
        existing = []

    if not existing:
        print("\n=== A criar e2-micro Always Free (us-central1) ===\n")
        print("IMPORTANTE: NAO cliques Activate (conta paga). Fica so e2-micro.\n")
        create = run(
            gcloud,
            [
                "compute",
                "instances",
                "create",
                args.name,
                f"--project={args.project}",
                f"--zone={args.zone}",
                "--machine-type=e2-micro",
                "--image-family=ubuntu-2204-lts",
                "--image-project=ubuntu-os-cloud",
                "--boot-disk-size=30GB",
                "--boot-disk-type=pd-standard",
                f"--metadata=ssh-keys={args.user}:{pubkey}",
                "--tags=diomika-api",
                "--format=json",
            ],
            check=False,
        )
        if create.returncode != 0:
            print(create.stderr or create.stdout)
            raise SystemExit("ERRO a criar VM — ve mensagem acima (quota / billing / Free Trial)")
        print(create.stdout)
    else:
        print(f"OK VM {args.name} ja existe — a reutilizar")

    ip_proc = run(
        gcloud,
        [
            "compute",
            "instances",
            "describe",
            args.name,
            f"--project={args.project}",
            f"--zone={args.zone}",
            "--format=get(networkInterfaces[0].accessConfigs[0].natIP)",
        ],
    )
    ip = (ip_proc.stdout or "").strip()
    if not ip or not re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
        raise SystemExit("ERRO: nao consegui ler External IP da VM")

    ssh_target = f"{args.user}@{ip}"
    env_path = ROOT / ".env"
    text = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
    line = f"REMOTE_VM_SSH={ssh_target}"
    if re.search(r"^REMOTE_VM_SSH=.*$", text, flags=re.M):
        text = re.sub(r"^REMOTE_VM_SSH=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip() + f"\n\n# GCP e2-micro Always Free\n{line}\n"
    env_path.write_text(text, encoding="utf-8")

    print("\nOK VM pronta")
    print(f"  External IP: {ip}")
    print(f"  REMOTE_VM_SSH={ssh_target}  (gravado no .env)")
    print("\nProximo passo:")
    print("  Deploy: docs/runbook.md secção 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
