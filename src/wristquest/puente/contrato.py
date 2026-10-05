"""Contrato de mensajes entre el motor de decodificación de SynapVolit y WristQuest.

Cada mensaje es una línea ND-JSON con ``clase``, ``intensidad``, ``confianza``, ``t`` y,
opcionalmente, ``coactivacion``. El puente valida cada línea antes de reenviarla: una
línea inválida se descarta y se cuenta; nunca se corrige ni se rellena con reposo.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

INTENSIDAD_MAX = 1.5
"""Fracción de MVC máxima aceptada; puede superar 1 si la calibración subestimó la MVC."""


class Clase(IntEnum):
    """Las cinco clases del cabezal clasificador."""

    REPOSO = 0
    EXTENSION = 1
    FLEXION = 2
    PRONACION = 3
    SUPINACION = 4


class ErrorContrato(ValueError):
    """Una línea que no cumple el contrato."""


@dataclass(frozen=True, slots=True)
class Mensaje:
    """Una decisión del decodificador (una cada ~125 ms: ventana de 250 ms con 50% de traslape).

    Attributes
    ----------
    clase : Clase
        Movimiento que intenta el paciente.
    intensidad : float
        Intensidad como fracción de la MVC calibrada, en [0, INTENSIDAD_MAX].
    confianza : float
        Confianza del clasificador, en [0, 1].
    t : float
        Marca temporal del dispositivo, en ms.
    coactivacion : float or None
        Grado de coactivación antagonista, en [0, 1], si el motor lo entrega.
    """

    clase: Clase
    intensidad: float
    confianza: float
    t: float
    coactivacion: float | None = None

    def a_dict(self) -> dict[str, Any]:
        """Devuelve el mensaje en el formato del contrato."""
        d: dict[str, Any] = {
            "clase": int(self.clase),
            "intensidad": self.intensidad,
            "confianza": self.confianza,
            "t": self.t,
        }
        if self.coactivacion is not None:
            d["coactivacion"] = self.coactivacion
        return d

    def a_linea(self) -> bytes:
        """Serializa como una línea ND-JSON del contrato (lo que emitiría el dispositivo)."""
        return json.dumps(self.a_dict(), separators=(",", ":")).encode() + b"\n"

    def a_cliente(self) -> str:
        """Serializa para el cliente: el contrato más ``tipo`` para distinguirlo del estado."""
        return json.dumps({"tipo": "decodificador", **self.a_dict()}, separators=(",", ":"))


def _numero(d: dict[str, Any], clave: str, minimo: float, maximo: float) -> float:
    v = d.get(clave)
    # bool es subclase de int en Python: se rechaza explícitamente
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ErrorContrato(f"'{clave}' debe ser un número finito; llegó {v!r}")
    if not minimo <= v <= maximo:
        raise ErrorContrato(f"'{clave}'={v} fuera de [{minimo}, {maximo}]")
    return float(v)


def leer_linea(linea: str | bytes) -> Mensaje:
    """Valida una línea ND-JSON y la convierte en ``Mensaje``.

    Parameters
    ----------
    linea : str or bytes
        Una línea del flujo, con o sin salto de línea final.

    Returns
    -------
    Mensaje
        El mensaje validado.

    Raises
    ------
    ErrorContrato
        Si la línea no es JSON, no es un objeto, o algún campo falta o está fuera de rango.
    """
    try:
        d = json.loads(linea)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ErrorContrato(f"JSON inválido: {e}") from e
    if not isinstance(d, dict):
        raise ErrorContrato("el mensaje debe ser un objeto JSON")
    c = d.get("clase")
    if isinstance(c, bool) or not isinstance(c, int) or c not in Clase._value2member_map_:
        raise ErrorContrato(f"'clase' debe ser un entero de 0 a 4; llegó {c!r}")
    co = d.get("coactivacion")
    return Mensaje(
        clase=Clase(c),
        intensidad=_numero(d, "intensidad", 0.0, INTENSIDAD_MAX),
        confianza=_numero(d, "confianza", 0.0, 1.0),
        t=_numero(d, "t", 0.0, math.inf),
        coactivacion=None if co is None else _numero(d, "coactivacion", 0.0, 1.0),
    )


def mensaje_estado(fuente: str, activa: bool, descartadas: int) -> str:
    """Latido de estado para el cliente: qué fuente hay y si está entregando datos válidos."""
    return json.dumps(
        {"tipo": "estado", "fuente": fuente, "activa": activa, "descartadas": descartadas},
        separators=(",", ":"),
    )
