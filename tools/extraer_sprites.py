"""Recorta los sprites de las hojas de arte, quita el fondo blanco sin halo y los guarda en PNG.

Uso: uv run --with pillow --with scipy python extraer_sprites.py <carpeta_hojas> <carpeta_salida>
Cada sprite se define por una caja (x0, y0, x1, y1) en su hoja; se toman los componentes conectados
que caen dentro de la caja, así un vecino cercano nunca se cuela en el recorte.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

F, A, B = "Fondos_WristQuest.png", "Copia_de_WristQuest__1_.png", "Copia_de_WristQuest.png"
# nombre: (hoja, caja, modo)  modo: "cut" quita el fondo; "rect" conserva el rectángulo opaco
SPRITES = {
    "pinos": (F, (119, 30, 419, 381), "cut"),
    "bosque_capas": (F, (457, 31, 1229, 406), "cut"),
    "suelo": (F, (1274, 47, 1811, 407), "rect"),
    "esc_casa": (F, (109, 430, 647, 728), "rect"),
    "esc_hongo": (F, (1274, 430, 1811, 728), "rect"),
    "esc_rio": (F, (108, 751, 646, 1050), "rect"),
    "esc_noche": (F, (690, 749, 1229, 1043), "rect"),
    "esc_sol": (F, (1274, 748, 1811, 1047), "rect"),
    "mano_flexion": (A, (20, 31, 407, 366), "cut"),
    "mano_extension": (A, (20, 710, 455, 1045), "cut"),
    "mano_dorso": (A, (448, 43, 774, 399), "cut"),
    "mano_palma": (A, (519, 702, 755, 1044), "cut"),
    "brazo_giro": (A, (20, 410, 597, 668), "cut"),
    "cadenas": (A, (823, 20, 1564, 384), "cut"),
    "avatar": (A, (1619, 173, 1810, 367), "cut"),
    "buho": (A, (810, 428, 1085, 735), "cut"),
    "ardilla": (A, (1115, 427, 1395, 744), "cut"),
    "oso": (A, (1475, 470, 1843, 1036), "cut"),
    "cofre": (A, (814, 773, 1189, 1040), "cut"),
    "pocion_lava": (B, (20, 28, 140, 314), "cut"),
    "pocion_vid": (B, (167, 26, 346, 319), "cut"),
    "pocion_corazon": (B, (377, 22, 572, 314), "cut"),
    "pocion_gema": (B, (607, 35, 785, 317), "cut"),
    "pocion_verde": (B, (827, 60, 1060, 318), "cut"),
    "pocion_hongo": (B, (1132, 41, 1476, 310), "cut"),
    "pocion_h": (B, (1509, 38, 1760, 316), "cut"),
    "pers_jabali": (B, (24, 356, 322, 641), "cut"),
    "pers_mapache": (B, (351, 358, 608, 644), "cut"),
    "pers_rana": (B, (646, 354, 916, 671), "cut"),
    "pers_conejo": (B, (941, 353, 1197, 645), "cut"),
    "pers_castor": (B, (1225, 356, 1505, 646), "cut"),
    "caldero": (B, (1541, 347, 1891, 734), "cut"),
    "carton": (B, (49, 667, 325, 1046), "cut"),
    "cristal": (B, (369, 894, 526, 1053), "cut"),
    "mortero": (B, (554, 918, 744, 1052), "cut"),
    "roca_runica": (B, (778, 868, 960, 1056), "cut"),
    "pocion_azul": (B, (992, 815, 1182, 1048), "cut"),
    "llave": (B, (1222, 887, 1370, 1045), "cut"),
    "libro": (B, (1420, 863, 1613, 1053), "cut"),
    "runa_chica": (B, (1640, 879, 1763, 1055), "cut"),
}


def fondo_global(rgb: np.ndarray) -> np.ndarray:
    """Blanco conectado con el borde de la hoja."""
    blanco = rgb.min(axis=2) >= 244
    lab, _ = ndi.label(blanco)
    borde = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    return np.isin(lab, list(borde))


def recorte(
    rgb: np.ndarray, fg: np.ndarray, lab: np.ndarray, caja: tuple[int, int, int, int]
) -> Image.Image:
    x0, y0, x1, y1 = caja
    centro = lab[y0 : y1 + 1, x0 : x1 + 1]
    ids = [i for i in np.unique(centro) if i and (centro == i).sum() > 200]
    pad = 6
    ya, yb, xa, xb = (
        max(0, y0 - pad),
        min(rgb.shape[0], y1 + 1 + pad),
        max(0, x0 - pad),
        min(rgb.shape[1], x1 + 1 + pad),
    )
    c = rgb[ya:yb, xa:xb].copy()
    f = fg[ya:yb, xa:xb] & np.isin(lab[ya:yb, xa:xb], ids)
    # descontaminación del borde: las zonas de transición toman el color del interior más cercano,
    # así no queda el halo blanco del fondo original al ponerlas sobre un escenario oscuro
    seguro = ndi.binary_erosion(f, iterations=1)
    dist, (iy, ix) = ndi.distance_transform_edt(~seguro, return_indices=True)
    cerca = (~seguro) & (dist <= 3)
    c[cerca] = c[iy[cerca], ix[cerca]]
    alfa = ndi.gaussian_filter(f.astype(float), 0.7)
    alfa = np.clip((alfa - 0.08) / 0.84, 0, 1)
    im = Image.fromarray(np.dstack([c, (alfa * 255).astype(np.uint8)]), "RGBA")
    return im.crop(im.getbbox())


def main(hojas: Path, salida: Path) -> None:
    salida.mkdir(parents=True, exist_ok=True)
    cache: dict[str, tuple] = {}
    for nombre, (hoja, caja, modo) in SPRITES.items():
        if hoja not in cache:
            rgb = np.asarray(Image.open(hojas / hoja).convert("RGB"))
            bg = fondo_global(rgb)
            lab, _ = ndi.label(ndi.binary_dilation(~bg, iterations=7))
            cache[hoja] = (rgb, ~bg, lab)
        rgb, fg, lab = cache[hoja]
        if modo == "rect":
            x0, y0, x1, y1 = caja
            Image.fromarray(rgb[y0 : y1 + 1, x0 : x1 + 1]).convert("RGBA").save(
                salida / f"{nombre}.png"
            )
        else:
            recorte(rgb, fg, lab, caja).save(salida / f"{nombre}.png")
    print(f"{len(SPRITES)} sprites en {salida}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
