"""Identificação legal da Diomika para os emails (CSC, art. 171.º; DL 7/2004, art. 10.º; DL 156/2005, art. 5.º-B).

Espelha COMPANY, ADR_ENTITY e COMPLAINTS_BOOK_URL de frontend-web/src/lib/constants.js: mudar nos dois
(tests/test_quote_b2b.py compara-os). Sem email público nem capital social até o cliente os dar
(ficha do cliente, Parte D, itens 1 e 2): quando os der, preencher aqui e na loja.
"""
from __future__ import annotations

SITE = "https://www.diomika.com"
LEGAL_NAME = "DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA"
REGISTRY = "Conservatória do Registo Comercial"
ADDRESS = "Rua da Quintã, n.º 89"
POSTAL = "4805-116 Caldas das Taipas"
MUNICIPALITY = "Guimarães"
NIPC = "508 651 557"
PHONE = "935 745 663"
SHARE_CAPITAL = ""
EMAIL = ""
COMPLAINTS_BOOK_URL = "https://www.livroreclamacoes.pt"
ADR_NAME = "TRIAVE – Centro de Arbitragem de Conflitos de Consumo do Ave, Tâmega e Sousa"
ADR_SITE = "www.triave.pt"

# Custo da chamada a indicar junto do número (DL 59/2021, art. 4.º): 2… é rede fixa, 9… é móvel.
_CALL_COST = {"2": "Chamada para a rede fixa nacional", "9": "Chamada para a rede móvel nacional"}


def legal_signature() -> str:
    """Assinatura dos emails comerciais: identificação, contacto, Livro de Reclamações e RAL."""
    phone_note = _CALL_COST.get(PHONE.replace(" ", "")[:1], "")
    lines = [
        LEGAL_NAME,
        "Sociedade unipessoal por quotas",
        f"Sede: {ADDRESS}, {POSTAL}, {MUNICIPALITY}",
        f"Matrícula na {REGISTRY} e NIPC {NIPC}",
    ]
    if SHARE_CAPITAL:
        lines.append(f"Capital social {SHARE_CAPITAL}")
    lines.append(f"Telefone {PHONE} ({phone_note})" if phone_note else f"Telefone {PHONE}")
    if EMAIL:
        lines.append(f"Email {EMAIL}")
    lines += [
        f"Contacto electrónico: formulário de contacto em {SITE}/contacto",
        "",
        f"Livro de Reclamações Eletrónico: {COMPLAINTS_BOOK_URL}",
        f"Em caso de litígio de consumo, pode recorrer ao {ADR_NAME} ({ADR_SITE}).",
    ]
    return "\n".join(lines)
