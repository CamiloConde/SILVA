"""Modo Palabras: características de cuerpo, segmentación y clasificador."""

import numpy as np
import pytest

from silva import config
from silva.cuerpo import (
    N_CARACTERISTICAS_CUADRO, N_MANO, N_POSE, CuadroCuerpo, asignar_manos, caracteristicas_cuadro, espejar,
)
from silva.modelo import Landmark
from silva.palabras import (
    CUADROS_FIN, LONGITUD_FIJA, MIN_ACTIVOS, ClasificadorPalabras, SegmentadorSenas, recortar_activo,
    remuestrear, vector_secuencia,
)


def pose_base(dx=0.0):
    p = [Landmark(0.5 + dx, 0.5) for _ in range(33)]
    p[11], p[12] = Landmark(0.6 + dx, 0.5), Landmark(0.4 + dx, 0.5)  # hombros izq./der. de la persona
    p[15], p[16] = Landmark(0.62 + dx, 0.9), Landmark(0.38 + dx, 0.9)  # muñecas abajo
    return p


def mano_en(x, y):
    return [Landmark(x + 0.005 * i, y - 0.005 * i) for i in range(21)]


def cuadro(altura_muneca: float, x: float = 0.6) -> np.ndarray:
    """Vector de un cuadro con la mano izquierda de la persona a cierta altura (en anchos de hombro)."""
    f = np.zeros(N_CARACTERISTICAS_CUADRO, np.float32)
    f[[11, 13]] = 1.5  # muñecas de la pose en reposo (la mano detectada es la que se mueve)
    f[N_POSE:N_POSE + 42:2] = x
    f[N_POSE + 1:N_POSE + 42:2] = altura_muneca
    f[N_POSE + 42] = 1
    return f


def test_vector_de_cuadro_centrado_en_hombros():
    c = CuadroCuerpo(pose_base(), mano_en(0.6, 0.5), None, aspecto=1.0)
    v = caracteristicas_cuadro(c)
    assert v.shape == (N_CARACTERISTICAS_CUADRO,)
    hombros = v[2:6].reshape(2, 2)
    assert np.allclose(hombros.mean(axis=0), 0, atol=1e-6)  # origen entre los hombros
    assert np.linalg.norm(hombros[0] - hombros[1]) == pytest.approx(1.0)  # escala = ancho de hombros
    assert v[N_POSE + 42] == 1 and v[N_POSE + N_MANO + 42] == 0  # solo la mano izquierda presente


def test_invariante_a_la_posicion_de_la_persona():
    a = caracteristicas_cuadro(CuadroCuerpo(pose_base(), mano_en(0.6, 0.5), None, 1.0))
    b = caracteristicas_cuadro(CuadroCuerpo(pose_base(0.2), mano_en(0.8, 0.5), None, 1.0))
    assert np.allclose(a, b, atol=1e-5)


def test_sin_pose_no_hay_vector():
    assert caracteristicas_cuadro(CuadroCuerpo(None, mano_en(0.5, 0.5), None, 1.0)) is None


def test_asignar_manos_por_muneca_mas_cercana():
    pose = pose_base()
    cerca_izq, cerca_der = mano_en(0.62, 0.88), mano_en(0.38, 0.88)
    assert asignar_manos(pose, [cerca_der, cerca_izq]) == (cerca_izq, cerca_der)
    assert asignar_manos(pose, [cerca_der]) == (None, cerca_der)


def test_espejar_dos_veces_es_identidad():
    rng = np.random.default_rng(0)
    s = rng.normal(size=(10, N_CARACTERISTICAS_CUADRO)).astype(np.float32)
    s[:, N_POSE + 42] = 1
    s[:, N_POSE + N_MANO + 42] = 1
    assert np.allclose(espejar(espejar(s)), s)


def test_remuestrear_longitud_fija():
    s = np.linspace(0, 1, 37)[:, None] * np.ones((1, 3))
    r = remuestrear(s)
    assert r.shape == (LONGITUD_FIJA, 3)
    assert r[0, 0] == 0 and r[-1, 0] == 1


def test_recortar_activo_quita_el_reposo():
    reposo = [cuadro(2.0)] * 10
    sena = [cuadro(0.0)] * 15
    tramo = recortar_activo(np.array(reposo + sena + reposo))
    assert 15 <= len(tramo) <= 15 + 6  # seña + transición + márgenes


def test_segmentador_detecta_una_sena():
    seg = SegmentadorSenas()
    terminadas = []
    for f in [cuadro(2.0)] * 10 + [cuadro(0.0)] * 15 + [cuadro(2.0)] * (CUADROS_FIN + 2):
        e = seg.agregar(f)
        if e.terminada is not None:
            terminadas.append(e.terminada)
    assert len(terminadas) == 1
    assert len(terminadas[0]) >= 15


def test_segmentador_ignora_gestos_muy_cortos():
    seg = SegmentadorSenas()
    for f in [cuadro(2.0)] * 5 + [cuadro(0.0)] * (MIN_ACTIVOS - 2) + [cuadro(2.0)] * (CUADROS_FIN + 5):
        assert seg.agregar(f).terminada is None


def test_segmentador_ignora_cuadros_sin_pose():
    seg = SegmentadorSenas()
    assert seg.agregar(None).terminada is None
    assert not seg.grabando


@pytest.fixture(scope="module")
def clasificador():
    if not config.RUTA_MODELO_PALABRAS.exists():
        pytest.skip("Falta modelos/modelo_palabras.pkl (scripts/entrenar_palabras.py)")
    return ClasificadorPalabras()


def test_clasificador_devuelve_palabra_y_confianza(clasificador):
    seq = np.array([cuadro(0.5 - 0.05 * t) for t in range(20)])
    p = clasificador.predecir(seq)
    assert p.letra in clasificador.nombres.values()
    assert 0 <= p.confianza <= 1
    assert len(vector_secuencia(seq)) == clasificador._modelo.n_features_in_


# ---------- controlador en modo Palabras ----------

class _SegmentadorGuionado:
    """Termina una seña en los cuadros indicados."""

    def __init__(self, fines):
        self.fines, self.n = set(fines), 0

    def agregar(self, f):
        from silva.palabras import EstadoSegmentador
        self.n += 1
        termina = self.n in self.fines
        return EstadoSegmentador(False, 0, np.zeros((10, N_CARACTERISTICAS_CUADRO)) if termina else None)

    def reiniciar(self):
        pass


class _CuerpoFalso:
    def detectar(self, cuadro, ms):
        return CuadroCuerpo(None, None, None, 4 / 3)

    def cerrar(self):
        pass


class _ClasificadorPalabrasFalso:
    nombres = {}

    def __init__(self, salidas):
        self.salidas = list(salidas)

    def predecir(self, cuadros):
        from silva.modelo import Prediccion
        palabra, confianza = self.salidas.pop(0)
        return Prediccion(palabra, confianza)


def _controlador(fines, salidas, umbral=0.2):
    from conftest import CapturaFalsa, ClasificadorFalso, DetectorFalso
    from silva.controlador import MODO_PALABRAS, ControladorSILVA
    from silva.repositorio_historial import RepositorioHistorial
    ctrl = ControladorSILVA(CapturaFalsa(), DetectorFalso([]), ClasificadorFalso([]), RepositorioHistorial(":memory:"),
                            detector_cuerpo=_CuerpoFalso(), clasificador_palabras=_ClasificadorPalabrasFalso(salidas),
                            umbral_palabras=umbral)
    ctrl.cambiar_modo(MODO_PALABRAS)
    ctrl.segmentador = _SegmentadorGuionado(fines)
    ctrl.iniciar()
    return ctrl


def test_palabras_se_escriben_y_las_dudosas_se_piden_repetir():
    ctrl = _controlador(fines=[20, 60, 100], salidas=[("Hola", 0.9), ("Gracias", 0.1), ("Gracias", 0.6)])
    descartadas = []
    for _ in range(110):
        r = ctrl.procesar_cuadro()
        if r.descartada:
            descartadas.append(r.descartada.letra)
    assert ctrl.buffer.texto == "Hola Gracias"
    assert descartadas == ["Gracias"]
    assert [l for l, _ in ctrl.historial.letras_de_sesion(ctrl.sesion_id)] == ["Hola", "Gracias"]


def test_misma_palabra_casi_seguida_se_escribe_una_vez():
    # Seña partida en dos (cuadros 30 y 35) -> una sola; repetición real 60 cuadros después -> se escribe
    ctrl = _controlador(fines=[30, 35, 95], salidas=[("Hola", 0.9), ("Hola", 0.9), ("Hola", 0.9)])
    for _ in range(100):
        ctrl.procesar_cuadro()
    assert ctrl.buffer.texto == "Hola Hola"
