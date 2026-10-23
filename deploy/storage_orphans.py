#!/usr/bin/env python3
"""Lista (e com --apply apaga) imagens do Storage que nenhum registo da BD referencia.

Um objecto está "em uso" se o seu caminho aparecer em qualquer valor de qualquer linha
das tabelas públicas (não depende de saber que colunas têm imagens). Miniaturas
`.wNNN.webp` contam como em uso quando o original está. Antes de apagar, descarrega
cada órfão para deploy/backups/orfaos-<data>/ (repor: carregar de volta no mesmo caminho).

  python deploy/storage_orphans.py            # dry-run
  python deploy/storage_orphans.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-api"))
sys.path.insert(0, str(ROOT / "deploy"))

from core.env_loader import load_project_env  # noqa: E402

load_project_env()

from backfill_thumbnails import list_all  # noqa: E402
from core.database import get_db  # noqa: E402
from utils.storage import BUCKET  # noqa: E402

TABLES = [
    "categories", "product_models", "product_model_colors", "product_variants",
    "contact_messages", "message_history", "pedidos_orcamento", "encomendas_internas",
]
THUMB = re.compile(r"\.w\d+\.webp$")


def referenced_text(db) -> str:
    chunks = []
    for table in TABLES:
        offset = 0
        while True:
            rows = db.table(table).select("*").range(offset, offset + 999).execute().data or []
            chunks.append(json.dumps(rows, ensure_ascii=False))
            if len(rows) < 1000:
                break
            offset += 1000
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="copiar para deploy/backups e apagar (sem isto é só dry-run)")
    args = ap.parse_args()

    db = get_db()
    bucket = db.storage.from_(BUCKET)
    names = sorted(list_all(bucket))
    refs = referenced_text(db)
    orphans = [n for n in names if THUMB.sub("", n) not in refs]
    print(f"{len(names)} objectos no bucket {BUCKET}; {len(orphans)} sem referência na BD")
    for n in orphans[:15]:
        print("  órfão:", n)
    if not args.apply:
        print("dry-run: nada apagado (use --apply)")
        return 0

    out = ROOT / "deploy" / "backups" / f"orfaos-{date.today():%Y%m%d}"
    for n in orphans:
        dest = out / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(bucket.download(n))
    print(f"cópia: {len(orphans)} ficheiros em {out}")
    for i in range(0, len(orphans), 100):
        bucket.remove(orphans[i:i + 100])
    print(f"apagados {len(orphans)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
