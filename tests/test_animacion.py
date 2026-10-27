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


def test_ninguna_animacion_pierde_la_mano_ni_se_sale(animaciones):
    """Las manos se completan al generar las animaciones, y cada seña se encuadra entera."""
    import numpy as np
    from silva.animacion import encuadre
    from silva.cuerpo import N_MANO, N_POSE
    for nombre in animaciones.nombres:
        c = animaciones.cuadros(nombre)
        assert (c[:, N_POSE + 42] > 0).all() and (c[:, N_POSE + N_MANO + 42] > 0).all(), nombre
        x0, y0, x1, y1 = animaciones.caja(nombre)
        escala, ox, oy = encuadre((x0, y0, x1, y1), 300, 300)
        assert ox + x0 * escala >= -1e-6 and ox + x1 * escala <= 300 + 1e-6, nombre
        assert oy + y0 * escala >= -1e-6 and oy + y1 * escala <= 300 + 1e-6, nombre


@pytest.mark.skipif(not config.RUTA_GUIAS_LETRAS.exists(), reason="Falta modelos/animaciones_letras.npz")
def test_hay_una_guia_por_letra_y_se_dibuja():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from silva.animacion import GuiaLetra, GuiasLetras
    g = GuiasLetras()
    assert g.letras == config.LETRAS
    assert {l for l in g.letras if g.con_trazo(l)} == set(config.LETRAS) - set(config.LETRAS_ESTATICAS)
    w = GuiaLetra(g)
    w.resize(240, 300)
    for letra in ("A", "J"):
        w.mostrar(letra)
        for _ in range(30):
            w._avanzar()
        w.grab()
    w.detener()
