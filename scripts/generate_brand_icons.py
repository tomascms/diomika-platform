"""Gera o conjunto de ícones da marca a partir do símbolo vectorial (D azul + M vermelho).

O logótipo original é um PNG embebido num SVG (fica desfocado quando ampliado).
Aqui o símbolo é desenhado em vector e rasterizado com supersampling, para que
favicon, ícone de app e ícones PWA fiquem nítidos em qualquer tamanho.

Uso: python scripts/generate_brand_icons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BLUE = (38, 98, 152, 255)
RED = (220, 62, 56, 255)
WHITE = (255, 255, 255, 255)

# Símbolo no seu sistema de coordenadas original (57 × 69).
MARK_W, MARK_H = 57.0, 69.0
BLUE_D = [(0, 0), (33, 17), (33, 48), (0, 66), (0, 57), (24, 44), (24, 22.5), (9, 14.8), (9, 45), (0, 45)]
RED_M = [(29, 13.2), (57, 0), (57, 44), (48, 44), (48, 13.6), (33.4, 20.4)]

MARK_SVG = (
    '<path fill="#266298" d="M0 0 33 17v31L0 66v-9l24-13V22.5L9 14.8V45H0z"/>'
    '<path fill="#dc3e38" d="M29 13.2 57 0v44h-9V13.6l-14.6 6.8z"/>'
)


def render(size: int, *, background: tuple | None, mark_height: float, radius: float = 0.0) -> Image.Image:
    """Símbolo centrado num quadrado `size`; mark_height é a fracção da altura ocupada."""
    ss = 8
    big = size * ss
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if background:
        draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=radius * big, fill=background)
    scale = (mark_height * big) / MARK_H
    ox = (big - MARK_W * scale) / 2
    oy = (big - MARK_H * scale) / 2
    for poly, color in ((BLUE_D, BLUE), (RED_M, RED)):
        draw.polygon([(ox + x * scale, oy + y * scale) for x, y in poly], fill=color)
    return img.resize((size, size), Image.LANCZOS)


def favicon_svg() -> str:
    # Mosaico branco arredondado: o azul da marca mantém contraste em separadores escuros.
    s = 44 / MARK_H
    tx = (64 - MARK_W * s) / 2
    ty = (64 - MARK_H * s) / 2
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#fff"/>'
        f'<g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">{MARK_SVG}</g>'
        "</svg>\n"
    )


def mark_svg() -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 57 69">{MARK_SVG}</svg>\n'


def main() -> None:
    web = ROOT / "frontend-web" / "public"
    bo_public = ROOT / "backoffice-desktop" / "public"
    bo_electron = ROOT / "backoffice-desktop" / "electron"
    for d in (web, web / "brand", bo_public, bo_electron):
        d.mkdir(parents=True, exist_ok=True)

    (web / "favicon.svg").write_text(favicon_svg(), encoding="utf-8")
    (web / "brand" / "mark.svg").write_text(mark_svg(), encoding="utf-8")
    (bo_public / "favicon.svg").write_text(favicon_svg(), encoding="utf-8")
    (bo_public / "mark.svg").write_text(mark_svg(), encoding="utf-8")

    tile = dict(background=WHITE, mark_height=0.70, radius=0.22)
    ico_sizes = [16, 32, 48, 64]
    ico_frames = [render(s, **tile) for s in ico_sizes]
    ico_frames[-1].save(web / "favicon.ico", sizes=[(s, s) for s in ico_sizes], append_images=ico_frames[:-1])

    # PNG pequenos: alguns browsers (Opera, Safari antigo) preferem PNG a SVG.
    render(16, **tile).save(web / "favicon-16.png", optimize=True)
    render(32, **tile).save(web / "favicon-32.png", optimize=True)

    # iOS arredonda sozinho → fundo cheio, sem cantos.
    render(180, background=WHITE, mark_height=0.62).save(web / "apple-touch-icon.png", optimize=True)
    render(192, **tile).save(web / "icon-192.png", optimize=True)
    render(512, **tile).save(web / "icon-512.png", optimize=True)
    # Maskable: o SO recorta até 20% de cada lado → símbolo dentro da zona segura.
    render(512, background=WHITE, mark_height=0.52).save(web / "icon-maskable-512.png", optimize=True)

    # Ícone da app de secretária (janela + instaladores).
    app_icon = render(512, background=WHITE, mark_height=0.66, radius=0.2)
    app_icon.save(bo_electron / "icon.png", optimize=True)
    app_icon.save(
        bo_electron / "icon.ico",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)],
    )
    print("OK ícones gerados")


if __name__ == "__main__":
    main()
