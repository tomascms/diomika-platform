#!/usr/bin/env python3
"""Instala (ou actualiza) o backup diário da BD na VM e corre-o uma vez.

Copia deploy/vm/backup_db.sh para ~/bin na VM e cria a entrada de cron
(03:30 UTC) sem duplicar. Uso: python deploy/install_db_backups.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_access  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "vm" / "backup_db.sh"
CRON_LINE = "30 3 * * * $HOME/bin/diomika-backup-db.sh >/dev/null 2>&1"


def main() -> int:
    if subprocess.run(vm_access.ssh("mkdir -p ~/bin")).returncode != 0:
        return 1
    if subprocess.run(vm_access.scp([str(SCRIPT)], "bin/diomika-backup-db.sh")).returncode != 0:
        return 1
    install = (
        "set -e; sed -i 's/\\r$//' ~/bin/diomika-backup-db.sh; chmod 700 ~/bin/diomika-backup-db.sh; "
        f"{{ crontab -l 2>/dev/null | grep -v diomika-backup-db.sh || true; echo '{CRON_LINE}'; }} | crontab -; "
        "crontab -l | grep diomika-backup-db.sh; "
        "~/bin/diomika-backup-db.sh; ls -la ~/backups/db"
    )
    return subprocess.run(vm_access.ssh(install)).returncode


if __name__ == "__main__":
    sys.exit(main())
