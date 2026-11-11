"""SEG-16: o que deploy/update_signing.py assina é o que o backoffice (Node) verifica."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy"))
import update_signing  # noqa: E402


@pytest.fixture(autouse=True)
def _passphrase(monkeypatch):
    monkeypatch.setenv("DIOMIKA_UPDATE_KEY_PASSPHRASE", "senha-de-teste")

VERIFY = (
    "const {verifyManifest, manifestDescribes}=require(process.argv[1]);"
    "const fs=require('fs');"
    "const manifest=fs.readFileSync(process.argv[2]);const sig=fs.readFileSync(process.argv[3],'utf8');"
    "const key=fs.readFileSync(process.argv[4],'utf8');"
    "console.log(JSON.stringify({ok:verifyManifest(manifest,sig,key),"
    "describes:manifestDescribes(manifest,{version:'1.4.0',sha512:'AbC+/123=='})}))"
)


@pytest.mark.skipif(shutil.which("node") is None, reason="sem Node")
def test_python_signature_verifies_in_node_and_tampering_does_not(tmp_path):
    key = tmp_path / "k.pem"
    assert update_signing.main(["x", "keygen", str(key)]) == 0
    pub = tmp_path / "pub.pem"
    pub.write_text(update_signing.public_pem(update_signing.load_private(key)), encoding="ascii")
    manifest = tmp_path / "latest.yml"
    manifest.write_text("version: 1.4.0\nsha512: AbC+/123==\n", encoding="utf-8")
    sig = update_signing.sign_file(manifest, key)
    module = str(ROOT / "backoffice-desktop" / "electron" / "update-signature.cjs")

    def check():
        out = subprocess.run(
            ["node", "-e", VERIFY, module, str(manifest), str(sig), str(pub)], capture_output=True, text=True, check=True
        )
        return json.loads(out.stdout)

    assert check() == {"ok": True, "describes": True}
    manifest.write_text("version: 1.4.0\nsha512: OUTRO==\n", encoding="utf-8")
    assert check()["ok"] is False


def test_the_embedded_public_key_is_never_replaced_silently(tmp_path):
    key = tmp_path / "k.pem"
    update_signing.main(["x", "keygen", str(key)])
    assert update_signing.main(["x", "keygen", str(key)]) == 1  # não substitui uma chave existente


def test_the_private_key_is_encrypted_and_private(tmp_path):
    import os
    import stat

    key = tmp_path / "pasta" / "k.pem"
    update_signing.main(["x", "keygen", str(key)])
    assert b"ENCRYPTED" in key.read_bytes()
    if os.name != "nt":
        assert stat.S_IMODE(key.stat().st_mode) == 0o600
        assert stat.S_IMODE(key.parent.stat().st_mode) == 0o700
    assert update_signing.load_private(key)  # abre com a senha certa
    os.environ["DIOMIKA_UPDATE_KEY_PASSPHRASE"] = "outra"
    with pytest.raises(ValueError):
        update_signing.load_private(key)


def test_protect_encrypts_an_existing_plain_key_in_place(tmp_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    path = tmp_path / "plain.pem"
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    assert update_signing.main(["x", "protect", str(path)]) == 0
    assert b"ENCRYPTED" in path.read_bytes()
    assert update_signing.public_pem(update_signing.load_private(path)) == update_signing.public_pem(key)
