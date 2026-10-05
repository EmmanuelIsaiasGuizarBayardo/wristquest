"""Servidor WebSocket que valida y difunde las decisiones del decodificador."""

from __future__ import annotations

import asyncio
import logging
import time

from websockets.asyncio.server import ServerConnection, broadcast, serve

from .contrato import ErrorContrato, leer_linea, mensaje_estado
from .fuentes import Fuente

log = logging.getLogger(__name__)


class Puente:
    """Lee una fuente, valida cada línea contra el contrato y la difunde a los clientes.

    Ausencia explícita: cada ``latido_s`` se envía un mensaje de estado con la fuente y si
    está activa, es decir, si llegó una línea válida en los últimos ``espera_s`` segundos.
    Nunca se sintetiza reposo para tapar un hueco: el cliente decide qué hacer sin señal.

    Parameters
    ----------
    fuente : Fuente or None
        Origen de las líneas; ``None`` deja al puente solo con el latido (fuente "ninguna").
    host : str
        Interfaz de escucha. Por defecto solo la máquina local, porque la señal es de pacientes.
    puerto : int
        Puerto TCP; 0 elige uno libre (útil en pruebas, ver ``puerto_real``).
    espera_s, latido_s : float
        Ventana para considerar activa la fuente y periodo del latido de estado.
    """

    def __init__(
        self,
        fuente: Fuente | None,
        host: str = "127.0.0.1",
        puerto: int = 8765,
        espera_s: float = 0.5,
        latido_s: float = 1.0,
    ) -> None:
        self.fuente, self.host, self.puerto = fuente, host, puerto
        self.espera_s, self.latido_s = espera_s, latido_s
        self.clientes: set[ServerConnection] = set()
        self.validas = 0
        self.descartadas = 0
        self.puerto_real: int | None = None
        self._ultimo = -float("inf")

    @property
    def activa(self) -> bool:
        """Si llegó una línea válida dentro de la ventana de espera."""
        return time.monotonic() - self._ultimo < self.espera_s

    def estado(self) -> str:
        """Mensaje de estado actual."""
        return mensaje_estado(
            self.fuente.nombre if self.fuente else "ninguna", self.activa, self.descartadas
        )

    async def _atender(self, ws: ServerConnection) -> None:
        self.clientes.add(ws)
        try:
            await ws.send(self.estado())
            await ws.wait_closed()
        finally:
            self.clientes.discard(ws)

    async def _leer(self) -> None:
        if self.fuente is None:
            return
        async for linea in self.fuente.lineas():
            try:
                m = leer_linea(linea)
            except ErrorContrato as e:
                self.descartadas += 1
                log.warning("línea descartada (%d): %s", self.descartadas, e)
                continue
            self.validas += 1
            self._ultimo = time.monotonic()
            broadcast(self.clientes, m.a_cliente())

    async def _latir(self) -> None:
        while True:
            broadcast(self.clientes, self.estado())
            await asyncio.sleep(self.latido_s)

    async def correr(self, listo: asyncio.Event | None = None) -> None:
        """Sirve hasta que se cancele la tarea; ``listo`` se activa cuando ya acepta conexiones."""
        async with serve(self._atender, self.host, self.puerto) as servidor:
            self.puerto_real = servidor.sockets[0].getsockname()[1]
            log.info(
                "puente en ws://%s:%d con fuente %s",
                self.host,
                self.puerto_real,
                self.fuente.nombre if self.fuente else "ninguna",
            )
            if listo is not None:
                listo.set()
            await asyncio.gather(self._leer(), self._latir())
