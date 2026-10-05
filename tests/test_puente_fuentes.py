"""Fuentes sin hardware: la simulada es reproducible y válida; la serie se prueba con loop:// de pyserial."""

import asyncio

import pytest

from wristquest.puente import Clase, FuenteSerie, FuenteSimulada, leer_linea


def test_simulada_reproducible():
    a = list(FuenteSimulada(semilla=7, n=200).mensajes())
    b = list(FuenteSimulada(semilla=7, n=200).mensajes())
    c = list(FuenteSimulada(semilla=8, n=200).mensajes())
    assert a == b and a != c and len(a) == 200


def test_simulada_cumple_el_contrato():
    ms = [leer_linea(m.a_linea()) for m in FuenteSimulada(n=600).mensajes()]
    assert {m.clase for m in ms} == set(Clase)  # aparecen las cinco clases
    assert all(b.t - a.t == pytest.approx(125.0) for a, b in zip(ms, ms[1:]))  # cadencia de 8 Hz
    assert all(m.intensidad < 0.1 for m in ms if m.clase is Clase.REPOSO)


def test_serie_lee_lineas_sin_hardware():
    serial = pytest.importorskip("serial")
    puerto = serial.serial_for_url("loop://", timeout=0.1)
    puerto.write(
        b'{"clase":1,"intensidad":0.4,"confianza":0.9,"t":0}\nbasura\n\n{"clase":0,"intensidad":0.0,"confianza":0.9,"t":125}\n'
    )

    async def primeras(n):
        out, gen = [], FuenteSerie(abierto=puerto).lineas()
        async for linea in gen:
            out.append(linea)
            if len(out) == n:
                await gen.aclose()
                return out

    lineas = asyncio.run(asyncio.wait_for(primeras(3), timeout=3))
    assert lineas[1] == b"basura"  # la fuente no valida: eso lo hace el puente
    assert leer_linea(lineas[2]).t == 125.0  # las líneas vacías se omiten
