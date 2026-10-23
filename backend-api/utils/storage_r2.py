"""Cloudflare R2 (S3-compatible) — backend opcional de storage.

Active com:
  STORAGE_BACKEND=r2
  R2_ACCOUNT_ID=...
  R2_ACCESS_KEY_ID=...
  R2_SECRET_ACCESS_KEY=...
  R2_BUCKET=product-images
  R2_PUBLIC_BASE_URL=https://img.diomika.com   # ou r2.dev
"""
from __future__ import annotations

import os
from functools import lru_cache


def r2_enabled() -> bool:
    return (os.getenv("STORAGE_BACKEND") or "supabase").strip().lower() == "r2"


@lru_cache(maxsize=1)
def _client():
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("STORAGE_BACKEND=r2 requer boto3 — pip install boto3") from exc

    account = (os.getenv("R2_ACCOUNT_ID") or "").strip()
    key = (os.getenv("R2_ACCESS_KEY_ID") or "").strip()
    secret = (os.getenv("R2_SECRET_ACCESS_KEY") or "").strip()
    if not account or not key or not secret:
        raise RuntimeError("R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY obrigatórios")
    endpoint = f"https://{account}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    return (os.getenv("R2_BUCKET") or os.getenv("SUPABASE_STORAGE_BUCKET") or "product-images").strip()


def upload_bytes(data: bytes, dest_path: str, content_type: str) -> str:
    client = _client()
    client.put_object(Bucket=_bucket(), Key=dest_path, Body=data, ContentType=content_type)
    return resolve_url(dest_path)


def resolve_url(dest_path: str) -> str:
    public = (os.getenv("R2_PUBLIC_BASE_URL") or "").rstrip("/")
    if public:
        return f"{public}/{dest_path.lstrip('/')}"
    # signed URL curta se sem CDN público
    client = _client()
    ttl = max(60, int(os.getenv("STORAGE_SIGNED_URL_TTL") or "3600"))
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": dest_path},
        ExpiresIn=ttl,
    )


def get_signed_url(dest_path: str, expires_in: int | None = None) -> str:
    client = _client()
    ttl = expires_in if expires_in is not None else max(60, int(os.getenv("STORAGE_SIGNED_URL_TTL") or "3600"))
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": dest_path},
        ExpiresIn=ttl,
    )
