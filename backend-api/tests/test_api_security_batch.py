"""Task 2.4: MFA, lockout em /mfa/setup, CSV, Turnstile, auditoria RGPD, imagens, higiene (SEG-02/03/05/12/14/18/19/20)."""
from __future__ import annotations

import io
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

PASSWORD = "Password-Ok-99x!"


@pytest.fixture()
def admin(tmp_path, monkeypatch):
    monkeypatch.setattr("core.admin_users._STORE", tmp_path / "admin_users.json")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "1")
    from core import rate_limit
    from core.admin_users import upsert_user

    monkeypatch.setattr(rate_limit, "_hits", rate_limit.defaultdict(list))
    upsert_user("alice", PASSWORD, role="admin")
    return "alice"


def _request(ip="198.51.100.7"):
    req = MagicMock()
    req.client.host = ip
    req.state.request_id = "t"
    return req


def _call(route, *args):
    with patch("routes.admin_auth.log_admin_action"):
        return route(*args)


# --- SEG-02 / SEG-03 ------------------------------------------------------------------------------


def test_mfa_setup_counts_towards_lockout(admin):
    from routes import admin_auth

    body = admin_auth.LoginBody(username="alice", password="wrong-password")
    for _ in range(5):
        with pytest.raises(HTTPException) as exc:
            _call(admin_auth.mfa_setup, body, _request())
        assert exc.value.status_code == 401
    # a conta ficou bloqueada: nem a password certa abre o enrolamento
    good = admin_auth.LoginBody(username="alice", password=PASSWORD)
    with pytest.raises(HTTPException) as exc:
        _call(admin_auth.mfa_setup, good, _request())
    assert exc.value.status_code == 401


def test_mfa_confirm_counts_towards_lockout(admin):
    from routes import admin_auth

    body = admin_auth.MfaConfirmBody(username="alice", password="wrong-password", totp_code="123456")
    for _ in range(5):
        with pytest.raises(HTTPException):
            _call(admin_auth.mfa_confirm, body, _request())
    from core.admin_users import authenticate

    user, err = authenticate("alice", PASSWORD)
    assert user is None and "bloqueada" in err.lower()


def test_enrolment_then_login_needs_the_code(admin):
    pyotp = pytest.importorskip("pyotp")
    from core.admin_users import authenticate
    from routes import admin_auth

    # sem MFA enrolado e com MFA obrigatório: não há sessão, só o pedido de enrolamento
    assert authenticate("alice", PASSWORD) == (None, "mfa_setup_required")

    setup = _call(admin_auth.mfa_setup, admin_auth.LoginBody(username="alice", password=PASSWORD), _request())
    code = pyotp.TOTP(setup["secret"]).now()
    out = _call(
        admin_auth.mfa_confirm,
        admin_auth.MfaConfirmBody(username="alice", password=PASSWORD, totp_code=code),
        _request(),
    )
    assert out["mfa_enabled"] is True

    # depois do enrolamento: sem código não entra, com código entra
    assert authenticate("alice", PASSWORD) == (None, "mfa_required")
    user, err = authenticate("alice", PASSWORD, totp_code=pyotp.TOTP(setup["secret"]).now())
    assert err is None and user["mfa_enabled"] is True

    # e já não se pode enrolar outro segundo factor só com a password
    with pytest.raises(HTTPException) as exc:
        _call(admin_auth.mfa_setup, admin_auth.LoginBody(username="alice", password=PASSWORD), _request())
    assert exc.value.status_code == 400


def test_wrong_totp_codes_count_towards_the_lockout(admin):
    pyotp = pytest.importorskip("pyotp")
    from core.admin_users import authenticate
    from routes import admin_auth

    setup = _call(admin_auth.mfa_setup, admin_auth.LoginBody(username="alice", password=PASSWORD), _request())
    _call(
        admin_auth.mfa_confirm,
        admin_auth.MfaConfirmBody(username="alice", password=PASSWORD, totp_code=pyotp.TOTP(setup["secret"]).now()),
        _request(),
    )
    for _ in range(4):
        assert authenticate("alice", PASSWORD, totp_code="000000") == (None, "Código MFA inválido")
    user, err = authenticate("alice", PASSWORD, totp_code="000000")
    assert user is None and "bloqueada" in err.lower()
    # bloqueada: nem o código certo entra
    user, err = authenticate("alice", PASSWORD, totp_code=pyotp.TOTP(setup["secret"]).now())
    assert user is None and "bloqueada" in err.lower()


def test_mfa_setup_has_a_per_user_limit(admin):
    from routes import admin_auth

    body = admin_auth.LoginBody(username="alice", password="x")
    statuses = set()
    for n in range(12):
        with pytest.raises(HTTPException) as exc:
            _call(admin_auth.mfa_setup, body, _request(ip=f"198.51.100.{n}"))  # IPs diferentes
        statuses.add(exc.value.status_code)
    assert 429 in statuses  # o limite por utilizador apanha o brute-force multi-IP


# --- SEG-05 ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["=HYPERLINK(\"http://x\")", "+1+1", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd"])
def test_csv_cells_that_start_like_formulas_are_neutralised(value):
    from routes.admin import _csv_safe

    assert _csv_safe(value) == "'" + value


@pytest.mark.parametrize("value", ["Ana Silva", "", "12", None, 5, "a=b"])
def test_csv_normal_cells_are_untouched(value):
    from routes.admin import _csv_safe

    assert _csv_safe(value) == value


# --- SEG-14 ---------------------------------------------------------------------------------------


def _verify(monkeypatch, hostname, *, production=True, secret="real-secret"):
    from utils import turnstile

    monkeypatch.setenv("TURNSTILE_SECRET_KEY", secret)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY_PREVIOUS", raising=False)
    monkeypatch.delenv("TURNSTILE_ALLOWED_HOSTNAMES", raising=False)
    settings = SimpleNamespace(is_production=production, is_beta=False, _turnstile_is_test_key=lambda: False)
    result = {"success": True}
    if hostname is not None:
        result["hostname"] = hostname
    fake = SimpleNamespace(json=lambda: result)
    with patch.object(turnstile, "get_settings", lambda: settings), patch.object(
        turnstile.requests, "post", lambda *a, **k: fake
    ):
        turnstile.verify_turnstile("tok")


@pytest.mark.parametrize("hostname", ["www.diomika.com", "diomika-loja.pages.dev", "WWW.DIOMIKA.COM"])
def test_turnstile_accepts_our_hostnames(monkeypatch, hostname):
    _verify(monkeypatch, hostname)


@pytest.mark.parametrize("hostname", ["localhost", "127.0.0.1", "evil.example", None, ""])
def test_turnstile_rejects_other_hostnames_in_production(monkeypatch, hostname):
    with pytest.raises(ValueError):
        _verify(monkeypatch, hostname)


def test_turnstile_hostname_not_enforced_outside_production(monkeypatch):
    _verify(monkeypatch, "example.com", production=False)


def test_turnstile_hostname_list_is_configurable(monkeypatch):
    from utils import turnstile

    monkeypatch.setenv("TURNSTILE_ALLOWED_HOSTNAMES", "a.example, b.example")
    assert turnstile._allowed_hostnames() == {"a.example", "b.example"}


# --- SEG-18 ---------------------------------------------------------------------------------------


def test_erase_audit_keeps_a_hash_not_the_email():
    import hashlib

    from routes.privacy import EraseBody, erase_by_email

    request = MagicMock()
    request.state.api_actor = "admin"
    db = MagicMock()
    db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": 1}])
    with patch("routes.privacy.get_db", return_value=db), patch("routes.privacy.log_admin_action") as audit:
        erase_by_email(EraseBody(email="Victim@Example.com", confirm="ERASE"), request, role="admin")
    detail = audit.call_args.kwargs["detail"]
    assert detail["email_sha256"] == hashlib.sha256(b"victim@example.com").hexdigest()
    assert "victim" not in json.dumps(detail).lower()


# --- SEG-19 ---------------------------------------------------------------------------------------

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from utils.image_resize import optimize_for_web  # noqa: E402


def _jpeg_with_gps() -> bytes:
    img = Image.new("RGB", (300, 200), (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "CameraMaker"  # Make
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (41.0, 33.0, 0.0)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_reencode_strips_exif_even_when_the_result_is_not_smaller():
    data = _jpeg_with_gps()
    assert dict(Image.open(io.BytesIO(data)).getexif())  # a fixture tem mesmo metadados
    out = optimize_for_web(data, "foto.jpg")
    assert not dict(Image.open(io.BytesIO(out)).getexif())


def test_gif_is_reencoded_and_keeps_its_frames():
    frames = [Image.new("RGB", (40, 40), c) for c in ((250, 0, 0), (0, 250, 0), (0, 0, 250))]
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=50, comment=b"secret note")
    out = optimize_for_web(buf.getvalue(), "anim.gif")
    result = Image.open(io.BytesIO(out))
    assert result.n_frames == 3
    assert b"secret note" not in out


@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
def test_image_above_the_pixel_ceiling_is_refused_before_decoding():
    img = Image.new("1", (8001, 10))  # lado acima de 8000 px
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    with pytest.raises(ValueError, match="demasiado grande"):
        optimize_for_web(buf.getvalue(), "x.png")
    wide = Image.new("1", (7000, 7000))  # 49 Mpx > 40 Mpx
    buf = io.BytesIO()
    wide.save(buf, format="PNG")
    with pytest.raises(ValueError, match="demasiado grande"):
        optimize_for_web(buf.getvalue(), "y.png")


def test_pixel_ceiling_is_set_on_pillow():
    optimize_for_web(_jpeg_with_gps(), "a.jpg")
    assert Image.MAX_IMAGE_PIXELS == 40_000_000


# --- SEG-20 ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    import main

    return TestClient(main.app, base_url="http://localhost")


def test_public_health_does_not_reveal_the_version(client):
    assert client.get("/health").json() == {"status": "online"}


def test_request_id_is_only_reflected_when_safe(client):
    ok = client.get("/health/live", headers={"X-Request-Id": "abc-123"})
    assert ok.headers["x-request-id"] == "abc-123"
    for bad in ("x" * 65, "a b", "<script>", "a;b"):
        got = client.get("/health/live", headers={"X-Request-Id": bad}).headers["x-request-id"]
        assert got != bad and len(got) == 36  # uuid novo


def test_ops_analytics_requires_a_local_caller():
    from core.local_only import admin_must_be_local
    from routes.ops_analytics import router

    deps = [d.dependency for d in router.dependencies]
    assert admin_must_be_local in deps


def test_csv_import_only_updates_rows_of_its_own_family():
    import asyncio

    from routes import admin

    db = MagicMock()
    query = db.table.return_value.update.return_value.eq.return_value
    query.eq.return_value.execute.return_value = MagicMock(data=[])  # id de outra família: nada actualizado
    csv_bytes = b"id,nome\n11111111-1111-1111-1111-111111111111,Novo\n"
    upload = MagicMock()

    async def read():
        return csv_bytes

    upload.read = read
    schema = MagicMock()
    schema.model_validate.return_value.model_dump.return_value = {"nome": "Novo"}
    with patch.object(admin, "get_db", return_value=db), patch.object(admin, "_exportable_tables", lambda: {"almofadas"}), patch.object(
        admin, "assert_table_action"
    ), patch.object(admin, "_schema_for", return_value=schema), patch.object(admin, "audit_request"), patch(
        "models.catalog_registry.physical_table_for", return_value="product_models"
    ), patch("models.catalog_registry.tipo_for_table", return_value="almofada"), patch(
        "models.catalog_registry.fold_attributes", lambda t, p: p
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(admin.import_csv(MagicMock(state=SimpleNamespace(api_role="admin")), "almofadas", upload))
    query.eq.assert_called_with("tipo_catalogo", "almofada")
    assert "id inexistente" in json.dumps(exc.value.detail)


def test_csv_import_of_colours_is_scoped_through_the_parent_model():
    import asyncio

    from routes import admin

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "m1"}])
    update = db.table.return_value.update.return_value.eq.return_value
    update.in_.return_value.execute.return_value = MagicMock(data=[{"id": "c1"}])
    upload = MagicMock()

    async def read():
        return b"id,nome" + bytes([10]) + b"11111111-1111-1111-1111-111111111111,Azul" + bytes([10])

    upload.read = read
    schema = MagicMock()
    schema.model_validate.return_value.model_dump.return_value = {"nome": "Azul"}
    with patch.object(admin, "get_db", return_value=db), patch.object(admin, "_exportable_tables", lambda: {"cores"}), patch.object(
        admin, "assert_table_action"
    ), patch.object(admin, "_schema_for", return_value=schema), patch.object(admin, "audit_request"), patch(
        "models.catalog_registry.physical_table_for", return_value="product_model_colors"
    ), patch("models.catalog_registry.tipo_for_table", return_value="almofada"), patch(
        "models.catalog_registry.fold_attributes", lambda t, p: p
    ):
        out = asyncio.run(admin.import_csv(MagicMock(state=SimpleNamespace(api_role="admin")), "cores", upload))
    update.in_.assert_called_once_with("id_modelo", ["m1"])  # sem `tipo_catalogo`, que as cores não têm
    update.eq.assert_not_called()
    assert out["updated"] == 1


def test_worker_ignores_replies_from_strangers(monkeypatch):
    from workers import email_worker

    monkeypatch.setattr(email_worker, "MAIL_FROM", "loja@diomika.test")
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"email": "Cliente@Exemplo.pt"}]
    )
    monkeypatch.setattr(email_worker, "supabase", db)
    assert email_worker._sender_allowed("m1", "cliente@exemplo.pt")
    assert email_worker._sender_allowed("m1", "loja@diomika.test")
    assert not email_worker._sender_allowed("m1", "estranho@exemplo.pt")
    # o domínio do remetente nosso dentro de outro endereço já não faz de «vendor»
    assert not email_worker._is_vendor("loja@diomika.test.evil.example")
    assert email_worker._is_vendor("Loja <LOJA@diomika.test>")


def test_worker_drops_stranger_reply_without_recording(monkeypatch):
    from workers import email_worker

    monkeypatch.setattr(email_worker, "MAIL_FROM", "loja@diomika.test")
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"email": "cliente@exemplo.pt"}]
    )
    monkeypatch.setattr(email_worker, "supabase", db)
    processed: set[str] = set()
    with patch.object(email_worker, "_is_duplicate", return_value=False):
        assert email_worker._record_message("m1", "estranho@exemplo.pt", "olá", "INBOX:1", processed) is False
    assert "INBOX:1" in processed
    db.table.return_value.insert.assert_not_called()


# --- SEG-12 e IPv6 --------------------------------------------------------------------------------


def test_edge_proxy_has_its_own_catalog_bucket():
    from core.rate_limit import _limits_for_path

    assert _limits_for_path("GET", "/categorias", "DiomikaEdge/1.0")[0] == "edge"
    assert _limits_for_path("GET", "/categorias", "Mozilla/5.0")[0] == "catalog"
    assert _limits_for_path("POST", "/contacto", "DiomikaEdge/1.0")[0] == "global"


def test_edge_flood_does_not_exhaust_the_visitor_bucket(monkeypatch):
    from starlette.requests import Request

    from core import rate_limit

    monkeypatch.setattr(rate_limit, "_hits", rate_limit.defaultdict(list))
    monkeypatch.setenv("RATE_LIMIT_EDGE_PER_MIN", "3")

    def req(ua):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/categorias",
            "client": ("198.51.100.1", 5000),
            "headers": [(b"user-agent", ua.encode())],
        }
        return Request(scope)

    results = [rate_limit.check_global_rate_limit(req("DiomikaEdge/1.0")) for _ in range(5)]
    assert [r is None for r in results] == [True, True, True, False, False]
    assert results[-1].status_code == 429
    assert rate_limit.check_global_rate_limit(req("Mozilla/5.0")) is None


def test_ipv6_clients_share_a_limit_per_slash_64():
    from core.rate_limit import _limit_key

    assert _limit_key("2001:db8:1:2:aaaa:bbbb:cccc:dddd") == _limit_key("2001:db8:1:2::1") == "2001:db8:1:2::/64"
    assert _limit_key("2001:db8:1:3::1") != _limit_key("2001:db8:1:2::1")
    assert _limit_key("203.0.113.9") == "203.0.113.9"
    assert _limit_key("unknown") == "unknown"
    assert _limit_key("::ffff:203.0.113.9") == "::ffff:203.0.113.9"


def test_bot_log_uses_the_real_client_ip(client):
    with patch("core.bot_defense.log_bot_attempt") as log:
        client.get("/health/live", headers={"User-Agent": "Scrapy/2.11", "CF-Connecting-IP": "203.0.113.50"})
    # localhost/testclient não é proxy de confiança: o IP registado é o do par, nunca o do cabeçalho forjado
    assert log.call_args.args[0] != "203.0.113.50"
