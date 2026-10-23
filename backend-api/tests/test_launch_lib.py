"""Helpers do orquestrador de lançamento."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy"))

from launch_lib import Report, build_maintenance_artifact, require_env_keys  # noqa: E402


def test_report_tracks_critical_failures():
    r = Report()
    r.add("a", True)
    r.add("b", False, "x", critical=False)
    r.add("c", False, "y", critical=True)
    assert not r.ok
    assert r.failed() == ["c"]


def test_require_env_keys():
    r = Report()
    require_env_keys({"A": "1"}, ["A", "B"], r)
    assert not r.ok


def test_maintenance_artifact_builds():
    path = build_maintenance_artifact()
    assert (path / "index.html").is_file()
    assert "Diomika" in (path / "index.html").read_text(encoding="utf-8")
