"""Palabras a señas (RF-15): búsqueda de señas en un texto y animación."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from silva import config

pytestmark = pytest.mark.skipif(not config.RUTA_ANIMACIONES.exists(), reason="Falta modelos/animaciones_senas.npz")


@pytest.fixture(scope="module")
def animaciones():
    from silva.animacion import AnimacionesSenas
    return AnimacionesSenas()


def test_hay_una_animacion_por_palabra(animaciones):
    assert len(animaciones.nombres) == 33
    cuadros = animaciones.cuadros("Hola")
    assert cuadros.ndim == 2 and cuadros.shape[1] == 100 and len(cuadros) > 20


def test_buscar_senas_en_un_texto(animaciones):
    assert animaciones.buscar("¡Hola! ¿Cómo estás? Muchas gracias") == ["Hola", "¿Cómo está?", "Muchas gracias"]
    assert animaciones.buscar("BUENOS DÍAS, siga por favor") == ["Buenos días", "Por favor"]
    assert animaciones.buscar("El médico lo atiende en 5 minutos") == []


def test_la_animacion_avanza_y_cambia_de_sena(animaciones):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from silva.animacion import AnimacionSena
    w = AnimacionSena(animaciones)
    w.resize(320, 400)
    w.mostrar(["Hola", "Gracias"])
    total = len(animaciones.cuadros("Hola"))
    for _ in range(total + 20):
        w._avanzar()
    assert w._actual == 1  # pasó a la segunda seña
    w.grab()  # se dibuja sin errores
    w.detener()
