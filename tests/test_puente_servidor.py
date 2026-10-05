"""Puente completo sin hardware: difusión, descarte de líneas inválidas y ausencia explícita."""

import asyncio
import json

from websockets.asyncio.client import connect

from wristquest.puente import FuenteSimulada, Puente


class FuenteLista:
    """Fuente de prueba que entrega líneas fijas."""

    nombre = "lista"

    def __init__(self, lineas):
        self._lineas = lineas

    async def lineas(self):
        for linea in self._lineas:
            await asyncio.sleep(0.05)
            yield linea


async def _recibir(puente, segundos):
    listo = asyncio.Event()
    tarea = asyncio.create_task(puente.correr(listo))
    await listo.wait()
    msgs = []
    async with connect(f"ws://127.0.0.1:{puente.puerto_real}") as ws:
        try:
            async with asyncio.timeout(segundos):
                while True:
                    msgs.append(json.loads(await ws.recv()))
        except TimeoutError:
            pass
    tarea.cancel()
    return msgs


def test_difunde_la_fuente_simulada():
    p = Puente(FuenteSimulada(periodo_s=0.01, n=40), puerto=0, latido_s=0.1)
    msgs = asyncio.run(_recibir(p, 1.0))
    datos = [m for m in msgs if m["tipo"] == "decodificador"]
    assert (
        msgs[0]["tipo"] == "estado" and msgs[0]["fuente"] == "simulada"
    )  # el cliente sabe de inmediato que es simulada
    assert len(datos) >= 30 and all(
        {"clase", "intensidad", "confianza", "t"} <= m.keys() for m in datos
    )


def test_descarta_lineas_invalidas():
    ok = b'{"clase":2,"intensidad":0.5,"confianza":0.8,"t":0}'
    p = Puente(FuenteLista([ok, b"basura", b'{"clase":9}', ok]), puerto=0, latido_s=0.1)
    msgs = asyncio.run(_recibir(p, 0.8))
    assert sum(m["tipo"] == "decodificador" for m in msgs) == 2 and p.descartadas == 2


def test_sin_fuente_la_ausencia_es_explicita():
    p = Puente(None, puerto=0, latido_s=0.1)
    msgs = asyncio.run(_recibir(p, 0.5))
    assert msgs and all(
        m == {"tipo": "estado", "fuente": "ninguna", "activa": False, "descartadas": 0}
        for m in msgs
    )


def test_la_fuente_se_marca_inactiva_cuando_se_detiene():
    p = Puente(FuenteSimulada(periodo_s=0.01, n=5), puerto=0, espera_s=0.2, latido_s=0.1)
    msgs = asyncio.run(_recibir(p, 1.0))
    estados = [m["activa"] for m in msgs if m["tipo"] == "estado"]
    assert True in estados and estados[-1] is False  # sin datos recientes: no se finge reposo
