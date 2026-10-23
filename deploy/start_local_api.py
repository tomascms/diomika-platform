#!/usr/bin/env python3
"""Arranca API local em 127.0.0.1:8001 (só developers / tunnel beta).

O backoffice do cliente usa a API cloud — não precisa deste script.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend-api"
HOST = "127.0.0.1"
PORT = int(os.getenv("DIOMIKA_API_PORT") or "8001")
HEALTH = f"http://{HOST}:{PORT}/health"


def health_ok() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=2) as r:
            return 200 <= getattr(r, "status", 200) < 500
    except Exception:
        return False


def port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((HOST, PORT)) == 0


def main() -> int:
    sys.path.insert(0, str(BACKEND))
    os.chdir(ROOT)
    try:
        from core.env_loader import load_project_env

        load_project_env()
    except Exception:
        pass

    if health_ok():
        print(f"OK — API já responde em {HEALTH}")
        return 0

    if port_open():
        print(f"ERRO — porta {PORT} ocupada mas /health falha. Liberte a porta e tente de novo.")
        return 1

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND) + os.pathsep + env.get("PYTHONPATH", "")
    # Workers embutidos úteis em local single-process
    env.setdefault("RUN_EMBEDDED_WORKERS", "true")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
        "--app-dir",
        str(BACKEND),
    ]
    print(f"A arrancar API em {HOST}:{PORT} ...")
    kwargs: dict = {"cwd": str(BACKEND), "env": env}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
        kwargs["stdin"] = subprocess.DEVNULL
    else:
        kwargs["start_new_session"] = True
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL

    subprocess.Popen(cmd, **kwargs)

    for i in range(40):
        time.sleep(0.5)
        if health_ok():
            print(f"OK — API pronta em {HEALTH}")
            return 0
        if i in (6, 14, 24):
            print(f"  a aguardar health... ({i * 0.5:.0f}s)")

    print(f"ERRO — API não respondeu em {HEALTH} a tempo")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
