"""Detección de la mano y extracción de landmarks con MediaPipe Hand Landmarker."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from silva import config
from silva.modelo import Landmark, Mano

CONEXIONES_MANO = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]


def normalizar_landmarks(landmarks: list[Landmark], es_izquierda: bool) -> list[float]:
    """Convierte 21 landmarks en un vector de 42 valores invariante a posición y escala.

    Se toma la muñeca (landmark 0) como origen, se espeja el eje x si la mano
    es la izquierda y se divide por la distancia muñeca-nudillo del dedo medio
    (landmark 9). Es la misma normalización del dataset externo de LSC usado
    para entrenar (ver docs/dataset.md), por eso no debe cambiarse por separado.
    """
    if len(landmarks) != config.NUM_LANDMARKS:
        raise ValueError(f"Se esperaban {config.NUM_LANDMARKS} landmarks, llegaron {len(landmarks)}")

    muneca = landmarks[0]
    coords = []
    for lm in landmarks:
        dx = muneca.x - lm.x if es_izquierda else lm.x - muneca.x
        coords.append((dx, lm.y - muneca.y))

    escala = math.hypot(*coords[9])
    if escala > 0:
        coords = [(x / escala, y / escala) for x, y in coords]

    return [v for punto in coords for v in punto]


class DetectorManos:
    """Envuelve MediaPipe para detectar una mano por cuadro."""

    def __init__(self, ruta_modelo: Path = config.RUTA_MODELO_MANOS) -> None:
        if not ruta_modelo.exists():
            raise FileNotFoundError(f"No se encontró el modelo de MediaPipe en {ruta_modelo}")
        opciones = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ruta_modelo)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=config.CONFIANZA_DETECCION,
            min_hand_presence_confidence=config.CONFIANZA_DETECCION,
            min_tracking_confidence=config.CONFIANZA_SEGUIMIENTO,
        )
        self._detector = vision.HandLandmarker.create_from_options(opciones)
        self._ultimo_ms = -1

    def detectar(self, cuadro_bgr: np.ndarray, marca_tiempo_ms: int) -> Mano | None:
        """Devuelve la mano detectada en el cuadro o None si no hay ninguna."""
        # El modo VIDEO exige marcas de tiempo estrictamente crecientes.
        marca_tiempo_ms = max(marca_tiempo_ms, self._ultimo_ms + 1)
        self._ultimo_ms = marca_tiempo_ms

        rgb = cv2.cvtColor(cuadro_bgr, cv2.COLOR_BGR2RGB)
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        resultado = self._detector.detect_for_video(imagen, marca_tiempo_ms)
        if not resultado.hand_landmarks:
            return None

        landmarks = [Landmark(lm.x, lm.y) for lm in resultado.hand_landmarks[0]]
        es_izquierda = resultado.handedness[0][0].index == 1
        return Mano(landmarks, es_izquierda, normalizar_landmarks(landmarks, es_izquierda))

    def cerrar(self) -> None:
        self._detector.close()


def dibujar_mano(cuadro_bgr: np.ndarray, mano: Mano) -> None:
    """Dibuja el esqueleto de la mano sobre el cuadro (in situ)."""
    alto, ancho = cuadro_bgr.shape[:2]
    puntos = [(int(lm.x * ancho), int(lm.y * alto)) for lm in mano.landmarks]
    for a, b in CONEXIONES_MANO:
        cv2.line(cuadro_bgr, puntos[a], puntos[b], (80, 200, 120), 2)
    for p in puntos:
        cv2.circle(cuadro_bgr, p, 4, (255, 140, 40), cv2.FILLED)
