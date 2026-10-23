import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from utils.storage import upload_bytes


def generate_ean13(ean_code: str):
    """Gera codigo de barras EAN-13 e envia para o Supabase Storage."""
    ean_code = ean_code.strip()
    if len(ean_code) != 13:
        return None

    try:
        ean_class = barcode.get_barcode_class("ean13")
        ean_instance = ean_class(ean_code[:12], writer=ImageWriter())
        expected_ean = ean_instance.get_fullcode()

        if expected_ean != ean_code:
            return ("INVALID_CHECKSUM", expected_ean)

        buffer = BytesIO()
        ean_instance.write(buffer, options={"write_text": True})
        buffer.seek(0)

        dest_path = f"barcodes/{expected_ean}.png"
        # optimize=False: um código de barras recomprimido/redimensionado
        # como se fosse uma fotografia deixa de ser legível por um scanner.
        public_url = upload_bytes(buffer.read(), dest_path, "image/png", optimize=False)
        return (public_url, expected_ean)
    except barcode.errors.BarcodeError:
        return None


def apply_barcode_url(data: dict) -> None:
    """Gera barcode_url a partir do EAN. Levanta ValueError se checksum invalido."""
    ean = (data.get("ean") or "").strip()
    if len(ean) != 13:
        return

    result = generate_ean13(ean)
    if result is None:
        return
    if isinstance(result, tuple) and result[0] == "INVALID_CHECKSUM":
        raise ValueError(f"EAN invalido. Digito de controlo correcto: {result[1]}")
    if isinstance(result, tuple):
        data["barcode_url"] = result[0]
