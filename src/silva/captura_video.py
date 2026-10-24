"""Captura de video desde la cámara web con OpenCV."""

from __future__ import annotations

import sys

import cv2
import numpy as np

from silva import config


class CamaraNoDisponibleError(RuntimeError):
    """La cámara no existe o la está usando otra aplicación (alt de la Figura 3)."""


class CapturaVideo:
    def __init__(self, indice: int = config.INDICE_CAMARA) -> None:
        self._indice = indice
        self._cap: cv2.VideoCapture | None = None

    def abrir(self) -> None:
        # En Windows DirectShow abre la cámara mucho más rápido que el backend por defecto (RF-01: < 3 s).
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self._indice, backend)
        if not cap.isOpened():
            cap.release()
            raise CamaraNoDisponibleError(f"No se pudo abrir la cámara {self._indice}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap = cap

    @property
    def abierta(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def leer_cuadro(self) -> np.ndarray | None:
        if not self.abierta:
            return None
        ok, cuadro = self._cap.read()
        return cuadro if ok else None

    def liberar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
