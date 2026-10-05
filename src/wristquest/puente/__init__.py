"""Puente entre el motor de decodificación de SynapVolit y el cliente WristQuest.

Lee mensajes ND-JSON (serie o fuente simulada), los valida contra el contrato y los
difunde por WebSocket a ``WQ.feedDecoder`` en el navegador.
"""

from .contrato import Clase, ErrorContrato, Mensaje, leer_linea, mensaje_estado
from .fuentes import FuenteSerie, FuenteSimulada
from .servidor import Puente

__all__ = [
    "Clase",
    "ErrorContrato",
    "FuenteSerie",
    "FuenteSimulada",
    "Mensaje",
    "Puente",
    "leer_linea",
    "mensaje_estado",
]
