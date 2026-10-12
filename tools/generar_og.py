"""Genera la imagen social (Open Graph) del juego con las piezas de assets/sprites.

Composición: bosque de noche al fondo, el conejo a la izquierda, el caldero (con su líquido, gas,
burbujas, cuchara y runa) al centro y la poción grande sobre un tronco a la derecha. Todo el
sombreado sigue el contrato de estilo (sombra teñida, abajo y a la derecha, nunca negra).

Uso (desde la raíz del repositorio):

    uv run --with pillow --with numpy python tools/generar_og.py

Escribe ``web/og-image.jpg`` (1200 × 630). La semilla es fija: el resultado es repetible.
"""

from __future__ import annotations

import argparse
import io
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H, S = 1200, 630, 2  # tamaño final y sobremuestreo interno
SUELO = 520  # línea donde pisan los personajes
NOCHE = (22, 38, 94)
LIMITE_BYTES = 300_000  # WhatsApp y otras apps descartan imágenes más pesadas


def cargar(carpeta: Path, nombre: str) -> Image.Image:
    return Image.open(carpeta / f"{nombre}.png").convert("RGBA")


def tenir(im: Image.Image, color: tuple, a: float) -> Image.Image:
    """Mezcla un color sobre los píxeles de la pieza (como ``source-atop``)."""
    d = np.asarray(im).astype(float)
    d[..., :3] = d[..., :3] * (1 - a) + np.array(color, float) * a
    return Image.fromarray(d.astype(np.uint8), "RGBA")


def alto_a(im: Image.Image, alto: float) -> Image.Image:
    return im.resize((round(im.width * alto * S / im.height), round(alto * S)), Image.LANCZOS)


def pegar(lienzo: Image.Image, im: Image.Image, x: int, y: int) -> None:
    lienzo.paste(im.convert("RGB"), (x, y), im.getchannel("A"))


def sombra(lienzo: Image.Image, im: Image.Image, x: int, y: int, k: float = 1.0) -> None:
    """Sombra de papel: teñida, desplazada abajo y a la derecha, difuminada."""
    p = round(14 * S * k)
    base = Image.new("L", (im.width + 2 * p, im.height + 2 * p), 0)
    base.paste(im.getchannel("A"), (p, p))
    a = base.filter(ImageFilter.GaussianBlur(5.5 * S * k)).point(lambda v: int(v * 0.46))
    ox, oy = x - p + round(3.2 * S * k), y - p + round(4.6 * S * k)
    lienzo.paste(Image.new("RGB", a.size, (30, 20, 34)), (ox, oy), a)


def poner(lienzo, im, cx, pie, alto, rot=0.0, k=1.0) -> tuple[int, int, Image.Image]:
    """Coloca una pieza con la base centrada en (cx, pie); devuelve su esquina y su imagen."""
    im = alto_a(im, alto)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    x, y = round(cx * S - im.width / 2), round(pie * S - im.height)
    sombra(lienzo, im, x, y, k)
    pegar(lienzo, im, x, y)
    return x, y, im


def brillo(
    lienzo: Image.Image, cx: float, cy: float, radio: float, color: tuple, fuerza: float
) -> None:
    """Resplandor aditivo (como ``lighter``), calculado solo en la zona que toca."""
    r = radio * S
    x0, y0 = max(0, round(cx * S - 2 * r)), max(0, round(cy * S - 2 * r))
    x1, y1 = min(lienzo.width, round(cx * S + 2 * r)), min(lienzo.height, round(cy * S + 2 * r))
    if x1 <= x0 or y1 <= y0:
        return
    capa = Image.new("RGB", (x1 - x0, y1 - y0), (0, 0, 0))
    c = tuple(int(v * fuerza) for v in color)
    ImageDraw.Draw(capa).ellipse(
        [cx * S - x0 - r, cy * S - y0 - r, cx * S - x0 + r, cy * S - y0 + r], fill=c
    )
    capa = capa.filter(ImageFilter.GaussianBlur(r * 0.55))
    lienzo.paste(ImageChops.add(lienzo.crop((x0, y0, x1, y1)), capa), (x0, y0))


def cielo() -> Image.Image:
    t = np.linspace(0, 1, H * S)[:, None]
    canales = [
        np.interp(t, [0, 0.45, 1], [a, b, c])
        for a, b, c in ((7, 14, 27), (11, 21, 37), (36, 56, 82))
    ]
    arr = np.repeat(np.stack(canales, axis=-1), W * S, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def luna_y_estrellas(lienzo: Image.Image, rng: random.Random) -> None:
    brillo(lienzo, 170, 105, 90, (150, 165, 230), 0.22)
    m = Image.new("L", lienzo.size, 0)
    dm = ImageDraw.Draw(m)
    dm.ellipse([(170 - 40) * S, (105 - 40) * S, (170 + 40) * S, (105 + 40) * S], fill=255)
    dm.ellipse([(188 - 37) * S, (92 - 37) * S, (188 + 37) * S, (92 + 37) * S], fill=0)  # creciente
    lienzo.paste(Image.new("RGB", lienzo.size, (244, 237, 214)), (0, 0), m)
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    for _ in range(130):
        x, y, r = rng.random() * W, rng.random() * 360, 0.7 + rng.random() * 1.6
        dc.ellipse(
            [(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S],
            fill=(223, 230, 255, int(60 + rng.random() * 150)),
        )
    lienzo.paste(capa.convert("RGB"), (0, 0), capa.getchannel("A"))


def bosque_lejano(lienzo: Image.Image, im: Image.Image) -> None:
    t = tenir(im, NOCHE, 0.62)
    t = t.resize((round(t.width * 340 * S / t.height), 340 * S), Image.LANCZOS)
    espejo, x, i = t.transpose(Image.FLIP_LEFT_RIGHT), -90 * S, 0
    while x < W * S:  # mosaico espejado: la costura no se nota
        pegar(lienzo, t if i % 2 == 0 else espejo, x, (SUELO + 40) * S - t.height)
        x, i = x + t.width, i + 1


def pinos(lienzo: Image.Image, im: Image.Image) -> None:
    for cx, alto, flip, a in (
        (60, 560, 0, 0.30),
        (350, 380, 1, 0.5),
        (700, 330, 0, 0.55),
        (1130, 590, 1, 0.30),
        (840, 400, 1, 0.45),
    ):
        p = alto_a(tenir(im, NOCHE, a), alto)
        if flip:
            p = p.transpose(Image.FLIP_LEFT_RIGHT)
        sombra(lienzo, p, round(cx * S - p.width / 2), (SUELO + 24) * S - p.height, 0.8)
        pegar(lienzo, p, round(cx * S - p.width / 2), (SUELO + 24) * S - p.height)


def suelo(lienzo: Image.Image, im: Image.Image, rng: random.Random) -> None:
    top = (SUELO - 14) * S
    alto = H * S - top
    t = tenir(im, NOCHE, 0.4).convert("RGB")
    t = t.resize((round(t.width * alto / t.height), alto), Image.LANCZOS)
    espejo, tira, x, i = t.transpose(Image.FLIP_LEFT_RIGHT), Image.new("RGB", (W * S, alto)), 0, 0
    while x < W * S:
        tira.paste(t if i % 2 == 0 else espejo, (x, 0))
        x, i = x + t.width, i + 1
    onda = [
        (x, 6 * S + 5 * S * math.sin(x / (W * S) * math.tau * 9)) for x in range(0, W * S + 1, 8)
    ]
    mascara = Image.new("L", tira.size, 0)
    ImageDraw.Draw(mascara).polygon([*onda, (W * S, alto), (0, alto)], fill=255)
    lienzo.paste(tira, (0, top), mascara)
    d = ImageDraw.Draw(lienzo)
    d.line([(x, top + y) for x, y in onda], fill=(67, 35, 14), width=4 * S)
    for _ in range(46):  # matas de pasto del código del juego
        x = rng.random() * W * S
        y = top + 8 * S + 5 * S * math.sin(x / (W * S) * math.tau * 9)
        for dx, dy in ((-6, -12), (0, -15), (6, -11)):
            d.line(
                [(x + dx * S * 0.4, y), (x + dx * S, y + dy * S)], fill=(36, 79, 61), width=3 * S
            )


def luciernagas(lienzo: Image.Image, rng: random.Random) -> None:
    for _ in range(26):
        brillo(lienzo, rng.random() * W, 190 + rng.random() * 320, 9, (200, 235, 90), 0.8)


def tronco(lienzo: Image.Image, cx: int, tope: int) -> None:
    """Tronco de papel: tiras de corteza con bordes ondulados y tapa con anillos."""
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    ancho, base = 205, SUELO + 12
    for i, (col, dx, w) in enumerate(((107, 60, 30), (139, 79, 39), (166, 100, 52))):
        izq, der = cx - ancho / 2 + dx * 0, cx + ancho / 2
        pts = []
        for y in range(tope, base + 1, 4):  # cada capa de papel es un poco más angosta y ondulada
            pts.append(((izq + 10 * i + 6 * math.sin(y / 13 + i)) * S, y * S))
        for y in range(base, tope - 1, -4):
            pts.append(((der - 10 * i + 6 * math.sin(y / 11 + 2 * i)) * S, y * S))
        d.polygon(pts, fill=(col, dx, w, 255))
    ry = 27
    d.ellipse(
        [(cx - ancho / 2 - 4) * S, (tope - ry) * S, (cx + ancho / 2 + 4) * S, (tope + ry) * S],
        fill=(160, 105, 55, 255),
    )
    d.ellipse(
        [(cx - ancho / 2) * S, (tope - ry + 3) * S, (cx + ancho / 2) * S, (tope + ry - 1) * S],
        fill=(224, 169, 106, 255),
    )
    for k in (0.74, 0.5, 0.26):
        d.ellipse(
            [
                (cx - ancho / 2 * k) * S,
                (tope + 1 - ry * k) * S,
                (cx + ancho / 2 * k) * S,
                (tope + 1 + ry * k) * S,
            ],
            outline=(200, 138, 76, 255),
            width=3 * S,
        )
    capa = tenir(capa, NOCHE, 0.12)
    sombra(lienzo, capa, 0, 0, 1.0)
    pegar(lienzo, capa, 0, 0)


def liquido(im: Image.Image) -> tuple[float, float, float, float] | None:
    """Caja del líquido morado (parte alta del dibujo): centro x, centro y, ancho y alto (px)."""
    d = np.asarray(im).astype(int)[: int(im.height * 0.45)]
    r, g, b, a = d[..., 0], d[..., 1], d[..., 2], d[..., 3]
    m = (a > 200) & (b > 120) & (r > 90) & (g < 110) & (b > g * 1.6)
    if m.sum() < 40:
        return None
    ys, xs = np.nonzero(m)
    return (
        (xs.min() + xs.max() + 1) / 2,
        (ys.min() + ys.max() + 1) / 2,
        xs.max() - xs.min() + 1,
        ys.max() - ys.min() + 1,
    )


def caldero(
    lienzo: Image.Image, im: Image.Image, cuchara: Image.Image, cx: int, rng: random.Random
) -> None:
    alto = 300
    x, y, tam = poner(lienzo, im, cx, SUELO + 12, alto)
    f = tam.height / im.height
    liq = liquido(im) or (im.width / 2, im.height * 0.1, im.width * 0.7, im.height * 0.11)
    lx, ly, lw, lh = x + liq[0] * f, y + liq[1] * f, liq[2] * f * 1.04, liq[3] * f * 1.12
    d = ImageDraw.Draw(lienzo)
    d.ellipse(
        [lx - lw / 2, ly - lh / 2, lx + lw / 2, ly + lh / 2], fill=(40, 225, 210)
    )  # líquido animado
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    dc.ellipse(
        [lx - lw * 0.32, ly - lh * 0.32, lx + lw * 0.1, ly - lh * 0.02], fill=(255, 255, 255, 115)
    )
    lienzo.paste(capa.convert("RGB"), (0, 0), capa.getchannel("A"))
    brillo(lienzo, lx / S, ly / S, lw / S * 0.55, (60, 230, 255), 0.45)
    # cuchara: se hunde por su eje; lo que queda bajo la superficie no se dibuja
    c = alto_a(cuchara, lw / S * 1.3)
    cx0, cy0 = lx + lw * 0.1 - c.width * 0.42, ly - c.height * 0.62
    a = c.getchannel("A")
    ImageDraw.Draw(a).rectangle([0, round(ly - cy0), c.width, c.height], fill=0)
    c.putalpha(a)
    sombra(lienzo, c, round(cx0), round(cy0), 0.7)
    pegar(lienzo, c, round(cx0), round(cy0))
    # runa de ocho puntas en la panza, iluminada
    rx, ry = x + tam.width / 2 - 0.16 * tam.width, y + tam.height / 2 - 0.02 * tam.height
    lado = lw * 0.3
    brillo(lienzo, rx / S, ry / S, lado / S * 1.2, (60, 230, 255), 0.5)
    halo = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    for grosor, col in ((10 * S, (190, 246, 255, 120)), (4 * S, (67, 230, 255, 255))):
        for ang in (0.3, -0.3, 0.3 + math.pi / 4):
            lado2 = lado * (0.33 if ang > 0.4 else 1)
            pts = [
                (
                    rx + math.cos(ang + k * math.pi / 2 + math.pi / 4) * lado2 / math.sqrt(2) * 1.0,
                    ry + math.sin(ang + k * math.pi / 2 + math.pi / 4) * lado2 / math.sqrt(2) * 1.0,
                )
                for k in range(4)
            ]
            ImageDraw.Draw(halo).polygon(pts, outline=col, width=grosor)
    lienzo.paste(halo.convert("RGB"), (0, 0), halo.getchannel("A"))
    # burbujas y gas
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    for _ in range(8):
        bx, by, r = (
            lx + (rng.random() - 0.5) * lw * 0.8,
            ly - 6 * S - rng.random() * 70 * S,
            (5 + rng.random() * 7) * S,
        )
        dc.ellipse([bx - r, by - r, bx + r, by + r], fill=(40, 225, 210, 215))
        dc.ellipse(
            [bx - r * 0.55, by - r * 0.55, bx - r * 0.15, by - r * 0.15], fill=(255, 255, 255, 150)
        )
    lienzo.paste(capa.convert("RGB"), (0, 0), capa.getchannel("A"))
    gas = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    dg = ImageDraw.Draw(gas)
    for dx, subida, r in ((-70, 70, 38), (0, 130, 48), (68, 190, 40)):
        gx, gy = lx + dx * S, ly - subida * S
        dg.ellipse(
            [gx - r * S, gy - r * S * 0.8, gx + r * S, gy + r * S * 0.8], fill=(205, 245, 255, 55)
        )
    gas = gas.filter(ImageFilter.GaussianBlur(12 * S))
    lienzo.paste(gas.convert("RGB"), (0, 0), gas.getchannel("A"))


def destellos(lienzo: Image.Image, puntos: list[tuple[float, float, float]]) -> None:
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for x, y, r in puntos:  # estrellas de cuatro puntas de papel dorado
        p = [
            (x, y - r),
            (x + r * 0.25, y - r * 0.25),
            (x + r, y),
            (x + r * 0.25, y + r * 0.25),
            (x, y + r),
            (x - r * 0.25, y + r * 0.25),
            (x - r, y),
            (x - r * 0.25, y - r * 0.25),
        ]
        d.polygon([(a * S, b * S) for a, b in p], fill=(244, 196, 48, 255))
    sombra(lienzo, capa, 0, 0, 0.5)
    lienzo.paste(capa.convert("RGB"), (0, 0), capa.getchannel("A"))


def vineta_y_grano(lienzo: Image.Image) -> Image.Image:
    a = np.asarray(lienzo).astype(float)
    yy, xx = np.mgrid[0 : lienzo.height, 0 : lienzo.width]
    d = np.hypot((xx / lienzo.width - 0.5) * 1.15, (yy / lienzo.height - 0.5) * 1.3)
    a *= (1 - 0.42 * np.clip((d - 0.38) / 0.5, 0, 1) ** 1.6)[..., None]
    a += np.random.default_rng(3).normal(0, 3.2, a.shape[:2])[..., None]  # grano de cartulina
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def componer(carpeta: Path) -> Image.Image:
    rng = random.Random(7)
    lienzo = cielo()
    luna_y_estrellas(lienzo, rng)
    bosque_lejano(lienzo, cargar(carpeta, "bosque_capas"))
    pinos(lienzo, cargar(carpeta, "pinos"))
    suelo(lienzo, cargar(carpeta, "suelo"), rng)
    luciernagas(lienzo, rng)
    tope = 462
    tronco(lienzo, 985, tope)
    brillo(lienzo, 985, 300, 120, (90, 220, 120), 0.2)
    poner(lienzo, cargar(carpeta, "pocion_verde"), 985, tope + 8, 300)
    destellos(lienzo, [(885, 195, 16), (1090, 250, 12), (1040, 150, 18), (900, 330, 8)])
    caldero(lienzo, cargar(carpeta, "caldero"), cargar(carpeta, "cuchara"), 600, rng)
    poner(lienzo, cargar(carpeta, "pers_conejo"), 235, SUELO + 16, 305, rot=-3)
    final = vineta_y_grano(lienzo).resize((W, H), Image.LANCZOS)
    return final


def guardar(im: Image.Image, ruta: Path) -> int:
    for q in (90, 85, 80, 74):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= LIMITE_BYTES:
            break
    ruta.write_bytes(buf.getvalue())
    return buf.tell()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Genera web/og-image.jpg a partir de assets/sprites.")
    ap.add_argument("--sprites", type=Path, default=Path("assets/sprites"))
    ap.add_argument("--salida", type=Path, default=Path("web/og-image.jpg"))
    a = ap.parse_args(argv)
    faltan = [
        n
        for n in (
            "bosque_capas",
            "pinos",
            "suelo",
            "pocion_verde",
            "caldero",
            "cuchara",
            "pers_conejo",
        )
        if not (a.sprites / f"{n}.png").exists()
    ]
    if faltan:
        print(f"Faltan piezas en {a.sprites}: {', '.join(faltan)}")
        return 2
    n = guardar(componer(a.sprites), a.salida)
    print(f"{a.salida} ({W}x{H}, {n / 1000:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
