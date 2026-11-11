"""Task 2.5: gravações atómicas, retenção, apagamento RGPD, origem, migrações (API-08, BD-*, LEGAL-09, RP-08, RP-10)."""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "db" / "migrations"
EAN = "4006381333931"  # EAN-13 válido


def _req(role="admin"):
    return SimpleNamespace(state=SimpleNamespace(api_role=role, api_actor="t", request_id="r"), client=None, headers={})


# --- API-08: modelo + cores + variantes numa transacção ---------------------------------------------


def _bundle_body(**over):
    cat = str(uuid4())
    body = {
        "model": {
            "id_categoria": cat,
            "tipo_catalogo": "almofada",
            "nome": "Foglia",
            "visibilidade": False,
            "attributes": {"tipo": "decorativa", "composicao": {"algodao": 100}, "dimensoes": ["45x45"]},
        },
        "colors": [{"numero": 1, "imagem": "https://x.test/a.png"}, {"numero": 2, "imagem": "https://x.test/b.png"}],
        "variants": [{"ean": EAN, "attributes": {"dimensoes": "45x45"}}],
    }
    body.update(over)
    return body


def test_bundle_is_one_rpc_one_invalidation_and_forces_the_parent_id():
    from routes import admin_crud

    db = MagicMock()
    db.rpc.return_value.execute.return_value = MagicMock(data={"colors": 2, "variants": 1})
    with patch("core.catalog_bundle.get_db", return_value=db), patch.object(
        admin_crud, "_invalidate_catalog_cache"
    ) as invalidate, patch.object(admin_crud, "_audit"), patch.object(admin_crud, "_schedule_barcode_update"):
        out = admin_crud.save_model_bundle(_req(), "modelos_almofadas", _bundle_body())
    assert db.rpc.call_count == 1  # uma só chamada: uma só transacção
    assert invalidate.call_count == 1  # e a versão do catálogo muda uma só vez
    name, args = db.rpc.call_args.args
    assert name == "save_model_bundle"
    p = args["p"]
    assert out["id"] == p["model"]["id"]
    assert {c["id_modelo"] for c in p["colors"]} == {p["model"]["id"]} == {v["id_modelo"] for v in p["variants"]}
    assert p["variants"][0]["tipo_catalogo"] == "almofada"
    # só leituras (pertença dos filhos); nenhuma escrita solta
    for call in (db.table.return_value.insert, db.table.return_value.update, db.table.return_value.delete, db.table.return_value.upsert):
        call.assert_not_called()


def test_bundle_failure_leaves_nothing_and_does_not_invalidate():
    from routes import admin_crud

    db = MagicMock()
    db.rpc.return_value.execute.side_effect = RuntimeError("duplicate key value violates unique constraint uq_product_variants_ean")
    with patch("core.catalog_bundle.get_db", return_value=db), patch.object(
        admin_crud, "_invalidate_catalog_cache"
    ) as invalidate, patch.object(admin_crud, "_audit") as audit, patch.object(
        admin_crud, "_schedule_barcode_update"
    ) as barcode:
        with pytest.raises(HTTPException) as exc:
            admin_crud.save_model_bundle(_req(), "modelos_almofadas", _bundle_body())
    assert exc.value.status_code in (400, 409)
    invalidate.assert_not_called()
    audit.assert_not_called()
    barcode.assert_not_called()


def test_bundle_validates_every_row_before_touching_the_db():
    from routes import admin_crud

    db = MagicMock()
    bad_ean = _bundle_body(variants=[{"ean": "123", "attributes": {}}])
    with patch("core.catalog_bundle.get_db", return_value=db):
        with pytest.raises(HTTPException) as exc:
            admin_crud.save_model_bundle(_req(), "modelos_almofadas", bad_ean)
    assert exc.value.status_code == 400
    db.rpc.assert_not_called()


def test_bundle_publish_needs_a_colour_with_image_and_an_ean():
    from routes import admin_crud

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    body = _bundle_body(colors=[], variants=[])
    body["model"]["visibilidade"] = True
    with patch("core.catalog_bundle.get_db", return_value=db):
        with pytest.raises(HTTPException) as exc:
            admin_crud.save_model_bundle(_req(), "modelos_almofadas", body)
    assert "cor com imagem" in exc.value.detail
    db.rpc.assert_not_called()


def test_bundle_publish_makes_children_visible_and_counts_existing_children():
    from core.catalog_bundle import build_bundle

    db = MagicMock()
    existing = {"product_model_colors": [{"id": "c-old", "imagem": "https://x.test/old.png"}], "product_variants": []}

    def table(name):
        t = MagicMock()
        t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=existing[name])
        return t

    db.table.side_effect = table
    body = _bundle_body(colors=[])
    body["model"]["visibilidade"] = True
    with patch("core.catalog_bundle.get_db", return_value=db):
        param, _ = build_bundle("modelos_almofadas", body)  # a cor que já existe chega para publicar
    assert param["variants"][0]["visibilidade"] is True


def test_bundle_delete_lists_must_be_uuids():
    from core.catalog_bundle import build_bundle

    with pytest.raises(ValueError, match="delete_colors"):
        build_bundle("modelos_almofadas", _bundle_body(delete_colors=["x'); drop table"]))


def test_bundle_only_for_model_tables():
    from routes import admin_crud

    with pytest.raises(HTTPException) as exc:
        admin_crud.save_model_bundle(_req(), "categories", {"model": {}})
    assert exc.value.status_code == 404


# --- API-08: visibilidade e apagar -----------------------------------------------------------------


def _visibility_db(row):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[row])
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[row])
    db.rpc.return_value.execute.return_value = MagicMock(data=1)
    return db


@pytest.mark.parametrize("table,kind", [("categories", "category"), ("modelos_almofadas", "model")])
def test_visibility_change_is_one_rpc_for_parent_and_children(table, kind):
    from routes import admin_crud, admin_crud_publishing

    rid = str(uuid4())
    db = _visibility_db({"id": rid, "visibilidade": False})
    with patch.object(admin_crud, "_db_table", side_effect=lambda t: db.table(t)), patch.object(
        admin_crud_publishing, "get_db", return_value=db
    ):
        res = admin_crud._set_visibility(table, rid, True)
    db.rpc.assert_called_once_with("set_catalog_visibility", {"p_kind": kind, "p_id": rid, "p_visible": True})
    assert res.data[0]["visibilidade"] is True
    db.table.return_value.update.assert_not_called()  # nada de UPDATE soltos


def test_visibility_of_a_missing_record_is_404():
    from routes import admin_crud

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    with patch.object(admin_crud, "_db_table", side_effect=lambda t: db.table(t)):
        with pytest.raises(HTTPException) as exc:
            admin_crud._set_visibility("categories", str(uuid4()), True)
    assert exc.value.status_code == 404
    db.rpc.assert_not_called()


def test_hard_delete_of_a_model_is_a_single_delete():
    from routes import admin_crud

    db = MagicMock()
    with patch.object(admin_crud, "get_db", return_value=db), patch.object(
        admin_crud, "_db_table", side_effect=lambda t: db.table(t)
    ), patch.object(admin_crud, "_invalidate_catalog_cache"), patch.object(admin_crud, "_audit"):
        out = admin_crud.delete_record(_req(), "modelos_almofadas", str(uuid4()), hard=True)
    assert out == {"status": "deleted", "hard": True}
    tables = [c.args[0] for c in db.table.call_args_list]
    assert "product_variants" not in tables and "product_model_colors" not in tables  # a FK em cascata trata deles
    assert db.table.return_value.delete.call_count == 1


def test_deleting_a_category_with_models_is_409_not_a_cascade():
    from routes import admin_crud

    db = MagicMock()
    db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.side_effect = RuntimeError(
        'update or delete on table "categories" violates foreign key constraint (23503)'
    )
    db.table.return_value.delete.return_value.eq.return_value.execute.side_effect = RuntimeError(
        'update or delete on table "categories" violates foreign key constraint (23503)'
    )
    with patch.object(admin_crud, "_db_table", side_effect=lambda t: db.table(t)), patch.object(
        admin_crud, "_invalidate_catalog_cache"
    ) as invalidate:
        with pytest.raises(HTTPException) as exc:
            admin_crud.delete_record(_req(), "categories", str(uuid4()), hard=True)
    assert exc.value.status_code == 409 and "Esvazie" in exc.value.detail
    invalidate.assert_not_called()


# --- LEGAL-09: retenção ---------------------------------------------------------------------------


def _purge(monkeypatch, **env):
    from core import retention

    for k in ("RETENTION_ORCAMENTO_AGE_PURGE",):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    db = MagicMock()
    chains: dict[str, MagicMock] = {}

    def table(name):
        t = MagicMock(name=name)
        chains[name] = t
        t.delete.return_value.lt.return_value.is_.return_value.in_.return_value.execute.return_value = MagicMock(data=[1])
        t.delete.return_value.lt.return_value.is_.return_value.execute.return_value = MagicMock(data=[1, 2])
        t.delete.return_value.lt.return_value.in_.return_value.execute.return_value = MagicMock(data=[1, 2, 3])
        t.delete.return_value.lt.return_value.neq.return_value.execute.return_value = MagicMock(data=[1, 2, 3, 4])
        t.delete.return_value.lt.return_value.execute.return_value = MagicMock(data=[])
        return t

    db.table.side_effect = table
    with patch("core.database.get_db", return_value=db), patch("core.alerts.send_alert"):
        out = retention.purge_expired_pii()
    return out, chains


def test_quote_age_purge_is_off_by_default_and_spares_sold_quotes(monkeypatch):
    out, chains = _purge(monkeypatch)
    q = chains["pedidos_orcamento"].delete.return_value.lt.return_value
    q.is_.assert_called_once_with("vendido_em", "null")  # nunca apaga vendas
    q.is_.return_value.in_.assert_called_once_with("status", ["Cancelado", "Arquivado", "Rejeitado"])
    assert out["pedidos_orcamento"] == 1


def test_quote_age_purge_when_enabled_ignores_status_but_still_spares_sales(monkeypatch):
    out, chains = _purge(monkeypatch, RETENTION_ORCAMENTO_AGE_PURGE="1")
    q = chains["pedidos_orcamento"].delete.return_value.lt.return_value
    q.is_.assert_called_once_with("vendido_em", "null")
    q.is_.return_value.in_.assert_not_called()  # qualquer estado, 24 meses depois
    assert out["pedidos_orcamento"] == 2


def test_outbox_and_sagas_are_purged_but_never_pending_or_running(monkeypatch):
    out, chains = _purge(monkeypatch)
    chains["outbox_events"].delete.return_value.lt.return_value.in_.assert_called_once_with("status", ["done", "failed"])
    chains["saga_instances"].delete.return_value.lt.return_value.neq.assert_called_once_with("status", "running")
    assert out["outbox_events"] == 3 and out["saga_instances"] == 4


def test_outbox_and_saga_retention_cannot_go_below_30_days(monkeypatch):
    from core.retention import _days

    monkeypatch.setenv("RETENTION_OUTBOX_DAYS", "1")
    assert _days("RETENTION_OUTBOX_DAYS", 30) == 30


# --- LEGAL-09: apagamento RGPD por lower(email) --------------------------------------------------


class _FakeTable:
    def __init__(self, rows, log, name):
        self.rows, self.log, self.name = rows, log, name

    def select(self, *_a):
        return self

    def ilike(self, col, pattern):
        self.log.setdefault("ilike", []).append((self.name, col, pattern))
        return self

    def delete(self):
        return self

    def in_(self, _col, ids):
        self.log[self.name] = list(ids)
        self.ids = list(ids)
        return self

    def execute(self):
        return SimpleNamespace(data=[{"id": i} for i in getattr(self, "ids", [])] or self.rows)


def test_erase_finds_mixed_case_addresses_and_only_those():
    from routes.privacy import EraseBody, erase_by_email

    rows = {
        "contact_messages": [{"id": "1", "email": "Ana.Silva@Exemplo.pt"}, {"id": "2", "email": "ana-silva@exemplo.pt"}],
        "pedidos_orcamento": [{"id": "3", "email": "ana.silva@exemplo.pt"}],
    }
    log: dict = {}
    db = MagicMock()
    db.table.side_effect = lambda name: _FakeTable(rows[name], log, name)
    with patch("routes.privacy.get_db", return_value=db), patch("routes.privacy.log_admin_action"):
        out = erase_by_email(EraseBody(email="ANA.SILVA@exemplo.pt", confirm="ERASE"), _req(), role="admin")
    assert log["contact_messages"] == ["1"] and log["pedidos_orcamento"] == ["3"]  # «ana-silva@» (curinga) fica
    assert out["deleted"] == {"contact_messages": 1, "pedidos_orcamento": 1}
    assert log["ilike"][0] == ("contact_messages", "email", "ana.silva@exemplo.pt")


def test_erase_pattern_has_no_wildcards():
    from routes.privacy import _like_literal

    assert _like_literal("a_b%c@x.pt") == r"a\_b\%c@x.pt"


# --- RP-10 / BD-11: origem e emails ---------------------------------------------------------------


def test_origem_keeps_only_known_short_keys_and_never_a_query():
    from core.origem import clean_origem

    out = clean_origem(
        {
            "entrada": "/categoria/almofadas?email=a@b.pt#x",
            "referrer": "google.com",
            "utm_source": "newsletter",
            "produto": "foglia",
            "email": "a@b.pt",
            "extra": "x" * 500,
            "utm_medium": 5,
        }
    )
    assert out == {"entrada": "/categoria/almofadas", "referrer": "google.com", "utm_source": "newsletter", "produto": "foglia"}
    assert clean_origem(None) is None and clean_origem("x") is None and clean_origem({"email": "a@b.pt"}) is None
    assert len(clean_origem({"produto": "y" * 500})["produto"]) == 120


def test_forms_lowercase_the_email_for_the_check_constraint():
    from routes.contact import ContactRequest
    from routes.orcamentos import OrcamentoRequest

    contact = ContactRequest(nome="Ana", email="Ana.Silva@Exemplo.PT", mensagem="Olá, preciso de preços.")
    quote = OrcamentoRequest(
        nome="Ana", email=" Ana.Silva@Exemplo.PT", linhas=[{"ean": EAN, "numero_cor": 1, "quantidade": 12}]
    )
    assert contact.email == quote.email == "ana.silva@exemplo.pt"


def test_quote_saga_stores_origem_only_when_present():
    import asyncio
    from unittest.mock import AsyncMock

    from core.saga import orcamento_saga
    from models.schemas import PedidoOrcamentoLinha

    inserted: list[dict] = []
    db = MagicMock()
    db.table.return_value.insert.side_effect = lambda rec: (inserted.append(rec), MagicMock(execute=lambda: MagicMock(data=[{"id": "p1"}])))[1]
    linhas = [PedidoOrcamentoLinha(ean=EAN, numero_cor=1, quantidade=12)]
    with patch.object(orcamento_saga, "get_db", return_value=db), patch.object(
        orcamento_saga, "saga_log_async", AsyncMock()
    ), patch.object(orcamento_saga, "contact_notify_email", lambda: None):
        asyncio.run(orcamento_saga.run_orcamento_submission_saga({"nome": "Ana", "email": "a@b.pt"}, linhas))
        asyncio.run(
            orcamento_saga.run_orcamento_submission_saga(
                {"nome": "Ana", "email": "a@b.pt", "origem": {"entrada": "/x?y=1", "bad": "z"}}, linhas
            )
        )
    assert "origem" not in inserted[0]
    assert inserted[1]["origem"] == {"entrada": "/x"}


def test_contact_saga_stores_origem_only_when_present():
    import asyncio
    from unittest.mock import AsyncMock

    from core.saga import contact_saga

    inserted: list[dict] = []
    db = MagicMock()
    db.table.return_value.insert.side_effect = lambda rec: (inserted.append(rec), MagicMock(execute=lambda: None))[1]
    with patch.object(contact_saga, "get_db", return_value=db), patch.object(
        contact_saga, "saga_log_async", AsyncMock()
    ), patch.object(contact_saga, "contact_notify_email", lambda: None):
        asyncio.run(contact_saga.run_contact_submission_saga({"nome": "a", "email": "a@b.pt", "origem": None}))
        asyncio.run(contact_saga.run_contact_submission_saga({"nome": "a", "email": "a@b.pt", "origem": {"produto": "foglia"}}))
    assert "origem" not in inserted[0]
    assert inserted[1]["origem"] == {"produto": "foglia"}


def test_slugs_are_ascii_so_the_db_check_accepts_them():
    from models.catalog_validators import generate_slug

    for text in ("Protetor de Colchão", "Guarda-chuva_XL", "Óculos 2.0!", "ação"):
        assert re.fullmatch(r"[a-z0-9-]+", generate_slug(text)), text
    assert generate_slug("???") == "item"  # nunca vazio (o CHECK recusa '')


def test_category_schema_has_the_description_column():
    from models.schemas import Categoria

    assert Categoria(nome="Almofadas", imagem="https://x.test/a.png").descricao == ""


# --- Migrações (ficheiros; nunca aplicadas aqui) -------------------------------------------------


def _sql(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding="utf-8")


EXPECTED_TABLES = (
    "admin_audit_log", "categories", "contact_messages", "encomendas_internas", "idempotency_keys",
    "message_history", "outbox_events", "pedidos_orcamento", "product_model_colors", "product_models",
    "product_variants", "saga_instances",
)


def test_baseline_defines_every_production_table_and_cannot_touch_a_live_database():
    sql = _sql("2026-10-28_0000_baseline.sql")
    for table in EXPECTED_TABLES:
        assert f"CREATE TABLE public.{table} " in sql, table
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;" in sql, table
    assert "public.legacy_" not in sql  # as tabelas legacy_* não voltam
    assert "to_regclass('public.categories') IS NOT NULL" in sql  # em produção não faz nada
    assert sql.count("$baseline$") == 2 and sql.count("$sql$") == 2  # blocos fechados
    assert sql.count("(") == sql.count(")")
    assert "CREATE VIEW public.catalog_ean_lookup" in sql and "rls_auto_enable" in sql
    assert "CREATE TRIGGER trg_product_variants_inherit_tipo" in sql


def test_only_the_baseline_and_later_migrations_are_in_the_apply_list():
    names = sorted(p.name for p in MIGRATIONS.glob("*.sql"))
    assert names[0] == "2026-10-28_0000_baseline.sql"
    assert not any(n < "2026-10-28" for n in names)


NEW_MIGRATIONS = (
    "2026-11-02_new_columns.sql",
    "2026-11-02_catalogue_functions.sql",
    "2026-11-02_database_hardening.sql",
    "2026-11-02_drop_backup_schema.sql",
)


@pytest.mark.parametrize("name", NEW_MIGRATIONS)
def test_new_migrations_are_idempotent(name):
    sql = re.sub(r"--[^\n]*", "", _sql(name))
    assert "ADD COLUMN" not in sql or "ADD COLUMN IF NOT EXISTS" in sql
    for stmt in re.findall(r"ADD COLUMN (?!IF NOT EXISTS)", sql):
        pytest.fail(f"{name}: ADD COLUMN sem IF NOT EXISTS")
    for m in re.finditer(r"ADD CONSTRAINT (\w+)", sql):
        assert f"DROP CONSTRAINT IF EXISTS {m.group(1)}" in sql, f"{name}: {m.group(1)} sem DROP IF EXISTS antes"
    assert not re.search(r"\bCREATE (UNIQUE )?INDEX (?!IF NOT EXISTS)", sql)
    assert not re.search(r"^\s*DROP (TABLE|INDEX|SCHEMA|POLICY) (?!IF EXISTS)", sql, re.M)


def test_columns_migration_has_what_the_api_selects_and_writes():
    sql = _sql("2026-11-02_new_columns.sql")
    for needle in (
        "public.categories ADD COLUMN IF NOT EXISTS descricao text NOT NULL DEFAULT ''",
        "public.pedidos_orcamento ADD COLUMN IF NOT EXISTS origem jsonb",
        "public.contact_messages ADD COLUMN IF NOT EXISTS origem jsonb",
        "public.pedidos_orcamento ADD COLUMN IF NOT EXISTS vendido_em timestamptz",
    ):
        assert needle in sql


def test_functions_migration_is_service_role_only():
    sql = _sql("2026-11-02_catalogue_functions.sql")
    for fn in ("save_model_bundle(jsonb)", "set_catalog_visibility(text, uuid, boolean)", "_bundle_upsert(regclass, jsonb)"):
        assert f"REVOKE ALL ON FUNCTION public.{fn} FROM PUBLIC, anon, authenticated;" in sql
        assert f"GRANT EXECUTE ON FUNCTION public.{fn} TO service_role;" in sql
    assert "SET search_path = public, pg_temp" in sql
    assert sql.count("$fn$") == 6  # 3 funções, abertura e fecho
    # as chamadas do código batem com as funções
    assert "save_model_bundle(p jsonb)" in sql and "set_catalog_visibility(p_kind text, p_id uuid, p_visible boolean)" in sql


def test_hardening_migration_covers_each_finding():
    sql = _sql("2026-11-02_database_hardening.sql")
    for needle in (
        "REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM anon, authenticated",  # BD-05
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public",
        "ALTER POLICY product_models_public_read",  # BD-06
        "ALTER POLICY product_variants_public_read",
        "ALTER POLICY product_model_colors_public_read",
        "DROP POLICY IF EXISTS product_images_public_read ON storage.objects",  # BD-07
        "file_size_limit = 5 * 1024 * 1024",
        "ALTER PUBLICATION supabase_realtime DROP TABLE",  # BD-08
        "DROP INDEX IF EXISTS public.idx_categories_slug",  # BD-09
        "DROP INDEX IF EXISTS public.idx_product_variants_attributes",
        "uq_product_models_cat_slug",  # BD-11
        "ck_contact_email_lower",
        "ck_pedidos_email_lower",
        "ALTER COLUMN tipo_catalogo DROP DEFAULT",
        "ck_pedidos_orcamento_status",
        "ON DELETE RESTRICT",  # BD-12
    ):
        assert needle in sql, needle
    assert "idx_message_history_message_id" not in sql.replace("Fica idx_message_history_message_id", "")
    assert "DROP SCHEMA" not in sql  # o DROP do schema backup fica à parte


def test_backup_schema_drop_is_separate_and_flagged_destructive():
    sql = _sql("2026-11-02_drop_backup_schema.sql")
    assert "DESTRUTIVO" in sql and "DROP SCHEMA IF EXISTS backup;" in sql and "CASCADE" not in sql.replace("sem CASCADE", "")


# --- Autorização do bundle: a acção vem da BD, filhos alheios recusados --------------------------


def _lookup_db(found: bool):
    db = MagicMock()
    chain = db.table.return_value.select.return_value
    for node in (chain.eq.return_value, chain.eq.return_value.eq.return_value):
        node.execute.return_value = MagicMock(data=[{"id": "x"}] if found else [])
    return db


def test_bundle_with_unknown_model_id_is_404_and_writes_nothing():
    from routes import admin_crud

    body = _bundle_body()
    body["model"]["id"] = str(uuid4())
    db = _lookup_db(False)
    with patch.object(admin_crud, "_db_table", side_effect=lambda t: db.table(t)), patch(
        "core.catalog_bundle.get_db", return_value=db
    ), patch.object(admin_crud, "assert_table_action") as act:
        with pytest.raises(HTTPException) as exc:
            admin_crud.save_model_bundle(_req(), "modelos_almofadas", body)
    assert exc.value.status_code == 404
    act.assert_not_called()
    db.rpc.assert_not_called()


def test_bundle_action_comes_from_the_database_not_the_body():
    from routes import admin_crud

    body = _bundle_body()
    db = MagicMock()
    db.rpc.return_value.execute.return_value = MagicMock(data={})
    with patch("core.catalog_bundle.get_db", return_value=db), patch.object(
        admin_crud, "assert_table_action"
    ) as act, patch.object(admin_crud, "_invalidate_catalog_cache"), patch.object(admin_crud, "_audit"), patch.object(
        admin_crud, "_schedule_barcode_update"
    ):
        admin_crud.save_model_bundle(_req(), "modelos_almofadas", body)  # sem id: criar
        assert act.call_args.args[1] == "create"
        body2 = _bundle_body()
        body2["model"]["id"] = str(uuid4())
        found = _lookup_db(True)
        with patch.object(admin_crud, "_db_table", side_effect=lambda t: found.table(t)):
            admin_crud.save_model_bundle(_req(), "modelos_almofadas", body2)  # existe: actualizar
        assert act.call_args.args[1] == "update"


def test_bundle_rejects_a_malformed_model_id():
    from routes import admin_crud

    body = _bundle_body()
    body["model"]["id"] = "not-a-uuid"
    with pytest.raises(HTTPException) as exc:
        admin_crud.save_model_bundle(_req(), "modelos_almofadas", body)
    assert exc.value.status_code == 400


def _children_db(table_rows):
    db = MagicMock()

    def table(name):
        t = MagicMock()
        t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=table_rows.get(name, []))
        return t

    db.table.side_effect = table
    return db


@pytest.mark.parametrize("where", ["colors", "variants", "delete_colors", "delete_variants"])
def test_bundle_rejects_children_of_another_model(where):
    from core.catalog_bundle import build_bundle

    other = str(uuid4())
    victim = str(uuid4())
    body = _bundle_body()
    if where == "colors":
        body["colors"][0]["id"] = victim
        rows = {"product_model_colors": [{"id": victim, "id_modelo": other}]}
    elif where == "variants":
        body["variants"][0]["id"] = victim
        rows = {"product_variants": [{"id": victim, "id_modelo": other}]}
    elif where == "delete_colors":
        body["delete_colors"] = [victim]
        rows = {"product_model_colors": [{"id": victim, "id_modelo": other}]}
    else:
        body["delete_variants"] = [victim]
        rows = {"product_variants": [{"id": victim, "id_modelo": other}]}
    with patch("core.catalog_bundle.get_db", return_value=_children_db(rows)):
        with pytest.raises(ValueError, match="outro modelo"):
            build_bundle("modelos_almofadas", body)


def test_bundle_accepts_new_children_and_children_of_the_same_model():
    from core.catalog_bundle import build_bundle

    model_id = str(uuid4())
    mine = str(uuid4())
    body = _bundle_body()
    body["model"]["id"] = model_id
    body["colors"][0]["id"] = mine
    rows = {"product_model_colors": [{"id": mine, "id_modelo": model_id}]}
    with patch("core.catalog_bundle.get_db", return_value=_children_db(rows)):
        param, _ = build_bundle("modelos_almofadas", body)
    assert param["colors"][0]["id"] == mine


def test_bundle_family_comes_from_the_table_not_the_body():
    from core.catalog_bundle import build_bundle

    body = _bundle_body()
    body["model"]["tipo_catalogo"] = "assento"
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    with patch("core.catalog_bundle.get_db", return_value=db):
        _, model = build_bundle("modelos_almofadas", body)
    assert model["tipo_catalogo"] == "almofada"


def test_child_upserts_never_reassign_another_models_row():
    sql = _sql("2026-11-02_catalogue_functions.sql")
    assert "id_modelo = excluded.id_modelo" in sql and "v_guard" in sql
