"""Contrato ND-JSON: lo válido pasa idéntico y lo inválido se rechaza, nunca se corrige."""

import pytest

from wristquest.puente import Clase, ErrorContrato, Mensaje, leer_linea


def test_ida_y_vuelta():
    m = Mensaje(Clase.SUPINACION, 0.42, 0.91, 1250.0, 0.3)
    assert leer_linea(m.a_linea()) == m


def test_coactivacion_es_opcional():
    m = leer_linea('{"clase":0,"intensidad":0.01,"confianza":0.95,"t":0}')
    assert m.clase is Clase.REPOSO and m.coactivacion is None


@pytest.mark.parametrize(
    "linea",
    [
        "no es json",
        "[1, 2, 3]",
        '{"intensidad":0.5,"confianza":0.9,"t":1}',  # falta la clase
        '{"clase":7,"intensidad":0.5,"confianza":0.9,"t":1}',  # clase inexistente
        '{"clase":"1","intensidad":0.5,"confianza":0.9,"t":1}',  # clase como texto
        '{"clase":true,"intensidad":0.5,"confianza":0.9,"t":1}',  # bool no es clase
        '{"clase":1,"intensidad":-0.1,"confianza":0.9,"t":1}',
        '{"clase":1,"intensidad":0.5,"confianza":1.2,"t":1}',
        '{"clase":1,"intensidad":NaN,"confianza":0.9,"t":1}',  # json de Python acepta NaN: se rechaza
        '{"clase":1,"intensidad":0.5,"confianza":0.9}',  # falta t
        '{"clase":1,"intensidad":0.5,"confianza":0.9,"t":1,"coactivacion":2}',
    ],
)
def test_rechaza_lineas_invalidas(linea):
    with pytest.raises(ErrorContrato):
        leer_linea(linea)
