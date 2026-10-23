"""Biblioteca partilhada — lançamento Diomika (precheck / smoke / estado)."""
from __future__ import annotations

import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "deploy" / "launch.state.json"
ARTIFACT_PROD = ROOT / "deploy" / "artifacts" / "loja-producao"
ARTIFACT_PREV = ROOT / "deploy" / "artifacts" / "loja-previous"
ARTIFACT_MAINT = ROOT / "deploy" / "artifacts" / "loja-maintenance"
DIST = ROOT / "frontend-web" / "dist"

sys.path.insert(0, str(ROOT / "deploy"))
sys.path.insert(0, str(ROOT / "backend-api"))

DOMAIN = os.getenv("DIOMIKA_DOMAIN", "diomika.com")
API_PROD = os.getenv("API_BASE_URL") or f"https://api.{DOMAIN}"
PAGES_PROD = f"https://www.{DOMAIN}"
PAGES_PROJECT = os.getenv("PAGES_PROJECT", "diomika-loja")


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""
    critical: bool = True


@dataclass
class Report:
    steps: list[StepResult] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "", *, critical: bool = True) -> None:
        self.steps.append(StepResult(name, ok, detail, critical))
        mark = "OK" if ok else ("FAIL" if critical else "WARN")
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps if s.critical)

    def failed(self) -> list[str]:
        return [s.name for s in self.steps if not s.ok and s.critical]


def load_env() -> dict[str, str]:
    """Ambiente do processo + .env da raiz (o processo tem prioridade)."""
    env = dict(os.environ)
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def save_launch_state(data: dict[str, Any]) -> None:
    prev = {}
    if STATE_PATH.is_file():
        try:
            prev = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    prev.update(data)
    prev["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    STATE_PATH.write_text(json.dumps(prev, indent=2, ensure_ascii=False), encoding="utf-8")


def read_launch_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def ssl_ctx():
    from test_http import ssl_context

    return ssl_context()


def http_get(url: str, *, timeout: float = 15.0) -> tuple[int, str, float]:
    started = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": "DiomikaLaunch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx()) as resp:
            body = resp.read(2048).decode("utf-8", errors="replace")
            return resp.status, body, (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        return exc.code, "", (time.perf_counter() - started) * 1000
    except Exception as exc:
        return 0, str(exc)[:200], (time.perf_counter() - started) * 1000


def tcp_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run(cmd: list[str], *, env: dict | None = None) -> int:
    return subprocess.run(cmd, cwd=ROOT, env=env).returncode


def require_env_keys(env: dict[str, str], keys: list[str], report: Report, *, critical: bool = True) -> None:
    missing = [k for k in keys if not (env.get(k) or "").strip()]
    if missing:
        report.add("envs", False, "em falta: " + ", ".join(missing), critical=critical)
    else:
        report.add("envs", True, f"{len(keys)} chaves OK")


def snapshot_dist_to(dest: Path) -> bool:
    if not DIST.is_dir():
        return False
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(DIST, dest)
    return True


def restore_artifact_to_dist(src: Path) -> bool:
    if not src.is_dir():
        return False
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(src, DIST)
    return True


def build_maintenance_artifact() -> Path:
    ARTIFACT_MAINT.mkdir(parents=True, exist_ok=True)
    src = ROOT / "frontend-web" / "public" / "maintenance.html"
    (ARTIFACT_MAINT / "index.html").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (ARTIFACT_MAINT / "maintenance.html").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (ARTIFACT_MAINT / "_headers").write_text(
        "/*\n  X-Robots-Tag: noindex\n  Cache-Control: no-store\n",
        encoding="utf-8",
    )
    return ARTIFACT_MAINT


def dns_resolves(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, 443)
        return True
    except OSError:
        return False


def check_tls(hostname: str) -> tuple[bool, str]:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return True, f"TLS OK ({cert.get('notAfter', '?')})"
    except Exception as exc:
        return False, str(exc)[:160]


def redis_ping(url: str) -> tuple[bool, str]:
    if not url.strip():
        return False, "REDIS_URL vazio"
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(url, socket_connect_timeout=2)
        client.ping()
        return True, "PONG"
    except Exception as exc:
        return False, str(exc)[:120]


def supabase_ok() -> tuple[bool, str]:
    try:
        from core.db_verify import verify_supabase

        state = verify_supabase(infra_tables=["categories"])
        if state.get("pg_ok"):
            return True, "PostgreSQL OK"
        return False, str(state.get("pg_msg") or "DB fail")
    except Exception as exc:
        return False, str(exc)[:120]
