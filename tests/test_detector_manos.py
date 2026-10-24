"""RF-02 / RF-03: detección de la mano y normalización de landmarks."""

import math

import numpy as np
import pytest

from silva import config
from silva.detector_manos import DetectorManos, normalizar_landmarks
from silva.modelo import Landmark


def mano_ejemplo(dx=0.0, dy=0.0, escala=1.0):
    base = [(0.5, 0.8)] + [(0.4 + 0.02 * i, 0.7 - 0.02 * i) for i in range(1, 21)]
    return [Landmark(0.5 + (x - 0.5) * escala + dx, 0.8 + (y - 0.8) * escala + dy) for x, y in base]


def test_muneca_es_el_origen_y_escala_unitaria():
    v = normalizar_landmarks(mano_ejemplo(), es_izquierda=False)
    assert len(v) == config.NUM_CARACTERISTICAS
    assert v[0] == 0 and v[1] == 0
    assert math.hypot(v[18], v[19]) == pytest.approx(1.0)  # landmark 9


def test_invariante_a_posicion_y_distancia():
    a = normalizar_landmarks(mano_ejemplo(), False)
    b = normalizar_landmarks(mano_ejemplo(dx=0.2, dy=-0.1, escala=0.5), False)
    assert np.allclose(a, b, atol=1e-6)


def test_mano_izquierda_se_espeja():
    derecha = normalizar_landmarks(mano_ejemplo(), False)
    izquierda = normalizar_landmarks(mano_ejemplo(), True)
    assert np.allclose(derecha[0::2], [-x for x in izquierda[0::2]])
    assert np.allclose(derecha[1::2], izquierda[1::2])


def test_cantidad_incorrecta_de_landmarks():
    with pytest.raises(ValueError):
        normalizar_landmarks(mano_ejemplo()[:20], False)


def test_formato_coincide_con_dataset_de_entrenamiento(datos_externos):
    X, _ = datos_externos
    assert X.shape[1] == config.NUM_CARACTERISTICAS
    assert np.allclose(X[:, :2], 0)  # muñeca en el origen
    assert np.allclose(np.hypot(X[:, 18], X[:, 19]), 1, atol=1e-4)


def test_cuadro_sin_mano_devuelve_none():
    detector = DetectorManos()
    try:
        for t in range(3):
            assert detector.detectar(np.zeros((480, 640, 3), dtype=np.uint8), t * 33) is None
    finally:
        detector.cerrar()


def test_marcas_de_tiempo_repetidas_no_fallan():
    detector = DetectorManos()
    try:
        cuadro = np.full((480, 640, 3), 127, dtype=np.uint8)
        detector.detectar(cuadro, 100)
        detector.detectar(cuadro, 100)  # MediaPipe exige tiempos crecientes; el detector lo corrige
    finally:
        detector.cerrar()
