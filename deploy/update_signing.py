#!/usr/bin/env python3
"""Assinatura dos manifestos de actualização do backoffice (SEG-16, 0 €).

A chave privada Ed25519 vive só no PC de quem publica, fora do repositório; a chave pública está embutida no
executável (backoffice-desktop/electron/update-key.cjs). O backoffice só instala uma actualização se o `latest*.yml`
que a descreve tiver uma assinatura válida: quem comprometer a VM não consegue distribuir um executável.

  python deploy/update_signing.py keygen CAMINHO_DA_CHAVE_PRIVADA   # cria o par; imprime a chave pública
  python deploy/update_signing.py protect CAMINHO_DA_CHAVE_PRIVADA  # cifra com senha uma chave que não o esteja
  python deploy/update_signing.py sign latest.yml CAMINHO_DA_CHAVE  # escreve latest.yml.sig (base64)

A chave privada é cifrada com uma senha (DIOMIKA_UPDATE_KEY_PASSPHRASE, ou pergunta no terminal), criada com
permissões 0600 numa pasta 0700 e nunca substitui um ficheiro existente. (Em Windows o modo é ignorado: a pasta
do utilizador é o que protege.)
"""
from __future__ import annotations

import base64
import getpass
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _passphrase(confirm: bool = False) -> bytes:
    value = os.environ.get("DIOMIKA_UPDATE_KEY_PASSPHRASE")
    if value is None:
        value = getpass.getpass("Senha da chave de assinatura: ")
        if confirm and getpass.getpass("Repita a senha: ") != value:
            raise ValueError("As senhas não coincidem.")
    if not value:
        raise ValueError("A senha não pode ser vazia.")
    return value.encode()


def load_private(path: str | Path) -> Ed25519PrivateKey:
    data = Path(path).read_bytes()
    encrypted = b"ENCRYPTED" in data
    key = serialization.load_pem_private_key(data, password=_passphrase() if encrypted else None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("A chave tem de ser Ed25519.")
    return key


def public_pem(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def sign_bytes(data: bytes, key: Ed25519PrivateKey) -> str:
    return base64.b64encode(key.sign(data)).decode()


def sign_file(manifest: Path, key_path: str | Path, out: Path | None = None) -> Path:
    out = out or manifest.with_name(manifest.name + ".sig")
    out.write_text(sign_bytes(manifest.read_bytes(), load_private(key_path)) + "\n", encoding="ascii")
    return out


def write_private(key: Ed25519PrivateKey, target: Path, *, replace: bool = False) -> None:
    """PEM cifrado, 0600, pasta 0700. Sem `replace`, falha se o ficheiro já existir (O_EXCL)."""
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(_passphrase(True))
    )
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if replace:
        tmp = target.with_name(target.name + ".tmp")
        tmp.unlink(missing_ok=True)
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as fh:
            fh.write(pem)
        os.replace(tmp, target)
        return
    with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as fh:
        fh.write(pem)


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "keygen":
        target = Path(argv[2])
        key = Ed25519PrivateKey.generate()
        try:
            write_private(key, target)
        except FileExistsError:
            print(f"ERRO: {target} já existe; não se substitui uma chave.")
            return 1
        print(public_pem(key))
        return 0
    if len(argv) == 3 and argv[1] == "protect":
        target = Path(argv[2])
        if b"ENCRYPTED" in target.read_bytes():
            print("A chave já está cifrada.")
            return 0
        write_private(load_private(target), target, replace=True)
        print(f"Chave cifrada: {target}")
        return 0
    if len(argv) == 4 and argv[1] == "sign":
        print(sign_file(Path(argv[2]), argv[3]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
