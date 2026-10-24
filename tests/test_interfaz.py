"""Interfaz Qt: ciclos Iniciar/Detener con el hilo de video, modos y edición del texto."""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from conftest import CapturaFalsa, ClasificadorFalso, DetectorFalso, mano_cualquiera
from silva import config
from silva.controlador import MODO_LETRAS, MODO_PALABRAS, ControladorSILVA
from silva.interfaz import VentanaPrincipal
from silva.modelo import Prediccion
from silva.repositorio_historial import RepositorioHistorial


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class ClasificadorLetras(ClasificadorFalso):
    letras = config.LETRAS_ESTATICAS

    def predecir(self, caracteristicas):
        return Prediccion("A", 0.95)


class DetectorSiempreMano(DetectorFalso):
    def detectar(self, cuadro, marca_ms):
        return mano_cualquiera()


def esperar(app, condicion, segundos=5.0):
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        app.processEvents()
        if condicion():
            return True
        time.sleep(0.01)
    return False


def crear(app, captura=None, detector=None):
    ctrl = ControladorSILVA(captura or CapturaFalsa(), detector or DetectorSiempreMano([]), ClasificadorLetras([]),
                            RepositorioHistorial(":memory:"))
    ventana = VentanaPrincipal(ctrl)
    errores = []
    ventana.mostrar_error = lambda titulo, mensaje: errores.append(titulo)
    return ventana, ctrl, errores


def test_iniciar_detener_varias_veces(app):
    ventana, ctrl, errores = crear(app)
    for ronda in range(3):
        ventana.btn_principal.click()
        assert esperar(app, lambda: ctrl.activo and ventana.lbl_fps.text() != ""), f"no inició (ronda {ronda})"
        assert "Detener" in ventana.btn_principal.text()
        ventana.btn_principal.click()
        assert not ctrl.activo and not ventana.activo
        assert "Iniciar" in ventana.btn_principal.text()
    assert errores == []
    assert len(ctrl.historial.listar_sesiones()) == 3
    ventana.close()


def test_letra_confirmada_aparece_en_el_texto(app):
    ventana, ctrl, _ = crear(app)
    ventana.iniciar()
    assert esperar(app, lambda: "A" in ventana.lbl_texto.text())
    assert "Última confirmada: A" in ventana.lbl_ultima.text()
    assert ventana.btn_borrar.isEnabled()
    ventana.detener()
    ventana.close()


def test_camara_no_disponible_muestra_error_y_permite_reintentar(app):
    ventana, ctrl, errores = crear(app, captura=CapturaFalsa(disponible=False))
    ventana.iniciar()
    assert esperar(app, lambda: errores != [])
    assert errores == ["Cámara no disponible"]
    assert not ventana.activo and ventana.btn_principal.isEnabled()
    ventana.close()


def test_edicion_del_texto(app):
    ventana, ctrl, _ = crear(app)
    ctrl.buffer.agregar_palabra("Hola")
    ventana.espacio()
    assert ctrl.buffer.texto == "Hola "
    ventana.borrar()
    assert ctrl.buffer.texto == "Hola"
    ventana.limpiar()
    assert ctrl.buffer.texto == ""
    assert not ventana.btn_borrar.isEnabled() and not ventana.btn_limpiar.isEnabled()
    assert ventana.lbl_texto.property("vacio") is True
    ventana.close()


def test_cambio_de_modo(app):
    if not config.RUTA_MODELO_PALABRAS.exists():
        pytest.skip("Falta modelos/modelo_palabras.pkl")
    from silva.palabras import ClasificadorPalabras

    class CuerpoFalso:
        def cerrar(self):
            pass

    ctrl = ControladorSILVA(CapturaFalsa(), DetectorFalso([]), ClasificadorLetras([]), RepositorioHistorial(":memory:"),
                            detector_cuerpo=CuerpoFalso(), clasificador_palabras=ClasificadorPalabras())
    ventana = VentanaPrincipal(ctrl)
    ventana.btn_modo[MODO_PALABRAS].click()
    assert ctrl.modo == MODO_PALABRAS
    assert ventana.lbl_titulo_det.text() == "PALABRA DETECTADA"
    assert ventana.pila.currentIndex() == 1 and not ventana.btn_espacio.isVisibleTo(ventana)
    ventana.btn_modo[MODO_LETRAS].click()
    assert ctrl.modo == MODO_LETRAS and ventana.pila.currentIndex() == 0
    ventana.close()


def test_historial(app):
    ventana, ctrl, _ = crear(app)
    sid = ctrl.historial.iniciar_sesion()
    ctrl.historial.guardar_sesion(sid, "HOLA")
    ctrl.historial.registrar_respuesta(sid, "Siga, por favor")
    ventana.ver_historial()
    from PySide6.QtWidgets import QTableWidget
    sesiones = ventana._dialogo_historial.findChild(QTableWidget, "tabla_sesiones")
    respuestas = ventana._dialogo_historial.findChild(QTableWidget, "tabla_respuestas")
    assert sesiones.rowCount() == 1 and sesiones.item(0, 2).text() == "HOLA"
    assert respuestas.rowCount() == 1 and respuestas.item(0, 2).text() == "Siga, por favor"
    ventana.close()


def test_responder_muestra_en_grande_y_guarda(app):
    """RF-09: la respuesta de la persona oyente se ve sobre el video y queda en el historial."""
    ventana, ctrl, _ = crear(app)
    ventana.responder()
    dialogo = ventana._dialogo_respuesta
    dialogo.editor.setPlainText("   ")
    dialogo.btn_mostrar.click()  # vacía: no hace nada
    assert not ventana.video.mostrando_respuesta and dialogo.isVisible()
    dialogo.editor.setPlainText("Siga, el médico lo atiende en 5 minutos")
    dialogo.btn_mostrar.click()
    assert ventana.video.mostrando_respuesta and not dialogo.isVisible()
    assert ctrl.historial.listar_respuestas()[0][1] == "Siga, el médico lo atiende en 5 minutos"
    ventana.video.grab()  # se pinta sin errores
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    clic = QMouseEvent(QMouseEvent.MouseButtonPress, QPointF(10, 10), QPointF(10, 10), Qt.LeftButton,
                       Qt.LeftButton, Qt.NoModifier)
    ventana.video.mousePressEvent(clic)
    assert not ventana.video.mostrando_respuesta
    ventana.close()
