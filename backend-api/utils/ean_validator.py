"""EAN-13 checksum validation and formatting."""


def validate_ean_checksum(ean: str) -> bool:
    """
    Valida checksum EAN-13 (13 dígitos).

    Algoritmo: Weighted sum (pesos alternados 1,3) modulo 10.
    Returns: True se checksum é válido, False caso contrário.
    """
    ean = str(ean or "").strip()

    # Apenas dígitos, exactamente 13 caracteres
    if not ean.isdigit() or len(ean) != 13:
        return False

    # Pesos: 1,3,1,3,1,3,1,3,1,3,1,3,1
    # Calcula sum dos primeiros 12 dígitos com pesos alternados
    total = 0
    for i in range(12):
        weight = 1 if i % 2 == 0 else 3
        total += int(ean[i]) * weight

    # Check digit = (10 - (sum mod 10)) mod 10
    check_digit = (10 - (total % 10)) % 10

    return int(ean[12]) == check_digit


def format_ean(ean: str) -> str | None:
    """
    Formata e valida EAN, retornando None se inválido.
    Remove espaços, hífens e valida checksum.
    """
    if not ean:
        return None

    # Remove caracteres não-dígitos
    cleaned = ''.join(c for c in str(ean) if c.isdigit())

    # Apenas 13 dígitos aceitos
    if len(cleaned) != 13:
        return None

    # Valida checksum
    if not validate_ean_checksum(cleaned):
        return None

    return cleaned


def get_ean_error_message(ean: str) -> str | None:
    """
    Retorna mensagem de erro se EAN for inválido, None se válido.
    """
    ean_clean = str(ean or "").strip()

    if not ean_clean:
        return None  # Empty é OK (opcional)

    # Remove caracteres de formatação
    digits_only = ''.join(c for c in ean_clean if c.isdigit())

    if not digits_only:
        return "EAN deve conter dígitos."

    if len(digits_only) != 13:
        return f"EAN deve ter 13 dígitos (tem {len(digits_only)})."

    if not validate_ean_checksum(digits_only):
        return "EAN checksum inválido."

    return None
