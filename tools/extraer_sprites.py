"""Recorta los sprites de las hojas de arte, quita el fondo blanco sin halo y los guarda en PNG.

Uso: uv run --with pillow --with scipy python tools/extraer_sprites.py <hojas> assets/sprites
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
CU = "Cuchara.png"
S, F1, F2 = "Suelos_WristQuest.png", "Fondos_WristQuest__1_.png", "Fondos_WristQuest__2_.png"
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
    "caldero": (B, (1540, 420, 1871, 708), "cut"),
    "carton": (B, (49, 667, 325, 1046), "cut"),
    "cristal": (B, (369, 894, 526, 1053), "cut"),
    "mortero": (B, (554, 918, 744, 1052), "cut"),
    "roca_runica": (B, (778, 868, 960, 1056), "cut"),
    "pocion_azul": (B, (992, 815, 1182, 1048), "cut"),
    "llave": (B, (1222, 887, 1370, 1045), "cut"),
    "libro": (B, (1420, 863, 1613, 1053), "cut"),
    "runa_chica": (B, (1640, 879, 1763, 1055), "cut"),
    "cuchara": (CU, (0, 180, 305, 900), "cut"),  # primer cuadro: la cuchara completa
    # suelos en franjas (repetibles en horizontal)
    "suelo_tierra": (S, (0, 0, 1919, 149), "cut"),
    "suelo_pasto": (S, (0, 197, 1919, 346), "cut"),
    "suelo_rocas": (S, (0, 367, 1919, 515), "cut"),
    "suelo_muro": (S, (0, 525, 1919, 727), "cut"),
    "suelo_pradera": (S, (0, 738, 1919, 884), "cut"),
    "suelo_seco": (S, (0, 931, 1919, 1079), "cut"),
    # vegetación
    "arbol_rosa": (F1, (6, 25, 284, 329), "cut"),
    "arbol_musgo": (F1, (332, 19, 605, 329), "cut"),
    "arboles_altos": (F1, (651, 6, 1027, 345), "cut"),
    "arbol_burbujas": (F1, (1066, 7, 1259, 347), "cut"),
    "plantas_magicas": (F1, (1307, 24, 1589, 330), "cut"),
    "hongos_rojos": (F1, (1631, 17, 1914, 341), "cut"),
    "arboles_otono": (F1, (664, 371, 1581, 702), "cut"),
    "hongo_grande": (F1, (1638, 368, 1905, 697), "cut"),
    "liana_grande": (F1, (11, 389, 605, 696), "cut"),
    "liana_lazo": (F1, (4, 731, 317, 912), "cut"),
    "arbol_acacia": (F1, (327, 756, 648, 1038), "cut"),
    "pinos_grupo": (F1, (653, 731, 1260, 1064), "cut"),
    "hongos_espiral": (F1, (1303, 728, 1498, 1063), "cut"),
    "hongos_naranja": (F1, (1569, 729, 1905, 1065), "cut"),
    "liana_hojas": (F1, (1, 937, 323, 1075), "cut"),
    # cielo, casas y relieve
    "nube_azul": (F2, (12, 10, 373, 180), "cut"),
    "casa_hongo_rosa": (F2, (424, 10, 727, 342), "cut"),
    "montana": (F2, (747, 42, 1257, 342), "cut"),
    "roca_gris": (F2, (1273, 7, 1588, 335), "cut"),
    "roca_naranja": (F2, (1598, 6, 1910, 346), "cut"),
    "nube_clara": (F2, (4, 209, 392, 343), "cut"),
    "casa_hongo": (F2, (624, 367, 1008, 701), "cut"),
    "nube_rosa": (F2, (6, 425, 604, 648), "cut"),
    "cordillera": (F2, (1033, 399, 1918, 678), "cut"),
    "estanque": (F2, (5, 796, 433, 1001), "cut"),
    "casa_hongo_naranja": (F2, (446, 730, 746, 1066), "cut"),
    "casa_arbol": (F2, (761, 727, 1086, 1065), "cut"),
    "casa_tocon": (F2, (1104, 733, 1560, 1052), "cut"),
    "casa_arbol2": (F2, (1585, 725, 1912, 1068), "cut"),
}


def fondo_global(im: Image.Image) -> np.ndarray:
    """Fondo de la hoja: transparencia real si la hay; si no, blanco conectado con el borde."""
    if im.mode == "RGBA":
        a = np.asarray(im)[..., 3]
        if (a == 0).mean() > 0.05:
            return a < 16
    rgb = np.asarray(im.convert("RGB"))
    blanco = rgb.min(axis=2) >= 244
    lab, _ = ndi.label(blanco)
    borde = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    return np.isin(lab, list(borde))


def recorte(
    rgba: np.ndarray, fg: np.ndarray, lab: np.ndarray, caja: tuple, k: float, alfa_real: bool
) -> Image.Image:
    x0, y0, x1, y1 = (round(v * k) for v in caja)
    centro = lab[y0 : y1 + 1, x0 : x1 + 1]
    ids = [i for i in np.unique(centro) if i and (centro == i).sum() > 200 * k * k]
    pad = round(6 * k)
    ya, yb = max(0, y0 - pad), min(rgba.shape[0], y1 + 1 + pad)
    xa, xb = max(0, x0 - pad), min(rgba.shape[1], x1 + 1 + pad)
    c = rgba[ya:yb, xa:xb].copy()
    f = fg[ya:yb, xa:xb] & np.isin(lab[ya:yb, xa:xb], ids)
    if alfa_real:  # la hoja ya trae transparencia: solo se aíslan los componentes de la caja
        c[..., 3] = np.where(f, c[..., 3], 0)
    else:  # fondo blanco: el borde toma el color del interior (sin halo) y el alfa se suaviza
        rgb = c[..., :3]
        seguro = ndi.binary_erosion(f, iterations=1)
        dist, (iy, ix) = ndi.distance_transform_edt(~seguro, return_indices=True)
        cerca = (~seguro) & (dist <= 3)
        rgb[cerca] = rgb[iy[cerca], ix[cerca]]
        alfa = np.clip((ndi.gaussian_filter(f.astype(float), 0.7) - 0.08) / 0.84, 0, 1)
        c[..., 3] = (alfa * 255).astype(np.uint8)
    im = Image.fromarray(c, "RGBA")
    return im.crop(im.getbbox())


# Variantes de color por ZONA (como trajes alternos): cada píxel se asigna a la zona cuyo color
# base está más cerca y se recolorea conservando su sombreado (luminancia relativa a la base).
ZONAS_CONEJO = {
    "uniforme": (222, 148, 49),
    "pelaje": (158, 80, 25),
    "pelaje_osc": (113, 53, 9),
    "crema": (228, 195, 149),
    "panuelo": (181, 45, 28),
    "tinta": (58, 22, 5),
    "crema_clara": (237, 215, 178),
    "almohadilla": (155, 118, 84),
}
VARIANTES = {
    "pers_conejo_nieve": (
        "pers_conejo",
        {
            "pelaje": (196, 202, 220),
            "pelaje_osc": (126, 132, 158),
            "uniforme": (64, 128, 178),
            "panuelo": (231, 189, 36),
            "almohadilla": (178, 170, 196),
        },
    ),
    "pers_conejo_canela": (
        "pers_conejo",
        {
            "pelaje": (148, 70, 34),
            "pelaje_osc": (86, 36, 16),
            "uniforme": (91, 139, 48),
            "panuelo": (228, 143, 31),
            "crema": (236, 201, 156),
        },
    ),
}


def variantes(salida: Path) -> None:
    nombres = list(ZONAS_CONEJO)
    base = np.array([ZONAS_CONEJO[n] for n in nombres], float)
    lum = base @ [0.299, 0.587, 0.114]
    for destino, (origen, cambios) in VARIANTES.items():
        im = np.asarray(Image.open(salida / f"{origen}.png").convert("RGBA")).astype(float)
        rgb = im[..., :3]
        zona = np.argmin(((rgb[..., None, :] - base) ** 2).sum(-1), axis=-1)
        sombra = (rgb @ [0.299, 0.587, 0.114]) / lum[zona]
        nuevo = rgb.copy()
        for n, col in cambios.items():
            m = zona == nombres.index(n)
            nuevo[m] = np.clip(np.array(col, float) * sombra[m, None], 0, 255)
        Image.fromarray(np.dstack([nuevo, im[..., 3]]).astype(np.uint8), "RGBA").save(
            salida / f"{destino}.png"
        )


def main(hojas: Path, salida: Path) -> None:
    """Las cajas están en coordenadas de una hoja de 1920 px; se escalan al ancho real (3x)."""
    salida.mkdir(parents=True, exist_ok=True)
    cache: dict[str, tuple] = {}
    for nombre, (hoja, caja, modo) in SPRITES.items():
        if hoja not in cache:
            im = Image.open(hojas / hoja).convert("RGBA")
            k = im.width / 1920
            bg = fondo_global(im)
            alfa_real = bool((np.asarray(im)[..., 3] == 0).mean() > 0.05)
            lab, _ = ndi.label(ndi.binary_dilation(~bg, iterations=max(1, round(7 * k))))
            cache[hoja] = (np.asarray(im).copy(), ~bg, lab, k, alfa_real)
        rgba, fg, lab, k, alfa_real = cache[hoja]
        if modo == "rect":
            x0, y0, x1, y1 = (round(v * k) for v in caja)
            Image.fromarray(rgba[y0 : y1 + 1, x0 : x1 + 1], "RGBA").save(salida / f"{nombre}.png")
        else:
            recorte(rgba, fg, lab, caja, k, alfa_real).save(salida / f"{nombre}.png")
    variantes(salida)
    print(f"{len(SPRITES)} sprites y {len(VARIANTES)} variantes en {salida} (escala {k:g}x)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
