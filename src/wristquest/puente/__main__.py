"""Línea de comandos del puente: ``uv run python -m wristquest.puente --fuente simulada``."""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import logging

from .fuentes import FuenteSerie, FuenteSimulada
from .servidor import Puente


def main() -> None:
    p = argparse.ArgumentParser(
        prog="python -m wristquest.puente",
        description="Puente ND-JSON (serie) a WebSocket para WristQuest.",
    )
    # sin valor por defecto: el operador debe declarar si la señal es real o simulada
    p.add_argument("--fuente", choices=["serie", "simulada", "ninguna"], required=True)
    p.add_argument(
        "--puerto-serie", default="", help='p. ej. "COM3"; obligatorio con --fuente serie'
    )
    p.add_argument("--baudios", type=int, default=115200)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--puerto", type=int, default=8765)
    p.add_argument("--semilla", type=int, default=42)
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.fuente == "serie" and not a.puerto_serie:
        p.error("--fuente serie requiere --puerto-serie")
    if not ipaddress.ip_address(a.host if a.host != "localhost" else "127.0.0.1").is_loopback:
        logging.warning(
            "escuchando fuera de la máquina local (%s): la señal de un paciente quedará expuesta en la red",
            a.host,
        )
    fuente = {
        "serie": lambda: FuenteSerie(a.puerto_serie, a.baudios),
        "simulada": lambda: FuenteSimulada(semilla=a.semilla),
        "ninguna": lambda: None,
    }[a.fuente]()
    if a.fuente == "simulada":
        logging.warning("FUENTE SIMULADA: los datos no provienen de ningún paciente ni dispositivo")
    try:
        asyncio.run(Puente(fuente, a.host, a.puerto).correr())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
