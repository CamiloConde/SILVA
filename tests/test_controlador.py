"""Flujo completo del controlador con cámara, detector y clasificador simulados (CU-01 a CU-05)."""

import pytest

from conftest import CapturaFalsa, ClasificadorFalso, DetectorFalso, mano_cualquiera
from silva.captura_video import CamaraNoDisponibleError
from silva.controlador import ControladorSILVA
from silva.modelo import Prediccion
from silva.repositorio_historial import RepositorioHistorial


class HistorialEspia(RepositorioHistorial):
    def __init__(self, registro):
        super().__init__(":memory:")
        self.registro = registro

    def guardar_sesion(self, sesion_id, texto):
        self.registro.append(f"guardar:{texto}")
        super().guardar_sesion(sesion_id, texto)


def crear(manos, predicciones, registro=None, disponible=True):
    registro = registro if registro is not None else []
    return ControladorSILVA(
        CapturaFalsa(registro, disponible),
        DetectorFalso(manos),
        ClasificadorFalso(predicciones),
        HistorialEspia(registro),
    )


def test_traduce_y_registra_letra_confirmada():
    ctrl = crear([mano_cualquiera()] * 5, [Prediccion("A", 0.93)] * 5)
    ctrl.iniciar()
    resultados = [ctrl.procesar_cuadro() for _ in range(5)]
    assert all(r.mano_detectada for r in resultados)
    assert resultados[-1].letra_confirmada == "A"
    assert resultados[-1].texto == "A"
    assert ctrl.ultima_confianza == pytest.approx(0.93)
    assert ctrl.historial.letras_de_sesion(ctrl.sesion_id) == [("A", 0.93)]


def test_cuadro_sin_mano():
    ctrl = crear([None], [])
    ctrl.iniciar()
    r = ctrl.procesar_cuadro()
    assert not r.mano_detectada
    assert r.prediccion is None


def test_detener_guarda_antes_de_liberar_la_camara():
    registro = []
    ctrl = crear([mano_cualquiera()] * 5, [Prediccion("B", 0.9)] * 5, registro)
    ctrl.iniciar()
    for _ in range(5):
        ctrl.procesar_cuadro()
    ctrl.detener()
    assert registro == ["abrir_camara", "guardar:B", "liberar_camara"]
    assert ctrl.historial.listar_sesiones()[0].texto == "B"
    assert ctrl.procesar_cuadro() is None


def test_camara_no_disponible():
    ctrl = crear([], [], disponible=False)
    with pytest.raises(CamaraNoDisponibleError):
        ctrl.iniciar()
    assert not ctrl.activo
    assert ctrl.historial.listar_sesiones() == []


def test_cada_inicio_es_una_sesion_nueva():
    ctrl = crear([], [])
    ctrl.iniciar()
    ctrl.detener()
    ctrl.iniciar()
    ctrl.detener()
    assert len(ctrl.historial.listar_sesiones()) == 2
