"""Captura de video desde la cámara web con OpenCV."""

from __future__ import annotations

import sys

import cv2
import numpy as np

from silva import config

ANCHO_PROCESO = 640  # los cuadros más anchos se reducen a este ancho (mismo campo de visión, menos cómputo)


class CamaraNoDisponibleError(RuntimeError):
    """La cámara no existe o la está usando otra aplicación (alt de la Figura 3)."""


class CapturaVideo:
    def __init__(self, indice: int = config.INDICE_CAMARA) -> None:
        self.indice = indice  # 0 = cámara integrada; 1, 2… = cámaras externas o el celular como cámara web
        self._resolucion = (640, 480)
        self._cap: cv2.VideoCapture | None = None

    def configurar(self, ancho: int, alto: int) -> None:
        """Resolución pedida a la cámara; si ya está abierta se aplica en caliente."""
        self._resolucion = (ancho, alto)
        if self.abierta:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)

    def abrir(self) -> None:
        # En Windows DirectShow abre la cámara mucho más rápido que el backend por defecto (RF-01: < 3 s).
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.indice, backend)
        if not cap.isOpened():
            cap.release()
            raise CamaraNoDisponibleError(f"No se pudo abrir la cámara {self.indice + 1}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolucion[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolucion[1])
        self._cap = cap

    @property
    def abierta(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def leer_cuadro(self) -> np.ndarray | None:
        if not self.abierta:
            return None
        ok, cuadro = self._cap.read()
        if not ok:
            return None
        alto, ancho = cuadro.shape[:2]
        if ancho > ANCHO_PROCESO:
            cuadro = cv2.resize(cuadro, (ANCHO_PROCESO, round(alto * ANCHO_PROCESO / ancho)),
                                interpolation=cv2.INTER_AREA)
        return cuadro

    def liberar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
