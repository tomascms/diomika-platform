"""BR-06, RP-05, FE-14, LEGAL-10: pedido de orçamento com empresa, NIF, localidade e tipo de cliente.

A BD, o Turnstile e o SMTP são substituídos: nada sai da máquina.
"""
from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from core.saga import orcamento_saga
from core.validators.nif import clean_nif, is_valid_nif

LINHAS = [{"ean": "5606044000012", "numero_cor": 1, "quantidade": 12}]
OLD_PAYLOAD = {"nome": "Ana Silva", "email": "ana@example.com", "linhas": LINHAS}
PEDIDO_ID = "3f2a9c1b-6d4e-4f10-9a77-0c5d2e8b1a34"

# Os mesmos valores que frontend-web/src/lib/nif.test.js.
VALID_NIFS = ["508651557", "123456789", "999999990", "501442600", "100000010", "100000070"]
INVALID_NIFS = ["508651558", "123456788", "123456780", "000000000", "12345678", "1234567890", "abcdefghi", ""]


# --- NIF ---------------------------------------------------------------------


@pytest.mark.parametrize("nif", VALID_NIFS)
def test_valid_pt_nif(nif):
    assert is_valid_nif(nif) is True


@pytest.mark.parametrize("nif", INVALID_NIFS)
def test_invalid_pt_nif(nif):
    assert is_valid_nif(nif) is False


@pytest.mark.parametrize(
    "typed", ["508651557", " 508 651 557 ", "508.651.557", "508-651-557", "PT508651557", "pt 508 651 557"]
)
def test_clean_nif_keeps_only_the_nine_digits(typed):
    assert clean_nif(typed) == "508651557"


@pytest.mark.parametrize("typed", ["508651558", "PT123456788", "123 456 780"])
def test_clean_nif_refuses_a_portuguese_nif_with_a_wrong_check_digit(typed):
    with pytest.raises(ValueError):
        clean_nif(typed)


@pytest.mark.parametrize("typed", ["ES B12345678", "DE123456789", "FR 12 345678901", "4567", "1234567890123"])
def test_clean_nif_keeps_a_foreign_number_as_typed(typed):
    assert clean_nif(typed) == typed.strip()


# --- Rota ----------------------------------------------------------------------


@pytest.fixture
def api(monkeypatch):
    """App completa com o Turnstile, a validação das linhas e a saga substituídos. `saga` regista o que se guardaria."""
    import main
    from core import rate_limit
    from core.config import get_settings

    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(rate_limit, "_hits", defaultdict(list))
    monkeypatch.setattr("utils.turnstile.verify_turnstile", lambda token, remote_ip=None: None)
    monkeypatch.setattr("routes.orcamentos.validate_order_lines", lambda linhas: None)
    saga = AsyncMock(return_value=SimpleNamespace(pedido_id=PEDIDO_ID, status="Nova"))
    monkeypatch.setattr("routes.orcamentos.run_orcamento_submission_saga", saga)
    yield SimpleNamespace(client=TestClient(main.app, base_url="http://localhost"), saga=saga)
    get_settings.cache_clear()


def _saved(api) -> dict:
    api.saga.assert_awaited_once()
    return api.saga.await_args.args[0]


def test_old_payload_is_still_accepted(api):
    response = api.client.post("/orcamentos", json=OLD_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["id"] == PEDIDO_ID
    saved = _saved(api)
    assert saved["nome"] == "Ana Silva"
    assert (saved["empresa"], saved["nif"], saved["localidade"], saved["tipo_cliente"]) == (None, None, None, None)


def test_new_fields_reach_the_saga(api):
    response = api.client.post(
        "/orcamentos",
        json={
            **OLD_PAYLOAD,
            "empresa": "Têxteis do Ave, Lda",
            "nif": "508651557",
            "localidade": "Guimarães",
            "tipo_cliente": "empresa",
        },
    )

    assert response.status_code == 200
    saved = _saved(api)
    assert saved["empresa"] == "Têxteis do Ave, Lda"
    assert saved["nif"] == "508651557"
    assert saved["localidade"] == "Guimarães"
    assert saved["tipo_cliente"] == "empresa"
    assert "website" not in saved and "cf_turnstile_response" not in saved


def test_nif_typed_with_prefix_and_separators_is_stored_as_nine_digits(api):
    response = api.client.post("/orcamentos", json={**OLD_PAYLOAD, "nif": " PT 508.651.557 "})

    assert response.status_code == 200
    assert _saved(api)["nif"] == "508651557"


@pytest.mark.parametrize("tipo", ["empresa", "particular", None])
def test_portuguese_nif_with_a_wrong_check_digit_is_refused_in_portuguese(api, tipo):
    response = api.client.post("/orcamentos", json={**OLD_PAYLOAD, "nif": "508651558", "tipo_cliente": tipo})

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert [e["loc"][-1] for e in errors] == ["nif"]
    assert errors[0]["msg"] == "NIF inválido: o dígito de controlo não confere. Confira os 9 dígitos."
    api.saga.assert_not_awaited()


@pytest.mark.parametrize("tipo", ["particular", "empresa", None])
def test_foreign_nif_is_accepted(api, tipo):
    response = api.client.post("/orcamentos", json={**OLD_PAYLOAD, "nif": "ES B12345678", "tipo_cliente": tipo})

    assert response.status_code == 200
    assert _saved(api)["nif"] == "ES B12345678"


@pytest.mark.parametrize("blank", ["", "   ", None], ids=["vazio", "espaços", "null"])
def test_blank_optional_fields_are_stored_as_null(api, blank):
    response = api.client.post(
        "/orcamentos",
        json={**OLD_PAYLOAD, "empresa": blank, "nif": blank, "localidade": blank, "tipo_cliente": None},
    )

    assert response.status_code == 200
    saved = _saved(api)
    assert (saved["empresa"], saved["nif"], saved["localidade"]) == (None, None, None)


def test_customer_type_only_accepts_empresa_or_particular(api):
    response = api.client.post("/orcamentos", json={**OLD_PAYLOAD, "tipo_cliente": "revendedor"})

    assert response.status_code == 422
    api.saga.assert_not_awaited()


@pytest.mark.parametrize("field,limit", [("empresa", 200), ("nif", 20), ("localidade", 120)])
def test_new_fields_have_a_length_limit(api, field, limit):
    assert api.client.post("/orcamentos", json={**OLD_PAYLOAD, field: "9" * limit}).status_code == 200
    api.saga.reset_mock()
    assert api.client.post("/orcamentos", json={**OLD_PAYLOAD, field: "9" * (limit + 1)}).status_code == 422
    api.saga.assert_not_awaited()


def test_twenty_lines_at_the_quantity_limit_are_still_accepted(api):
    """Revisão: carrinho com 20 linhas e quantidades no limite continua a enviar."""
    linhas = [{"ean": f"56060440000{n:02d}", "numero_cor": 1, "quantidade": 6000} for n in range(20)]

    response = api.client.post(
        "/orcamentos",
        json={**OLD_PAYLOAD, "linhas": linhas, "nif": "508651557", "tipo_cliente": "empresa", "empresa": "X" * 200},
    )

    assert response.status_code == 200
    assert len(_saved(api)["linhas"]) == 20


# --- Saga: gravação e emails -----------------------------------------------------


class _FakeTable:
    def __init__(self, db):
        self.db = db
        self.name = ""

    def insert(self, record):
        self.db.inserted.append((self.name, record))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=[{"id": PEDIDO_ID}]))

    def update(self, values):
        self.db.updated.append((self.name, values))
        return MagicMock()


class _FakeDb:
    def __init__(self):
        self.inserted: list[tuple[str, dict]] = []
        self.updated: list[tuple[str, dict]] = []

    def table(self, name):
        table = _FakeTable(self)
        table.name = name
        return table


@pytest.fixture
def saga(monkeypatch):
    """A saga com a BD, o SMTP e as consultas ao catálogo substituídos; `sent` guarda os emails que sairiam."""
    db = _FakeDb()
    sent: list[dict] = []

    async def fake_send(**kwargs):
        sent.append(kwargs)
        return True

    monkeypatch.setattr(orcamento_saga, "get_db", lambda: db)
    monkeypatch.setattr(orcamento_saga, "saga_log_async", AsyncMock())
    monkeypatch.setattr(orcamento_saga, "send_email_async", fake_send)
    monkeypatch.setattr(orcamento_saga, "contact_notify_email", lambda: "equipa@example.test")
    monkeypatch.setattr(
        orcamento_saga,
        "resolve_product_lines_batch",
        lambda linhas: [
            {**l, "modelo": "Agate", "dimensoes": "45x45", "cor_nome": "Azul", "altura": l.get("altura") or None}
            for l in linhas
        ],
    )
    monkeypatch.delenv("QUOTE_RECEIPT_EMAIL", raising=False)

    def run(**fields):
        body = {"nome": "Ana Silva", "email": "ana@example.com", "observacoes": "Entrega em maio", **fields}
        linhas = [orcamento_saga.PedidoOrcamentoLinha(**linha) for linha in LINHAS]
        return asyncio.run(orcamento_saga.run_orcamento_submission_saga(body, linhas))

    return SimpleNamespace(db=db, sent=sent, run=run)


def _saved_record(saga) -> dict:
    (table, record), = saga.db.inserted
    assert table == "pedidos_orcamento"
    return record


def test_saga_saves_the_company_fields(saga):
    saga.run(empresa="Têxteis do Ave, Lda", nif="508651557", localidade="Guimarães", tipo_cliente="empresa")

    record = _saved_record(saga)
    assert record["empresa"] == "Têxteis do Ave, Lda"
    assert record["nif"] == "508651557"
    assert record["localidade"] == "Guimarães"
    assert record["tipo_cliente"] == "empresa"


def test_saga_without_the_new_fields_writes_no_new_columns(saga):
    """Um pedido antigo grava-se mesmo que a migração ainda não esteja aplicada: só leva colunas que já existem."""
    saga.run(nif=None, localidade=None, tipo_cliente=None, empresa=None)

    record = _saved_record(saga)
    assert not {"nif", "localidade", "tipo_cliente"} & record.keys()
    assert record["nome"] == "Ana Silva"


def test_the_notification_to_the_team_shows_who_is_buying(saga):
    saga.run(empresa="Têxteis do Ave, Lda", nif="508651557", localidade="Guimarães", tipo_cliente="empresa")

    (email,) = saga.sent
    assert email["to_email"] == "equipa@example.test"
    for line in (
        "Empresa: Têxteis do Ave, Lda",
        "NIF: 508651557",
        "Localidade: Guimarães",
        "Compra como: empresa",
    ):
        assert line in email["body"]
    assert f"#{PEDIDO_ID[:8]}" in email["subject"] + email["body"]


def test_the_notification_to_the_team_shows_a_dash_for_what_was_not_given(saga):
    saga.run()

    (email,) = saga.sent
    for label in ("Empresa", "NIF", "Localidade", "Compra como"):
        assert f"{label}: -\n" in email["body"]
    assert "None" not in email["body"]


# --- Recibo ao comprador (desligado por omissão) ------------------------------------------


def test_receipt_is_off_by_default(saga):
    saga.run()

    assert [e["to_email"] for e in saga.sent] == ["equipa@example.test"]


@pytest.mark.parametrize("value", ["0", "", "false", "no"])
def test_receipt_stays_off_unless_the_flag_is_on(saga, monkeypatch, value):
    monkeypatch.setenv("QUOTE_RECEIPT_EMAIL", value)
    saga.run()

    assert [e["to_email"] for e in saga.sent] == ["equipa@example.test"]


def test_receipt_goes_to_the_buyer_when_the_flag_is_on(saga, monkeypatch):
    monkeypatch.setenv("QUOTE_RECEIPT_EMAIL", "1")
    result = saga.run(empresa="Têxteis do Ave, Lda", tipo_cliente="empresa")

    assert result.pedido_id == PEDIDO_ID
    team, buyer = saga.sent
    assert team["to_email"] == "equipa@example.test"
    assert buyer["to_email"] == "ana@example.com"
    ref = PEDIDO_ID[:8]
    assert ref in buyer["subject"]
    body = buyer["body"]
    assert body.startswith("Olá,\n\nRecebemos o seu pedido")
    assert f"n.º {ref}" in body
    assert "Agate 45x45 | Cor 1 (Azul) | EAN 5606044000012 | Qtd 12" in body  # o que pediu
    assert "O pedido não é vinculativo: a venda só se conclui quando aceitar a nossa proposta." in body
    assert "https://www.diomika.com/privacidade" in body
    assert "None" not in body


def test_receipt_does_not_repeat_free_text_from_the_form(saga, monkeypatch):
    """Quem escreve o formulário escolhe o destinatário: o recibo não pode levar texto dele com a nossa assinatura."""
    monkeypatch.setenv("QUOTE_RECEIPT_EMAIL", "1")
    saga.run(
        nome="Ana Silva Visite http://evil.example",
        observacoes="Pague já em http://evil.example/pagar",
        empresa="Empresa Falsa Lda",
        localidade="Terra Nenhuma",
        nif="508651557",
    )

    buyer = saga.sent[1]
    text = buyer["subject"] + buyer["body"]
    for typed in ("Ana Silva", "evil.example", "Empresa Falsa", "Terra Nenhuma", "508651557", "Pague já"):
        assert typed not in text


def test_receipt_carries_the_legal_identification_and_complaints_information(saga, monkeypatch):
    """Pontos de recolha e emails, n.º 4: assinatura com identificação legal, Livro de Reclamações e RAL."""
    monkeypatch.setenv("QUOTE_RECEIPT_EMAIL", "1")
    saga.run()

    body = saga.sent[1]["body"]
    for text in (
        "DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA",
        "Sociedade unipessoal por quotas",
        "Sede: Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas, Guimarães",
        "Matrícula na Conservatória do Registo Comercial e NIPC 508 651 557",
        "935 745 663 (Chamada para a rede móvel nacional)",
        "Livro de Reclamações Eletrónico: https://www.livroreclamacoes.pt",
        "TRIAVE – Centro de Arbitragem de Conflitos de Consumo do Ave, Tâmega e Sousa (www.triave.pt)",
    ):
        assert text in body


def test_receipt_never_shows_a_personal_mailbox(saga, monkeypatch):
    """O remetente de hoje é a caixa pessoal do prestador: as caixas do ambiente nunca vão para o texto do recibo."""
    personal = "prestador.pessoal@gmail.example"
    for var in ("MAIL_FROM", "MAIL_USERNAME", "CONTACT_EMAIL", "CONTACT_NOTIFY_EMAIL"):
        monkeypatch.setenv(var, personal)
    monkeypatch.setenv("QUOTE_RECEIPT_EMAIL", "1")
    saga.run()

    buyer = saga.sent[1]
    assert personal not in buyer["subject"] + buyer["body"]
    assert not buyer.get("reply_to")  # sem Reply-To: a resposta segue pelo formulário de contacto, não para uma caixa
    assert not re.search(r"\S+@\S+", buyer["body"])  # sem email público até o cliente o indicar (Parte D, item 2)


def test_receipt_failure_does_not_fail_or_change_the_quote(saga, monkeypatch):
    monkeypatch.setenv("QUOTE_RECEIPT_EMAIL", "1")

    async def only_the_team_gets_through(**kwargs):
        saga.sent.append(kwargs)
        return kwargs["to_email"] == "equipa@example.test"

    monkeypatch.setattr(orcamento_saga, "send_email_async", only_the_team_gets_through)
    result = saga.run()

    assert (result.pedido_id, result.status, result.email_sent) == (PEDIDO_ID, "Nova", True)
    assert saga.db.updated == []  # o estado do pedido não depende do recibo


def test_receipt_is_sent_even_when_there_is_no_team_address(saga, monkeypatch):
    monkeypatch.setenv("QUOTE_RECEIPT_EMAIL", "1")
    monkeypatch.setattr(orcamento_saga, "contact_notify_email", lambda: None)
    result = saga.run()

    assert result.status == "Nova"
    assert [e["to_email"] for e in saga.sent] == ["ana@example.com"]


def test_receipt_signature_says_the_same_as_the_storefront():
    """Os valores legais vivem em dois sítios (loja e API): este teste apanha uma deriva entre eles."""
    constants = (Path(__file__).resolve().parents[2] / "frontend-web" / "src" / "lib" / "constants.js").read_text(
        encoding="utf-8"
    )
    from core import company

    for value in (
        company.LEGAL_NAME,
        company.ADDRESS,
        company.POSTAL,
        company.MUNICIPALITY,
        company.NIPC,
        company.PHONE,
        company.REGISTRY,
        company.COMPLAINTS_BOOK_URL,
        company.ADR_NAME,
        company.ADR_SITE,
    ):
        assert f"'{value}'" in constants, value
    assert "shareCapital: ''" in constants and company.SHARE_CAPITAL == ""
    assert "email: ''" in constants and company.EMAIL == ""


# --- PDF do backoffice -----------------------------------------------------------------


def test_pdf_header_lists_who_is_buying(api, monkeypatch):
    from core.auth import require_pedidos
    from core.local_only import admin_must_be_local

    row = {
        "id": PEDIDO_ID,
        "nome": "Ana Silva",
        "email": "ana@example.com",
        "contacto": "912345678",
        "empresa": "Têxteis do Ave, Lda",
        "nif": "508651557",
        "localidade": "Guimarães",
        "tipo_cliente": "empresa",
        "linhas": [],
    }
    table = MagicMock()
    table.select.return_value.eq.return_value.single.return_value.execute.return_value = SimpleNamespace(data=row)
    monkeypatch.setattr("routes.orcamentos.supabase", SimpleNamespace(table=lambda name: table))
    monkeypatch.setattr("routes.orcamentos.enrich_order_lines", lambda linhas: linhas)
    monkeypatch.setattr("routes.orcamentos.audit_request", lambda *a, **k: None)
    build = MagicMock(return_value=b"%PDF-1.4")
    monkeypatch.setattr("routes.orcamentos.build_pedido_pdf", build)
    app = api.client.app
    app.dependency_overrides[admin_must_be_local] = lambda: None
    app.dependency_overrides[require_pedidos] = lambda: None
    try:
        response = api.client.get(f"/orcamentos/{PEDIDO_ID}/pdf")
    finally:
        app.dependency_overrides.pop(admin_must_be_local, None)
        app.dependency_overrides.pop(require_pedidos, None)

    assert response.status_code == 200
    assert build.call_args.args[3] == [
        "Email: ana@example.com",
        "Contacto: 912345678",
        "Empresa: Têxteis do Ave, Lda",
        "NIF: 508651557",
        "Localidade: Guimarães",
        "Compra como: empresa",
    ]
