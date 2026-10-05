"""Fuentes de líneas ND-JSON: el dispositivo por puerto serie o una simulación sin hardware.

Una fuente solo entrega líneas crudas; la validación es responsabilidad del puente. Así la
fuente simulada recorre exactamente el mismo camino que el hardware.
"""

from __future__ import annotations

import asyncio
import math
import random
from collections.abc import AsyncIterator, Iterator
from typing import Any, Protocol

from .contrato import Clase, Mensaje


class Fuente(Protocol):
    """Interfaz común de las fuentes."""

    nombre: str

    def lineas(self) -> AsyncIterator[bytes]:
        """Genera líneas crudas, sin salto de línea."""
        ...


class FuenteSerie:
    """Lee el flujo ND-JSON del ESP32 por puerto serie.

    Parameters
    ----------
    puerto : str
        Puerto o URL de pyserial: ``"COM3"`` en Windows, ``"loop://"`` para pruebas sin hardware.
    baudios : int
        Velocidad del puerto; debe coincidir con el firmware.
    abierto : objeto tipo ``serial.Serial``, opcional
        Puerto ya abierto, para inyectarlo en pruebas.
    """

    nombre = "serie"

    def __init__(self, puerto: str = "", baudios: int = 115200, abierto: Any | None = None) -> None:
        self.puerto, self.baudios, self._abierto = puerto, baudios, abierto

    async def lineas(self) -> AsyncIterator[bytes]:
        import serial  # pyserial: solo se exige si se usa esta fuente

        s = self._abierto or serial.serial_for_url(self.puerto, baudrate=self.baudios, timeout=0.2)
        try:
            while True:
                # readline bloquea hasta el timeout: se corre en un hilo para no detener el bucle de eventos
                linea = await asyncio.to_thread(s.readline)
                if linea.strip():
                    yield linea.strip()
                # un timeout sin datos no se rellena con nada: el latido del puente reportará la ausencia
        finally:
            s.close()


class FuenteSimulada:
    """Simula al decodificador sin hardware, con la misma cadencia y formato.

    Alterna bloques de reposo y de un movimiento al azar. Dentro de cada movimiento la
    intensidad sigue una campana (subida, meseta, bajada) con ruido, y la confianza baja en
    las transiciones, como ocurre en un clasificador real en los bordes de la contracción.

    Parameters
    ----------
    periodo_s : float
        Tiempo entre decisiones; 0.125 s reproduce ventanas de 250 ms con 50% de traslape.
    semilla : int
        Semilla del generador: la secuencia es reproducible.
    n : int or None
        Número de mensajes; ``None`` para un flujo infinito.
    """

    nombre = "simulada"

    def __init__(self, periodo_s: float = 0.125, semilla: int = 42, n: int | None = None) -> None:
        self.periodo_s, self.semilla, self.n = periodo_s, semilla, n

    def mensajes(self) -> Iterator[Mensaje]:
        """Genera los mensajes de forma síncrona (útil en pruebas)."""
        rng = random.Random(self.semilla)
        k, dt_ms = 0, self.periodo_s * 1000.0

        def emitir(clase: Clase, inten: float, conf: float, coact: float) -> Mensaje:
            return Mensaje(
                clase,
                round(min(max(inten, 0.0), 1.5), 4),
                round(min(max(conf, 0.0), 1.0), 4),
                round(k * dt_ms, 3),
                round(min(max(coact, 0.0), 1.0), 4),
            )

        while self.n is None or k < self.n:
            mov, dur, pico = Clase(rng.randint(1, 4)), rng.randint(8, 16), rng.uniform(0.35, 0.8)
            for i in range(dur):
                if self.n is not None and k >= self.n:
                    return
                env = math.sin(math.pi * i / (dur - 1))
                inten = pico * env + rng.gauss(0.0, 0.02)
                # con poca intensidad el clasificador decide reposo
                clase = mov if inten >= 0.08 else Clase.REPOSO
                yield emitir(
                    clase,
                    inten,
                    0.55 + 0.4 * env + rng.gauss(0.0, 0.03),
                    0.25 + 0.15 * env + rng.gauss(0.0, 0.03),
                )
                k += 1
            for _ in range(rng.randint(6, 12)):
                if self.n is not None and k >= self.n:
                    return
                yield emitir(
                    Clase.REPOSO,
                    abs(rng.gauss(0.02, 0.01)),
                    0.9 + rng.gauss(0.0, 0.03),
                    0.1 + rng.gauss(0.0, 0.02),
                )
                k += 1

    async def lineas(self) -> AsyncIterator[bytes]:
        for m in self.mensajes():
            yield m.a_linea().strip()
            await asyncio.sleep(self.periodo_s)
