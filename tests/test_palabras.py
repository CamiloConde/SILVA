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


# ---------- controlador en modo Palabras: provisional, sugerencia y corrección ----------

class _SegmentadorGuionado:
    """Termina una seña en los cuadros indicados; entre `inicio` y fin marca que está grabando."""

    def __init__(self, fines, duracion=5):
        self.fines, self.duracion, self.n = set(fines), duracion, 0

    def agregar(self, f):
        from silva.palabras import EstadoSegmentador
        self.n += 1
        grabando = any(fin - self.duracion <= self.n < fin for fin in self.fines)
        termina = self.n in self.fines
        return EstadoSegmentador(grabando, 0, np.zeros((10, N_CARACTERISTICAS_CUADRO)) if termina else None)

    def reiniciar(self):
        pass


class _CuerpoFalso:
    def detectar(self, cuadro, ms):
        return CuadroCuerpo(None, None, None, 4 / 3)

    def cerrar(self):
        pass


class _ClasificadorPalabrasFalso:
    """Cada seña devuelve (palabra, confianza, prob_otra); las opciones 2 y 3 son fijas."""

    nombres = {}

    def __init__(self, salidas):
        self.salidas = list(salidas)

    def evaluar(self, cuadros):
        from silva.modelo import Prediccion
        from silva.palabras import Evaluacion
        palabra, confianza, otra = self.salidas.pop(0)
        return Evaluacion([Prediccion(palabra, confianza), Prediccion("Chao", 0.05), Prediccion("Bien", 0.04)], otra)


class _Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _controlador(fines, salidas, umbral=0.25):
    from conftest import CapturaFalsa, ClasificadorFalso, DetectorFalso
    from silva.controlador import MODO_PALABRAS, ControladorSILVA
    from silva.repositorio_historial import RepositorioHistorial
    reloj = _Reloj()
    ctrl = ControladorSILVA(CapturaFalsa(), DetectorFalso([]), ClasificadorFalso([]), RepositorioHistorial(":memory:"),
                            detector_cuerpo=_CuerpoFalso(), clasificador_palabras=_ClasificadorPalabrasFalso(salidas),
                            umbral_palabras=umbral, umbral_sugerencia=0.12, reloj=reloj)
    ctrl.cambiar_modo(MODO_PALABRAS)
    ctrl.segmentador = _SegmentadorGuionado(fines)
    ctrl.iniciar()
    return ctrl, reloj


def _avanzar(ctrl, reloj, cuadros, paso=1 / 30):
    resultados = []
    for _ in range(cuadros):
        reloj.t += paso
        resultados.append(ctrl.procesar_cuadro())
    return resultados


def test_sena_segura_se_escribe_apenas_se_reconoce():
    ctrl, reloj = _controlador(fines=[10], salidas=[("Hola", 0.9, 0.05)])
    r = _avanzar(ctrl, reloj, 10)[-1]
    assert r.letra_confirmada == "Hola" and ctrl.buffer.texto == "Hola"  # sin esperar
    assert r.pendiente.automatica and r.pendiente.opciones[0].letra == "Hola"  # pero se puede corregir
    _avanzar(ctrl, reloj, 100)  # pasado el plazo de corrección
    assert ctrl.buffer.texto == "Hola" and ctrl.pendiente is None
    assert [l for l, _ in ctrl.historial.letras_de_sesion(ctrl.sesion_id)] == ["Hola"]


def test_movimiento_ajeno_no_escribe_nada():
    """El defecto de la v1.0.0: «otra cosa» gana y no se muestra nada."""
    ctrl, reloj = _controlador(fines=[10], salidas=[("Hola", 0.3, 0.7)])
    r = _avanzar(ctrl, reloj, 10)[-1]
    assert r.pendiente is None
    _avanzar(ctrl, reloj, 300)
    assert ctrl.buffer.texto == ""


def test_sena_dudosa_es_sugerencia_y_solo_se_escribe_si_se_elige():
    ctrl, reloj = _controlador(fines=[10, 300], salidas=[("Gracias", 0.18, 0.2), ("Gracias", 0.18, 0.2)])
    r = _avanzar(ctrl, reloj, 10)[-1]
    assert r.pendiente is not None and not r.pendiente.automatica
    _avanzar(ctrl, reloj, 240)  # vence sin que nadie elija
    assert ctrl.buffer.texto == "" and ctrl.pendiente is None
    _avanzar(ctrl, reloj, 50)  # segunda vez: alguien elige la opción 2
    assert ctrl.confirmar_pendiente(1) == "Chao"
    assert ctrl.buffer.texto == "Chao"


def test_cambiar_y_borrar_la_palabra_escrita():
    ctrl, reloj = _controlador(fines=[10, 40], salidas=[("Hola", 0.9, 0.0), ("No", 0.8, 0.0)])
    _avanzar(ctrl, reloj, 10)
    assert ctrl.confirmar_pendiente(2) == "Bien"  # no era «Hola»: la tercera opción la reemplaza
    assert ctrl.buffer.texto == "Bien"
    _avanzar(ctrl, reloj, 30)
    assert ctrl.buffer.texto == "Bien No"
    ctrl.descartar_pendiente()  # X: «No» se borra
    _avanzar(ctrl, reloj, 120)
    assert ctrl.buffer.texto.strip() == "Bien"


def test_confirmar_la_palabra_escrita_no_la_repite():
    ctrl, reloj = _controlador(fines=[10], salidas=[("Hola", 0.9, 0.0)])
    _avanzar(ctrl, reloj, 10)
    assert ctrl.confirmar_pendiente(0) == "Hola"  # Espacio: era correcta
    assert ctrl.buffer.texto == "Hola" and ctrl.pendiente is None


def test_empezar_otra_sena_cierra_la_correccion():
    ctrl, reloj = _controlador(fines=[10, 30], salidas=[("Hola", 0.9, 0.0), ("Gracias", 0.9, 0.0)])
    _avanzar(ctrl, reloj, 31)
    assert ctrl.buffer.texto == "Hola Gracias"


def test_detener_conserva_la_palabra_y_descarta_la_sugerencia():
    ctrl, reloj = _controlador(fines=[10], salidas=[("Hola", 0.9, 0.0)])
    _avanzar(ctrl, reloj, 10)
    ctrl.detener()
    assert ctrl.historial.listar_sesiones()[0].texto == "Hola"


def test_misma_palabra_casi_seguida_se_escribe_una_vez():
    ctrl, reloj = _controlador(fines=[30, 35, 140], salidas=[("Hola", 0.9, 0.0)] * 3)
    _avanzar(ctrl, reloj, 220)
    assert ctrl.buffer.texto == "Hola Hola"


def test_modo_palabras_pide_imagen_panoramica():
    """16:9 a 640×360: a 1280×720 muchas cámaras web solo entregan 10 cuadros/s."""
    ctrl, _ = _controlador(fines=[], salidas=[])
    assert ctrl.captura.resolucion == (640, 360)
    from silva.controlador import MODO_LETRAS
    ctrl.cambiar_modo(MODO_LETRAS)
    assert ctrl.captura.resolucion == (640, 480)


def test_mano_perdida_se_dibuja_aproximada_desde_la_pose():
    """Cuando MediaPipe pierde la mano, se dibuja la que estima el esqueleto (no desaparece en pantalla)."""
    from silva.cuerpo import dibujar_cuerpo
    pose = pose_base()
    pose[17], pose[19], pose[21] = Landmark(0.66, 0.95), Landmark(0.62, 0.97), Landmark(0.58, 0.93)
    sin_mano = np.zeros((360, 640, 3), np.uint8)
    dibujar_cuerpo(sin_mano, CuadroCuerpo(pose, None, None, 16 / 9))
    zona = sin_mano[int(0.85 * 360):, int(0.55 * 640):int(0.7 * 640)]
    assert zona.any()  # hay trazos donde está la mano izquierda aproximada


def test_mano_perdida_se_recupera_desde_la_muneca_de_la_pose():
    """Si MediaPipe pierde la mano, se busca en un recorte ampliado alrededor de la muñeca de la pose."""
    import zipfile

    import cv2

    from silva.cuerpo import MANO_POSE_IZQ, DetectorCuerpo
    from silva.detector_manos import DetectorManos

    ruta = config.RAIZ_PROYECTO / "data" / "externo" / "lsc70" / "LSC70.zip"
    if not ruta.exists():
        pytest.skip("Falta data/externo/lsc70/LSC70.zip")
    with zipfile.ZipFile(ruta) as z:
        img = cv2.imdecode(np.frombuffer(z.read("LSC70/LSC70AN/Per05/A/Per05_A_2.jpg"), np.uint8), cv2.IMREAD_COLOR)
    mano = DetectorManos().detectar(img, 0)
    assert mano is not None
    # pose inventada: hombros de ~0,25 del ancho y la muñeca izquierda donde está la mano
    pose = [Landmark(0.5, 0.6) for _ in range(33)]
    pose[11], pose[12] = Landmark(0.62, 0.6), Landmark(0.38, 0.6)
    m = mano.landmarks
    for i, k in zip(MANO_POSE_IZQ, (0, 17, 5, 2)):
        pose[i] = m[k]
    detector = DetectorCuerpo()
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    hombros = 0.24 * img.shape[1]
    recuperada = DetectorCuerpo._buscar_en_recorte(detector._recuperadores[0], rgb, pose, MANO_POSE_IZQ, None, hombros)
    assert recuperada is not None
    assert abs(recuperada[0].x - m[0].x) < 0.03 and abs(recuperada[0].y - m[0].y) < 0.03
    # la misma mano ya detectada como «la otra» no se acepta dos veces
    assert DetectorCuerpo._buscar_en_recorte(detector._recuperadores[0], rgb, pose, MANO_POSE_IZQ, m, hombros) is None
    detector.cerrar()


def test_brillo_del_cuadro():
    from silva.controlador import _brillo
    assert _brillo(np.zeros((480, 640, 3), np.uint8)) == 0
    assert _brillo(np.full((480, 640, 3), 200, np.uint8)) == 200


def _pose_en(cx, ancho, y_hombros=0.5, y_nariz=0.31):
    p = [Landmark(cx, y_hombros) for _ in range(33)]
    p[0] = Landmark(cx, y_nariz)
    p[11], p[12] = Landmark(cx + ancho / 2, y_hombros), Landmark(cx - ancho / 2, y_hombros)
    return p


def test_encuadre_como_en_los_datos_de_entrenamiento():
    from silva.cuerpo import evaluar_encuadre
    def guia(*a, **k):
        return evaluar_encuadre(CuadroCuerpo(_pose_en(*a, **k), None, None, 16 / 9))
    assert guia(0.51, 0.21) is None  # la mediana medida en LSC-54
    assert "Acércate" in guia(0.5, 0.10)
    assert "Aléjate" in guia(0.5, 0.40)
    assert "derecha" in guia(0.70, 0.21)  # x crece hacia la izquierda de la persona
    assert "izquierda" in guia(0.30, 0.21)
    assert "Baja" in guia(0.5, 0.21, y_hombros=0.3, y_nariz=0.05)
    assert "Sube" in guia(0.5, 0.21, y_hombros=0.8, y_nariz=0.6)
    assert evaluar_encuadre(CuadroCuerpo(None, None, None, 16 / 9)) is None
