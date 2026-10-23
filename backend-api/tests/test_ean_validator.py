"""Testes para validação de EAN-13 checksum."""
import pytest
from utils.ean_validator import validate_ean_checksum, format_ean, get_ean_error_message


class TestEANChecksum:
    """Testes de validação EAN-13."""

    def test_valid_ean(self):
        """EAN válido com checksum correto."""
        # Exemplo real: 5901234123457 é um EAN-13 válido
        assert validate_ean_checksum("5901234123457") is True

    def test_valid_ean_other(self):
        """Outro EAN válido."""
        assert validate_ean_checksum("4006381333931") is True

    def test_invalid_checksum(self):
        """EAN com checksum errado."""
        assert validate_ean_checksum("5901234123456") is False  # Checksum deveria ser 7, não 6

    def test_invalid_length(self):
        """EAN com comprimento errado."""
        assert validate_ean_checksum("590123412345") is False   # 12 dígitos
        assert validate_ean_checksum("59012341234567") is False  # 14 dígitos

    def test_invalid_non_numeric(self):
        """EAN com caracteres não-numéricos."""
        assert validate_ean_checksum("590123412345X") is False
        assert validate_ean_checksum("5901234-123457") is False

    def test_empty_ean(self):
        """EAN vazio."""
        assert validate_ean_checksum("") is False
        assert validate_ean_checksum(None) is False

    def test_leading_trailing_spaces(self):
        """O checksum tolera espaços à volta (EAN colado de uma folha de cálculo);
        o schema do produto (^\d{13}$) é que impede guardar com espaços."""
        assert validate_ean_checksum(" 5901234123457 ") is True
        assert validate_ean_checksum("5901234 123457") is False


class TestEANFormat:
    """Testes de formatação EAN."""

    def test_format_valid_ean(self):
        """Formata EAN válido."""
        assert format_ean("5901234123457") == "5901234123457"

    def test_format_removes_hyphens(self):
        """Remove hífens durante formatação."""
        assert format_ean("5901234-123457") == "5901234123457"

    def test_format_removes_spaces(self):
        """Remove espaços durante formatação."""
        assert format_ean("5901234 123457") == "5901234123457"

    def test_format_empty(self):
        """EAN vazio retorna None."""
        assert format_ean("") is None
        assert format_ean(None) is None

    def test_format_invalid_checksum(self):
        """EAN com checksum inválido retorna None."""
        assert format_ean("5901234123456") is None

    def test_format_wrong_length(self):
        """EAN com comprimento errado retorna None."""
        assert format_ean("590123412345") is None
        assert format_ean("59012341234567") is None


class TestEANErrorMessage:
    """Testes de mensagens de erro EAN."""

    def test_empty_is_ok(self):
        """EAN vazio é permitido (opcional)."""
        assert get_ean_error_message("") is None
        assert get_ean_error_message(None) is None

    def test_valid_no_error(self):
        """EAN válido não gera erro."""
        assert get_ean_error_message("5901234123457") is None

    def test_invalid_checksum_error(self):
        """EAN com checksum inválido gera erro."""
        error = get_ean_error_message("5901234123456")
        assert error is not None
        assert "checksum" in error.lower()

    def test_invalid_length_error(self):
        """EAN com comprimento errado gera erro."""
        error = get_ean_error_message("590123412345")
        assert error is not None
        assert "13 dígitos" in error

    def test_non_numeric_error(self):
        """EAN não-numérico gera erro."""
        error = get_ean_error_message("590123412345X")
        assert error is not None
        assert "dígitos" in error.lower()


class TestEANEdgeCases:
    """Testes de casos extremos."""

    def test_ean_all_zeros(self):
        """EAN com todos zeros (exceto checksum)."""
        # 0000000000000 é um caso extremo
        assert validate_ean_checksum("0000000000000") is True

    def test_ean_max_digits(self):
        """EAN com dígitos máximos."""
        # 9999999999999 é máximo válido
        assert validate_ean_checksum("9999999999990") is False  # Inválido
        # Calcular checksum correto
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate("999999999999"))
        check = (10 - (total % 10)) % 10
        valid_ean = "999999999999" + str(check)
        assert validate_ean_checksum(valid_ean) is True
