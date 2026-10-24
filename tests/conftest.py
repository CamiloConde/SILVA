from __future__ import annotations

import numpy as np
import pytest

from silva import config
from silva.modelo import Landmark, Mano, Prediccion


class CapturaFalsa:
    """Cámara simulada: entrega cuadros negros y registra las llamadas."""

    def __init__(self, registro: list[str] | None = None, disponible: bool = True) -> None:
        self.registro = registro if registro is not None else []
        self.disponible = disponible
        self.abierta = False

    def abrir(self) -> None:
        from silva.captura_video import CamaraNoDisponibleError

        if not self.disponible:
            raise CamaraNoDisponibleError("sin cámara")
        self.abierta = True
        self.registro.append("abrir_camara")

    def leer_cuadro(self):
        return np.zeros((480, 640, 3), dtype=np.uint8) if self.abierta else None

    def liberar(self) -> None:
        self.abierta = False
        self.registro.append("liberar_camara")


class DetectorFalso:
    """Devuelve, en orden, las manos (o None) de la lista dada."""

    def __init__(self, manos: list[Mano | None]) -> None:
        self.manos = list(manos)

    def detectar(self, cuadro, marca_ms):
        return self.manos.pop(0) if self.manos else None

    def cerrar(self) -> None:
        pass


class ClasificadorFalso:
    letras = ["A", "B"]

    def __init__(self, predicciones: list[Prediccion]) -> None:
        self.predicciones = list(predicciones)

    def predecir(self, caracteristicas):
        return self.predicciones.pop(0)


def mano_cualquiera() -> Mano:
    lms = [Landmark(0.5 + i * 0.01, 0.5 - i * 0.01) for i in range(config.NUM_LANDMARKS)]
    return Mano(lms, False, [0.0] * config.NUM_CARACTERISTICAS)


@pytest.fixture
def datos_externos():
    ruta = config.DIR_LANDMARKS / "externo_juanplazas.npz"
    if not ruta.exists():
        pytest.skip("Falta data/landmarks/externo_juanplazas.npz (scripts/preparar_dataset.py)")
    d = np.load(ruta)
    return d["X"], d["y"]
