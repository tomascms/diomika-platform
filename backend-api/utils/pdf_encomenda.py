"""PDF para encomendas e orcamentos."""
from __future__ import annotations

from io import BytesIO
from typing import Any


def build_pedido_pdf(
    titulo: str,
    cliente: str,
    linhas: list[dict[str, Any]],
    extra_linhas: list[str] | None = None,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    height = A4[1]
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, titulo)
    y -= 1 * cm
    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, y, f"Cliente: {cliente}")
    y -= 0.8 * cm

    if extra_linhas:
        c.setFont("Helvetica", 10)
        for line in extra_linhas:
            c.drawString(2 * cm, y, line[:100])
            y -= 0.5 * cm
        y -= 0.2 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Linhas")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)

    for i, linha in enumerate(linhas, 1):
        if y < 3 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", 10)
        alt = linha.get("altura") or ""
        alt_part = f" | Altura {alt}" if alt else ""
        texto = (
            f"{i}. {linha.get('modelo', '')} {linha.get('dimensoes', '')}{alt_part} | "
            f"Cor {linha.get('numero_cor')} ({linha.get('cor_nome', '')}) | "
            f"EAN {linha.get('ean')} | Qtd {linha.get('quantidade')}"
        )
        c.drawString(2 * cm, y, texto[:110])
        y -= 0.55 * cm

    c.save()
    return buf.getvalue()


def build_encomenda_pdf(referencia: str, linhas: list[dict[str, Any]], observacoes: str | None = None) -> bytes:
    extra = [f"Notas: {observacoes}"] if observacoes else None
    return build_pedido_pdf("Diomika — Encomenda", referencia, linhas, extra)
