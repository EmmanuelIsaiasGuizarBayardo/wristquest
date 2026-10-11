"""Inyecta el arte del juego (WebP en base64) dentro de web/wristquest.html, sin pasar por el chat.

Uso (desde la raíz del repositorio):

    uv run --with pillow python tools/inyectar_assets.py

Lee los PNG de ``assets/sprites/`` (uno por pieza, fondo transparente), los reduce si son enormes,
los codifica como WebP con transparencia y reemplaza el bloque entre ``/*ASSETS_BEGIN*/`` y
``/*ASSETS_END*/`` del HTML. Para cambiar una pieza basta con reemplazar su PNG (mismo nombre) y
volver a correr el script. El juego sigue funcionando sin arte: si el bloque está vacío, usa el
dibujo por código.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

MARCAS = re.compile(r"/\*ASSETS_BEGIN\*/.*?/\*ASSETS_END\*/", re.DOTALL)
AVISO_MB = 4.0


def codificar(png: Path, max_lado: int) -> str:
    """PNG a data URI WebP; reduce con filtro de calidad si algún lado supera ``max_lado``."""
    im = Image.open(png).convert("RGBA")
    if max(im.size) > max_lado:
        r = max_lado / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=86, alpha_quality=100, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Inyecta el arte en el HTML del juego.")
    ap.add_argument("--sprites", type=Path, default=Path("assets/sprites"))
    ap.add_argument("--html", type=Path, default=Path("web/wristquest.html"))
    ap.add_argument("--max-lado", type=int, default=900, help="lado máximo en píxeles")
    a = ap.parse_args(argv)
    pngs = sorted(a.sprites.glob("*.png"))
    if not pngs:
        print(f"No hay PNG en {a.sprites}")
        return 2
    if not a.html.exists():
        print(f"No existe {a.html}")
        return 2
    activos = {p.stem: codificar(p, a.max_lado) for p in pngs}
    bloque = (
        "/*ASSETS_BEGIN*/const ASSETS = "
        + json.dumps(activos, separators=(",", ":"))
        + ";/*ASSETS_END*/"
    )
    html = a.html.read_text(encoding="utf-8")
    if not MARCAS.search(html):
        print("El HTML no tiene las marcas /*ASSETS_BEGIN*/ ... /*ASSETS_END*/")
        return 2
    # la función de reemplazo evita que las diagonales del base64 se interpreten como escapes
    a.html.write_text(MARCAS.sub(lambda _: bloque, html, count=1), encoding="utf-8", newline="\n")
    mb = len(bloque) / 1e6
    print(f"{len(activos)} piezas inyectadas en {a.html} ({mb:.2f} MB de arte)")
    if mb > AVISO_MB:
        print(f"Aviso: más de {AVISO_MB:g} MB de arte; baja --max-lado para aligerar el HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
