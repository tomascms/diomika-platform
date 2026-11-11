"""Task 2.7 (API): ciclo do orçamento, lista com `lida`, linhas com nome, conteúdo em falta (RP-06, RP-11, LEGAL-09)."""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

MIGRATION = Path(__file__).resolve().parents[2] / "db" / "migrations" / "2026-11-03_quote_lifecycle.sql"


def _req():
    return SimpleNamespace(state=SimpleNamespace(api_role="admin", api_actor="t", request_id="r"), client=None, headers={})


def _db(current, updated=True):
    t = MagicMock()
    t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=current)
    t.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "x"}] if updated else [])
    db = MagicMock()
    db.upd = t
    db.table.return_value = t
    return db


def _patch(db):
    from routes import admin_crud

    return patch.object(admin_crud, "_db_table", side_effect=lambda t: db.table(t)), patch.object(admin_crud, "_audit")


def _manage(body, current=None, **kw):
    from routes import admin_crud

    db = _db(current if current is not None else [{"vendido_em": None}], **kw)
    p1, p2 = _patch(db)
    with p1, p2:
        out = admin_crud.patch_quote_management(_req(), str(uuid4()), body)
    return out, db.upd.update.call_args.args[0]


def test_selling_sets_vendido_em_and_leaving_clears_it():
    _, sold = _manage({"status": "Vendido"})
    assert sold["status"] == "Vendido" and sold["vendido_em"]
    _, back = _manage({"status": "Em tratamento"}, current=[{"vendido_em": "2026-11-01T10:00:00+00:00"}])
    assert back["vendido_em"] is None


def test_selling_twice_keeps_the_first_date():
    _, again = _manage({"status": "Vendido"}, current=[{"vendido_em": "2026-11-01T10:00:00+00:00"}])
    assert again["vendido_em"] == "2026-11-01T10:00:00+00:00"


def test_the_body_cannot_set_vendido_em_directly():
    _, payload = _manage({"nota_interna": "ligar amanhã", "vendido_em": "2020-01-01"})
    assert "vendido_em" not in payload and payload["nota_interna"] == "ligar amanhã"


@pytest.mark.parametrize(
    "body",
    [{"status": "Ganho"}, {"valor_proposta": "abc"}, {"valor_proposta": -1}, {"nota_interna": "x" * 2001}, {}],
)
def test_invalid_management_input_is_400_and_writes_nothing(body):
    from routes import admin_crud

    db = _db([{"vendido_em": None}])
    p1, p2 = _patch(db)
    with p1, p2, pytest.raises(HTTPException) as exc:
        admin_crud.patch_quote_management(_req(), str(uuid4()), body)
    assert exc.value.status_code == 400
    db.upd.update.assert_not_called()


def test_value_accepts_a_decimal_comma_and_empty_clears_it():
    _, payload = _manage({"valor_proposta": "1234,5"})
    assert payload["valor_proposta"] == 1234.5
    _, payload = _manage({"valor_proposta": ""})
    assert payload["valor_proposta"] is None


def test_unknown_quote_is_404():
    from routes import admin_crud

    db = _db([])
    p1, p2 = _patch(db)
    with p1, p2, pytest.raises(HTTPException) as exc:
        admin_crud.patch_quote_management(_req(), str(uuid4()), {"status": "Vendido"})
    assert exc.value.status_code == 404


def test_the_quote_list_select_has_the_unread_flag_and_the_status():
    from models.catalog_registry import admin_list_select_query

    cols = {c.strip() for c in admin_list_select_query("pedidos_orcamento").split(",")}
    assert {"id", "nome", "lida", "status", "vendido_em", "created_at"} <= cols


def test_the_quote_detail_carries_named_lines():
    from routes import admin_crud

    row = {"id": "p1", "linhas": [{"ean": "4006381333931", "numero_cor": 1, "quantidade": 3}]}
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=[row])
    with patch.object(admin_crud, "_scoped", return_value=chain), patch.object(admin_crud, "_db_table"), patch(
        "core.order_enrich.enrich_order_lines", side_effect=lambda l: [{**l[0], "modelo": "Agate", "cor_nome": "Azul"}]
    ):
        chain.eq.return_value = chain
        out = admin_crud.get_record(_req(), "pedidos_orcamento", str(uuid4()))
    assert out["linhas_detalhe"][0]["modelo"] == "Agate"


def test_migration_is_idempotent_and_adds_the_columns_and_the_status():
    sql = re.sub(r"--[^\n]*", "", MIGRATION.read_text(encoding="utf-8"))
    assert "ADD COLUMN IF NOT EXISTS valor_proposta" in sql and "ADD COLUMN IF NOT EXISTS nota_interna" in sql
    assert "DROP CONSTRAINT IF EXISTS ck_pedidos_orcamento_status" in sql
    assert "'Proposta enviada'" in sql
    from routes.admin_crud import QUOTE_STATUSES

    assert all(f"'{s}'" in sql for s in QUOTE_STATUSES)


# --- RP-11: conteúdo em falta ---------------------------------------------------------------------


def _model(i, **over):
    return {"id": f"m{i}", "nome": f"Modelo {i}", "tipo_catalogo": "almofada", "descricao": "Texto real", "visibilidade": True,
            "attributes": {"composicao": [{"material": "algodao", "pct": 100}]}, **over}


def _colour(i, image=None, nome="Azul"):
    return {"id_modelo": f"m{i}", "nome": nome, "imagem": image or f"foto-{i}.jpg"}


def test_a_complete_model_has_nothing_missing():
    from core.missing_content import find_missing

    assert find_missing([_model(1)], [_colour(1)], [{"id_modelo": "m1", "ean": "4006381333931"}]) == []


def test_each_gap_is_reported():
    from core.missing_content import find_missing

    bad = _model(1, descricao="Sem descrição", attributes={})
    out = find_missing([bad], [_colour(1, nome="Sortido")], [])
    assert out[0]["faltas"] == ["Sem descrição", "Sem composição", "Sem EAN", "Só a cor «Sortido»"]
    assert out[0]["tabela"]  # liga ao ecrã de edição


def test_the_same_image_on_two_models_is_a_demonstration_image():
    from core.missing_content import find_missing

    eans = [{"id_modelo": f"m{i}", "ean": "4006381333931"} for i in (1, 2, 3)]
    colours = [_colour(1, "logo.png"), _colour(2, "logo.png"), _colour(3)]
    out = {m["id"]: m["faltas"] for m in find_missing([_model(i) for i in (1, 2, 3)], colours, eans)}
    assert out == {"m1": ["Só imagem de demonstração"], "m2": ["Só imagem de demonstração"]}


def test_no_image_at_all_is_reported_and_worst_first():
    from core.missing_content import find_missing

    out = find_missing(
        [_model(1), _model(2, descricao="", attributes={})],
        [{"id_modelo": "m1", "nome": "Azul", "imagem": ""}],
        [{"id_modelo": "m1", "ean": "4006381333931"}],
    )
    assert [m["id"] for m in out] == ["m2", "m1"]
    assert "Sem imagem" in out[1]["faltas"]
