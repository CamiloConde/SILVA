"""Interfaz Clasificador y su implementación con el modelo preentrenado (Figura 2)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import numpy as np

from silva import config
from silva.modelo import Prediccion


class Clasificador(ABC):
    @abstractmethod
    def predecir(self, caracteristicas: list[float]) -> Prediccion:
        """Clasifica un vector de landmarks normalizados."""


class ClasificadorPreentrenado(Clasificador):
    """Carga `modelo_senas.pkl` (generado por scripts/entrenar_modelo.py)."""

    def __init__(self, ruta_modelo: Path = config.RUTA_MODELO_SENAS) -> None:
        if not ruta_modelo.exists():
            raise FileNotFoundError(
                f"No se encontró {ruta_modelo}. Ejecute primero: python scripts/entrenar_modelo.py"
            )
        paquete = joblib.load(ruta_modelo)
        self._modelo = paquete["modelo"]
        self.letras: list[str] = list(self._modelo.classes_)
        self.metadatos: dict = paquete.get("metadatos", {})

    def predecir(self, caracteristicas: list[float]) -> Prediccion:
        x = np.asarray(caracteristicas, dtype=np.float32).reshape(1, -1)
        probabilidades = self._modelo.predict_proba(x)[0]
        i = int(np.argmax(probabilidades))
        return Prediccion(self.letras[i], float(probabilidades[i]))
