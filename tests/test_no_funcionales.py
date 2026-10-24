"""RNF-01/02 (sin red) y RNF-03 (tiempo por cuadro) con los modelos reales."""

import socket
import time

import numpy as np
import pytest

from conftest import CapturaFalsa
from silva import config
from silva.buffer_texto import BufferTexto
from silva.clasificador import ClasificadorPreentrenado
from silva.controlador import ControladorSILVA
from silva.detector_manos import DetectorManos
from silva.repositorio_historial import RepositorioHistorial

pytestmark = pytest.mark.skipif(not config.RUTA_MODELO_SENAS.exists(), reason="Falta modelos/modelo_senas.pkl")


@pytest.fixture
def sin_red(monkeypatch):
    """Cualquier intento de conexión de red hace fallar la prueba."""

    def bloqueado(*args, **kwargs):
        raise AssertionError(f"Intento de conexión de red: {args}")

    monkeypatch.setattr(socket.socket, "connect", bloqueado)
    monkeypatch.setattr(socket.socket, "connect_ex", bloqueado)
    monkeypatch.setattr(socket, "create_connection", bloqueado)


def test_pipeline_completo_sin_red(sin_red, tmp_path, datos_externos):
    ctrl = ControladorSILVA(
        CapturaFalsa(), DetectorManos(), ClasificadorPreentrenado(),
        RepositorioHistorial(tmp_path / "h.db"), BufferTexto(),
    )
    ctrl.iniciar()
    for _ in range(10):
        assert ctrl.procesar_cuadro() is not None
    X, _ = datos_externos
    ctrl.clasificador.predecir(X[0].tolist())
    ctrl.detener()
    ctrl.cerrar()


def test_tiempo_por_cuadro_permite_15_fps(datos_externos):
    detector, clasificador = DetectorManos(), ClasificadorPreentrenado()
    X, _ = datos_externos
    cuadro = np.random.default_rng(0).integers(0, 255, (480, 640, 3), dtype=np.uint8)
    try:
        for i in range(5):  # calentamiento
            detector.detectar(cuadro, i * 33)
        n, t0 = 30, time.perf_counter()
        for i in range(n):
            detector.detectar(cuadro, 1000 + i * 33)
            clasificador.predecir(X[i].tolist())
        ms = (time.perf_counter() - t0) / n * 1000
    finally:
        detector.cerrar()
    print(f"\n{ms:.1f} ms por cuadro (detección + clasificación) = {1000 / ms:.0f} FPS")
    assert ms < 1000 / 15
