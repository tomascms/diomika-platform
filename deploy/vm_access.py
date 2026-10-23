"""Acesso à VM da API por gcloud + IAP (a porta 22 só aceita o intervalo do IAP).

Valores por omissão = produção; sobrepor com GCP_PROJECT / GCP_ZONE / GCP_VM_NAME.
"""
from __future__ import annotations

import os
import shutil

PROJECT = os.getenv("GCP_PROJECT") or "diomika"
ZONE = os.getenv("GCP_ZONE") or "us-west1-a"
VM = os.getenv("GCP_VM_NAME") or "diomika-api"
APP_DIR = os.getenv("VM_APP_DIR") or "/home/deploy/diomika"

_COMMON = [f"--zone={ZONE}", f"--project={PROJECT}", "--tunnel-through-iap", "--quiet"]


def _gcloud() -> str:
    # No Windows o executável é gcloud.cmd; subprocess não o encontra só por "gcloud".
    return shutil.which("gcloud") or "gcloud"


def ssh(command: str) -> list[str]:
    return [_gcloud(), "compute", "ssh", VM, *_COMMON, "--command", command]


def scp(sources: list[str], remote_dest: str) -> list[str]:
    """remote_dest relativo à home do utilizador na VM, ou absoluto."""
    return [_gcloud(), "compute", "scp", *sources, f"{VM}:{remote_dest}", *_COMMON]
