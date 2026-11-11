"""Fabricante ou importador e avisos de segurança de cada modelo (auditoria LEGAL-12).

Reg. (UE) 2023/988, art. 19.º, e Reg. (UE) 1007/2011: a ficha tem de dizer quem fabrica ou importa e que avisos o artigo
leva. Quatro colunas anuláveis em `product_models` (`fabricante_nome`, `fabricante_morada`, `fabricante_email`, `avisos`):
o backoffice grava-as, a API da loja devolve-as e os modelos antigos, que não as têm, continuam válidos.
"""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from catalog_db_fake import use_db  # noqa: F401  (fixture)
from catalog_db_fake import model, variant
from fastapi import HTTPException

from models.schemas import ProductModel

FIELDS = ("fabricante_nome", "fabricante_morada", "fabricante_email", "avisos")
CATEGORIA = str(uuid4())
BASE = {
    "id_categoria": CATEGORIA,
    "tipo_catalogo": "almofada",
    "nome": "Foglia",
    "attributes": {"tipo": "decorativa", "composicao": {"poliester": 100}, "dimensoes": ["45x45"]},
}
FILLED = {
    "fabricante_nome": "Têxteis do Ave, Lda",
    "fabricante_morada": "Rua da Fábrica 1, 4800-001 Guimarães",
    "fabricante_email": "qualidade@texteis-ave.example",
    "avisos": "Manter afastado de chamas.\nLavar a 30 °C.",
}


# --- O esquema ---------------------------------------------------------------------------------------------------


def test_the_four_fields_are_saved_as_written_and_cleaned():
    saved = ProductModel(**BASE, **{**FILLED, "fabricante_nome": "  Têxteis do Ave, Lda  ", "avisos": " Manter afastado de chamas. "}).model_dump()

    assert saved["fabricante_nome"] == "Têxteis do Ave, Lda"
    assert saved["fabricante_morada"] == FILLED["fabricante_morada"]
    assert saved["fabricante_email"] == "qualidade@texteis-ave.example"
    assert saved["avisos"] == "Manter afastado de chamas."


def test_an_old_model_without_them_stays_valid_and_sends_no_new_column():
    """O modelo antigo valida-se igual e a gravação não leva as colunas novas: funciona mesmo antes da migração."""
    saved = ProductModel(**BASE).model_dump()

    assert not set(FIELDS) & set(saved)
    assert saved["nome"] == "Foglia" and saved["descricao"] == ""


def test_clearing_a_field_in_the_backoffice_clears_it_in_the_database():
    """O formulário manda texto vazio quando se apaga um campo: tem de chegar à base de dados (senão ficava o valor antigo)."""
    saved = ProductModel(**BASE, fabricante_nome="", avisos="   ").model_dump()

    assert saved["fabricante_nome"] == "" and saved["avisos"] == ""
    assert "fabricante_morada" not in saved  # nunca preenchido: nem vai


@pytest.mark.parametrize("email", ["sem-arroba", "a@b", "a b@c.pt", "@c.pt", "a@"])
def test_a_bad_email_is_refused_in_portuguese(email):
    with pytest.raises(ValueError, match="Email do fabricante"):
        ProductModel(**BASE, fabricante_email=email)


def test_the_backoffice_form_lists_the_fields_as_optional_with_portuguese_labels():
    from models.schemas import TABLE_MAP
    from models.ui_schema import get_form_fields

    cfg = TABLE_MAP["modelos_almofadas"]
    fields = {f["name"]: f for f in get_form_fields(cfg["schema"], cfg, "modelos_almofadas")}

    assert [fields[name]["label"] for name in FIELDS] == [
        "Fabricante ou importador: nome",
        "Fabricante ou importador: morada",
        "Fabricante ou importador: email",
        "Avisos de segurança",
    ]
    assert all(fields[name]["required"] is False for name in FIELDS)
    assert fields["avisos"]["widget"] == "textarea"
    assert all(fields[name]["placeholder"] for name in FIELDS)
    # Logo a seguir à descrição, antes dos atributos da família.
    names = list(fields)
    assert names.index("descricao") < names.index("fabricante_nome") < names.index("tipo")


# --- A gravação (rotas do backoffice) ------------------------------------------------------------------------------


class _Table:
    def __init__(self):
        self.payloads: list[dict] = []

    def insert(self, payload):
        self.payloads.append(payload)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=[{**payload, "id": str(uuid4())}]))

    def update(self, payload):
        self.payloads.append(payload)
        chain = SimpleNamespace()
        chain.eq = lambda *_args: chain
        chain.execute = lambda: SimpleNamespace(data=[{**payload, "id": "m1"}])
        return chain


@pytest.fixture
def admin(monkeypatch):
    """As rotas de criar e actualizar um modelo, com a base de dados e os efeitos laterais substituídos."""
    from routes import admin_crud

    table = _Table()
    monkeypatch.setattr(admin_crud, "_db_table", lambda _name: table)
    monkeypatch.setattr(admin_crud, "_scoped", lambda query, *_args, **_kwargs: query)
    for effect in ("_audit", "_invalidate_catalog_cache", "_schedule_barcode_update", "_publish_catalog_children"):
        monkeypatch.setattr(admin_crud, effect, lambda *args, **kwargs: None)
    request = SimpleNamespace(state=SimpleNamespace(api_role="admin", api_actor="teste", request_id="t"))

    def create(request, table_name, body):
        return admin_crud.create_record(request, table_name, body, idempotency_key=None)

    return SimpleNamespace(table=table, request=request, create=create, update=admin_crud.update_record)


def _body(**extra):
    return {**BASE, "attributes": {}, "tipo": "decorativa", "composicao": {"poliester": 100}, "dimensoes": ["45x45"], **extra}


def test_creating_a_model_saves_the_fields_and_returns_them(admin):
    row = admin.create(admin.request, "modelos_almofadas", _body(**FILLED))

    (payload,) = admin.table.payloads
    assert {name: payload[name] for name in FIELDS} == FILLED
    assert {name: row[name] for name in FIELDS} == FILLED


def test_creating_a_model_without_them_sends_no_new_column(admin):
    admin.create(admin.request, "modelos_almofadas", _body())

    (payload,) = admin.table.payloads
    assert not set(FIELDS) & set(payload)


def test_updating_a_model_can_clear_a_field(admin):
    admin.update(admin.request, "modelos_almofadas", str(uuid4()), _body(fabricante_nome="", avisos=""))

    (payload,) = admin.table.payloads
    assert payload["fabricante_nome"] == "" and payload["avisos"] == ""


def test_a_bad_email_in_the_backoffice_is_a_400_with_the_message(admin):
    with pytest.raises(HTTPException) as error:
        admin.create(admin.request, "modelos_almofadas", _body(fabricante_email="isto-nao-e-um-email"))

    assert error.value.status_code == 400
    assert "Email do fabricante" in error.value.detail


# --- A API da loja ---------------------------------------------------------------------------------------------------


def test_the_store_api_returns_the_fields_and_an_old_model_without_them_is_unchanged(use_db):
    from core.catalog_storefront import models_detail_map_for_tipo

    novo = model("m-novo", "Foglia", "almofada", "almofada", [variant("5606044301018", dimensoes="45x45")], tipo="decorativa", composicao={"Poliester": 100})
    novo.update(FILLED)
    antigo = model("m-antigo", "Agate", "almofada", "almofada", [variant("5606044199011", dimensoes="45x45")], tipo="decorativa", composicao={"Veludo": 100})
    use_db([novo, antigo])

    details = models_detail_map_for_tipo("almofada", ["m-novo", "m-antigo"])

    assert {name: details["m-novo"][name] for name in FIELDS} == FILLED
    assert details["m-antigo"]["nome"] == "Agate"
    assert not set(FIELDS) & set(details["m-antigo"])
