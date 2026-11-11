"""Ficheiros de deploy: versões fixas e contentor sem privilégios (API-05, SEG-06, SEG-07, DEVOPS-09)."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _lines(name):
    return [l.strip() for l in (ROOT / name).read_text(encoding="utf-8").splitlines() if l.strip() and not l.lstrip().startswith(("#", "-r "))]


def test_every_requirement_is_pinned_to_an_exact_version():
    for name in ("requirements.txt", "requirements-dev.txt"):
        for line in _lines(name):
            assert re.search(r"==\d", line), f"{name}: «{line}» sem versão exacta"


def test_the_lock_pins_every_direct_dependency_to_the_same_version():
    lock = {l.split("==")[0].lower().replace("_", "-"): l.split("==")[1] for l in _lines("requirements.lock") if "==" in l}
    for line in _lines("requirements.txt"):
        name, version = line.split("==")
        name = re.sub(r"\[.*\]", "", name).lower().replace("_", "-")
        assert lock.get(name) == version, f"{name}: requirements.txt {version} != lock {lock.get(name)}"


def test_the_image_installs_with_the_lock_and_runs_as_a_non_root_user():
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^FROM python:3\.12-slim@sha256:[0-9a-f]{64}", docker, re.M)
    assert "-c requirements.lock" in docker
    assert docker.index("USER app") < docker.index("CMD")
