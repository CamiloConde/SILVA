"""Letras con movimiento: segmentación del trazo, características y uso en el controlador."""

import numpy as np
import pytest

from conftest import CapturaFalsa, DetectorFalso
from silva import config
from silva.controlador import ControladorSILVA
from silva.letras_movimiento import (LETRAS_MOVIMIENTO, ClasificadorMovimiento, SegmentadorLetras,
                                     a_isotropicas, caracteristicas_secuencia)
from silva.modelo import Landmark, Mano, Prediccion
from silva.repositorio_historial import RepositorioHistorial


def puntos_mano(dx: float = 0.0) -> np.ndarray:
    return np.array([(0.5 + dx + i * 0.01, 0.5 - i * 0.01) for i in range(21)], np.float32)


def mano(dx: float = 0.0) -> Mano:
    return Mano([Landmark(float(x), float(y)) for x, y in puntos_mano(dx)], False, [0.0] * 42)


def test_las_letras_con_movimiento_completan_el_alfabeto():
    assert LETRAS_MOVIMIENTO == list("GHJÑQSZ")
    assert sorted(config.LETRAS_ESTATICAS + LETRAS_MOVIMIENTO) == sorted(config.LETRAS)


def test_mano_quieta_no_es_un_trazo():
    seg = SegmentadorLetras()
    estados = [seg.agregar(puntos_mano()) for _ in range(30)]
    assert not any(e.moviendo or e.terminado is not None for e in estados)


def test_trazo_completo_se_entrega_al_quedarse_quieta():
    seg = SegmentadorLetras()
    for _ in range(5):
        seg.agregar(puntos_mano())
    for k in range(1, 13):
        estado = seg.agregar(puntos_mano(0.03 * k))
    assert estado.moviendo
    estados = [seg.agregar(puntos_mano(0.36)) for _ in range(config.CUADROS_QUIETO)]
    terminado = estados[-1].terminado
    assert terminado is not None and not estados[-1].moviendo
    puntos, izquierda = terminado
    assert len(puntos) >= 12 and not izquierda
    assert puntos[0, 0, 0] == pytest.approx(0.5)  # incluye el cuadro quieto previo: el inicio del trazo


def test_perder_la_mano_cierra_el_trazo_y_un_temblor_corto_no_cuenta():
    seg = SegmentadorLetras()
    for k in range(10):
        seg.agregar(puntos_mano(0.03 * k))
    sin_mano = round(config.SEGUNDOS_SIN_MANO_TRAZO * 30)  # a 30 cuadros/s
    assert all(seg.agregar(None).moviendo for _ in range(sin_mano))  # un instante sin mano: el trazo sigue
    assert seg.agregar(None).terminado is not None
    for k in range(4):  # 1-2 cuadros de movimiento: menos que el mínimo
        seg.agregar(puntos_mano(0.04 * k if k < 2 else 0.04))
    assert all(seg.agregar(puntos_mano(0.04)).terminado is None for _ in range(8))


def test_una_mano_rapida_que_se_pierde_un_instante_sigue_el_mismo_trazo():
    """Al trazar rápido la mano sale borrosa y MediaPipe la pierde 2-3 cuadros: no debe partirse la letra."""
    seg = SegmentadorLetras()
    for _ in range(3):
        seg.agregar(puntos_mano())
    terminados = []
    for k in range(1, 21):
        perdida = k in (8, 9, 10)  # ~0,1 s sin mano a mitad del trazo
        e = seg.agregar(None if perdida else puntos_mano(0.03 * k))
        terminados += [e.terminado] if e.terminado is not None else []
    terminados += [e.terminado for e in (seg.agregar(puntos_mano(0.6)) for _ in range(config.CUADROS_QUIETO))
                   if e.terminado is not None]
    assert len(terminados) == 1
    puntos, _ = terminados[0]
    assert puntos[-1, 0, 0] == pytest.approx(0.5 + 0.6, abs=1e-5)  # llega hasta el final del trazo


def test_caracteristicas_no_dependen_de_la_posicion_y_espejan_la_izquierda():
    trazo = np.stack([puntos_mano(0.02 * k) for k in range(9)])
    a = caracteristicas_secuencia(trazo, False)
    b = caracteristicas_secuencia(trazo + np.float32([0.2, 0.1]), False)
    assert a.shape == (264,)
    np.testing.assert_allclose(a, b, atol=1e-5)
    espejo = trazo.copy()
    espejo[..., 0] = 1 - espejo[..., 0]
    np.testing.assert_allclose(caracteristicas_secuencia(espejo, True), a, atol=1e-5)


class _Estatico:
    letras = ["A", "I"]

    def __init__(self, letra):
        self.letra = letra

    def predecir(self, _caracteristicas):
        return Prediccion(self.letra, 0.95)


class _Movimiento:
    letras = list("GHJÑQSZ")

    def __init__(self, letra, confianza=0.8):
        self.salida = Prediccion(letra, confianza)
        self.llamadas = 0

    def predecir(self, puntos, izquierda):
        self.llamadas += 1
        return self.salida


def _controlador(manos, movimiento, estatica="I"):
    reloj = iter(np.arange(0, 100, 1 / 30))
    return ControladorSILVA(CapturaFalsa(), DetectorFalso(manos), _Estatico(estatica),
                            RepositorioHistorial(":memory:"), clasificador_movimiento=movimiento,
                            reloj=lambda: float(next(reloj)))


def _trazo_j():
    """La I quieta (se escribe), un trazo y la mano quieta al final."""
    return [mano()] * 6 + [mano(0.03 * k) for k in range(1, 12)] + [mano(0.33)] * 8


def test_la_letra_con_movimiento_reemplaza_la_forma_con_que_empieza():
    ctrl = _controlador(_trazo_j(), _Movimiento("J"))
    ctrl.iniciar()
    resultados = [ctrl.procesar_cuadro() for _ in range(25)]
    assert resultados[4].letra_confirmada == "I"  # la I alcanzó a escribirse...
    assert any(r.trazando for r in resultados)
    assert [r.letra_confirmada for r in resultados if r.letra_confirmada] == ["I", "J"]
    assert resultados[-1].texto == "J"  # ...y la J la reemplazó
    assert ctrl.letras == ["A", "G", "H", "I", "J", "Ñ", "Q", "S", "Z"]


def test_un_trazo_que_no_es_letra_no_escribe_nada():
    movimiento = _Movimiento("__otra__", 0.9)
    ctrl = _controlador(_trazo_j(), movimiento)
    ctrl.iniciar()
    for _ in range(25):
        r = ctrl.procesar_cuadro()
    assert movimiento.llamadas == 1
    assert r.texto == "I"  # la letra estática se conserva y no se repite al quedarse quieto


def test_letra_estatica_que_reconoce_el_trazo_no_se_escribe():
    ctrl = _controlador(_trazo_j(), _Movimiento("A", 0.99))
    ctrl.iniciar()
    for _ in range(25):
        r = ctrl.procesar_cuadro()
    assert r.texto == "I"


@pytest.fixture(scope="module")
def modelo():
    if not config.RUTA_MODELO_LETRAS_MOVIMIENTO.exists():
        pytest.skip("Falta modelos/modelo_letras_movimiento.pkl (scripts/entrenar_letras_movimiento.py)")
    return ClasificadorMovimiento()


def test_modelo_real_reconoce_trazos_de_lsc70(modelo):
    assert modelo.letras == LETRAS_MOVIMIENTO
    ruta = config.DIR_LANDMARKS / "lsc70_secuencias.npz"
    if not ruta.exists():
        pytest.skip("Falta data/landmarks/lsc70_secuencias.npz")
    d = np.load(ruta)
    puntos = a_isotropicas(d["puntos"], 640, 480)
    completas = ~np.isnan(puntos[:, :, 0, 0]).any(axis=1)
    aciertos = total = 0
    for letra in LETRAS_MOVIMIENTO:
        for i in np.flatnonzero((d["letras"] == letra) & completas)[:5]:
            aciertos += modelo.predecir(puntos[i], bool(d["izquierda"][i].mean() >= 0.5)).letra == letra
            total += 1
    assert aciertos / total >= 0.9  # datos de entrenamiento: comprueba carga y características
