#!/usr/bin/env python3
"""Gera as miniaturas `<ficheiro>.w480.webp` e `.w960.webp` das imagens que ainda não as têm.

Usa a configuração do .env da raiz (produção). Por omissão só lista o que faria;
`--apply` grava. Nunca apaga nem altera os originais.

  python deploy/backfill_thumbnails.py            # dry-run
  python deploy/backfill_thumbnails.py --apply
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-api"))

from core.env_loader import load_project_env  # noqa: E402

load_project_env()

from core.database import get_db  # noqa: E402
from utils.image_resize import THUMB_WIDTHS, is_thumb, make_thumbnail, thumb_path  # noqa: E402
from utils.storage import BUCKET  # noqa: E402

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


def list_all(bucket, prefix: str = "") -> list[str]:
    out: list[str] = []
    offset = 0
    while True:
        page = bucket.list(prefix, {"limit": 1000, "offset": offset})
        for item in page:
            name = f"{prefix}/{item['name']}" if prefix else item["name"]
            if item.get("id") is None:  # pasta
                out.extend(list_all(bucket, name))
            else:
                out.append(name)
        if len(page) < 1000:
            return out
        offset += 1000


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="gravar as miniaturas (sem isto é só dry-run)")
    args = ap.parse_args()

    bucket = get_db().storage.from_(BUCKET)
    names = set(list_all(bucket))
    todo = sorted(
        (n, w) for n in names for w in THUMB_WIDTHS
        if n.lower().endswith(IMAGE_EXT) and not is_thumb(n) and thumb_path(n, w) not in names
        and not n.startswith("barcodes/")  # têm de ficar nítidos para o scanner
    )
    print(f"{len(names)} objectos no bucket {BUCKET}; {len(todo)} miniaturas em falta")
    if not args.apply:
        for n, w in todo[:20]:
            print("  faria:", thumb_path(n, w))
        print("dry-run: nada gravado (use --apply)")
        return 0

    done = failed = 0
    for n, w in todo:
        for attempt in range(3):  # a ligação ao Storage cai de vez em quando
            try:
                thumb = make_thumbnail(bucket.download(n), n, width=w)
                if thumb:
                    bucket.upload(thumb_path(n, w), thumb, file_options={"content-type": "image/webp", "upsert": "true", "cache-control": "31536000"})
                break
            except Exception as exc:
                if attempt == 2:
                    thumb = None
                    print("  erro:", n, type(exc).__name__)
                else:
                    time.sleep(2)
        if not thumb:
            failed += 1
            continue
        done += 1
    print(f"gravadas {done}, ignoradas {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
