"""Versão única do ecossistema Diomika."""
import os

VERSION = "2.5.0"
# Commit publicado (build-arg GIT_SHA no Dockerfile): sem isto não se sabe o que está em produção (API-14).
GIT_SHA = (os.getenv("GIT_SHA") or "unknown").strip()[:40]
BUILD = f"{VERSION}.{GIT_SHA[:12]}"
