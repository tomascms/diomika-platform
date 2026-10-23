"""Formulário agregado: consultas em paralelo e, num modelo, cores + EAN na mesma resposta."""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from routes import admin_form

SLOW = 0.3  # ~ida e volta VM (EUA) → Supabase (Irlanda)


def _slow(value):
    def fn(*_a, **_k):
        time.sleep(SLOW)
        return value
    return fn


def test_model_bundle_runs_queries_in_parallel_and_includes_children():
    table = MagicMock()
    table.select.return_value.eq.return_value.execute.side_effect = _slow(
        MagicMock(data=[{"id": "m1", "nome": "Foglia"}])
    )
    request = SimpleNamespace(state=SimpleNamespace(api_role="admin"))
    with patch.object(admin_form, "_db_table", return_value=table), patch.object(
        admin_form, "_scoped", side_effect=lambda q, *_a, **_k: q
    ), patch.object(admin_form, "relation_options", side_effect=_slow([{"id": "c1", "label": "Almofada", "tipo_catalogo": "almofada"}])), patch.object(
        admin_form, "admin_list_rows", side_effect=_slow([{"id": "x"}])
    ):
        started = time.perf_counter()
        bundle = admin_form.form_bundle(request, "modelos_almofadas", id="m1")
        elapsed = time.perf_counter() - started

    assert bundle["record"]["nome"] == "Foglia"
    assert bundle["children"]["colors"] == [{"id": "x"}]
    assert bundle["children"]["variants"] == [{"id": "x"}]
    assert isinstance(bundle["children"]["variant_fields"], list)
    # 4 consultas (registo, categorias, cores, EAN): em série seriam ~1,2 s.
    assert elapsed < SLOW * 2.5, elapsed


def test_new_record_bundle_has_no_children():
    request = SimpleNamespace(state=SimpleNamespace(api_role="admin"))
    with patch.object(admin_form, "relation_options", return_value=[]):
        bundle = admin_form.form_bundle(request, "modelos_almofadas", id=None)
    assert bundle["record"] is None and "children" not in bundle
