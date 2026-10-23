#!/usr/bin/env python3
"""Grava variáveis secretas no .env da VM sem as mostrar nem guardar em lado nenhum.

Quem sabe o valor (o cliente, na passagem de contas) escreve-o escondido no terminal; o script
envia-o por scp, faz cópia do .env (`.env.bak-<data>`), substitui/acrescenta as chaves e,
com --restart, recria a API (e o túnel, se mudou) para as lerem.

  python deploy/set_vm_env.py MAIL_USERNAME MAIL_PASSWORD --restart
  python deploy/set_vm_env.py CLOUDFLARE_TUNNEL_TOKEN --restart
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_access  # noqa: E402

KEY = re.compile(r"[A-Z][A-Z0-9_]{1,63}")

# Corre na VM: junta as chaves novas ao .env (atómico, 600) e apaga o ficheiro temporário.
MERGE = r'''
import os, sys, time
target, update = sys.argv[1], sys.argv[2]
new = dict(l.split("=", 1) for l in open(update).read().splitlines() if "=" in l)
lines = open(target).read().splitlines() if os.path.exists(target) else []
if lines:
    bak = f"{target}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    open(bak, "w").write("\n".join(lines) + "\n"); os.chmod(bak, 0o600)
seen, out = set(), []
for l in lines:
    k = l.split("=", 1)[0].strip()
    if k in new and not l.lstrip().startswith("#"):
        out.append(f"{k}={new[k]}"); seen.add(k)
    else:
        out.append(l)
out += [f"{k}={v}" for k, v in new.items() if k not in seen]
tmp = target + ".tmp"
open(tmp, "w").write("\n".join(out) + "\n"); os.chmod(tmp, 0o600); os.replace(tmp, target)
os.remove(update)
print("actualizadas:", ", ".join(sorted(new)))
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keys", nargs="+", help="nomes das variáveis (ex.: MAIL_PASSWORD)")
    ap.add_argument("--restart", action="store_true", help="recriar a API e o túnel para lerem os valores novos")
    ap.add_argument("--target", default=f"{vm_access.APP_DIR}/.env", help=argparse.SUPPRESS)
    args = ap.parse_args()

    bad = [k for k in args.keys if not KEY.fullmatch(k)]
    if bad:
        print("Nomes inválidos:", ", ".join(bad))
        return 2
    values = {}
    for k in args.keys:
        while not (v := getpass.getpass(f"{k} (colar e Enter; não aparece): ").strip()) or "\n" in v:
            print("  Vazio — tenta outra vez.")
        values[k] = v

    if subprocess.run(vm_access.ssh("mkdir -p ~/.config && chmod 700 ~/.config")).returncode:
        return 1
    files = []
    try:
        for name, body in (("upd", "".join(f"{k}={v}\n" for k, v in values.items())), ("merge", MERGE)):
            fd, path = tempfile.mkstemp(prefix=f"diomika-{name}-")
            with os.fdopen(fd, "w", newline="\n") as fh:
                fh.write(body)
            files.append(path)
        if subprocess.run(vm_access.scp(files, ".config/")).returncode:
            return 1
    finally:
        for p in files:
            os.remove(p)
    upd, merge = (f"~/.config/{Path(p).name}" for p in files)
    remote = f"set -e; sudo python3 {merge} {args.target} {upd}; rm -f {merge}"
    if args.restart:
        remote += (
            f"; cd {vm_access.APP_DIR} && sudo docker compose --env-file .env -f deploy/docker-compose.free.yml"
            " --profile tunnel up -d --no-build --force-recreate api cloudflared"
            " && sleep 20 && curl -fsS -A DiomikaHealthcheck/1.0 http://127.0.0.1:8000/health/live"
        )
    return subprocess.run(vm_access.ssh(remote)).returncode


if __name__ == "__main__":
    sys.exit(main())
