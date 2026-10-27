"""Modo Palabras: segmentación de señas con movimiento y su clasificación.

Flujo: cada cuadro produce un vector de 100 características (silva.cuerpo).
El SegmentadorSenas decide cuándo empieza y termina una seña observando la
actividad de las manos (que estén levantadas o moviéndose); al terminar, la
secuencia se remuestrea a una longitud fija y se clasifica.
El mismo recorte se aplica a los videos de entrenamiento (recortar_activo),
para que el modelo vea lo mismo en entrenamiento y en vivo.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from silva import config
from silva.cuerpo import N_MANO, N_POSE
from silva.modelo import Prediccion

LONGITUD_FIJA = 20  # cuadros tras remuestrear
MIN_ACTIVOS = 8  # cuadros activos mínimos para considerar que hubo una seña (~0,27 s): evita palabras por gestos rápidos
MAX_CUADROS = 120  # ~4 s: si no termina, se clasifica igual
CUADROS_FIN = 10  # cuadros seguidos en reposo (~0,33 s) para dar la seña por terminada
MARGEN = 2  # cuadros de reposo que se conservan antes y después

# Una mano está "activa" si la muñeca está por encima de esta altura (en anchos de
# hombro bajo la línea de los hombros; y crece hacia abajo). En LSC-54 las muñecas
# en reposo están a ~1,36 (percentil 5: 0,86) y durante la seña a ~0,03.
ALTURA_ACTIVA = 0.8
MOVIMIENTO_ACTIVO = 0.12  # desplazamiento de la muñeca por cuadro (anchos de hombro)

# En vivo el segmentador mide en segundos, no en cuadros: los valores de arriba se calibraron con el video
# a 30 cuadros/s de LSC-54, y un teléfono procesa 10-20. Contando cuadros, a 15 cuadros/s una seña tenía que
# durar el doble para contar, la pausa final se alargaba al doble y el umbral de movimiento (por cuadro) se
# volvía el doble de sensible. Sin reloj (entrenamiento, pruebas) se supone 30 cuadros/s: da lo mismo que antes.
FPS_REFERENCIA = 30
SEGUNDOS_MIN_ACTIVOS = MIN_ACTIVOS / FPS_REFERENCIA
SEGUNDOS_FIN = CUADROS_FIN / FPS_REFERENCIA
SEGUNDOS_MAX = (MAX_CUADROS - 1) / FPS_REFERENCIA
SEGUNDOS_MARGEN = MARGEN / FPS_REFERENCIA
VELOCIDAD_ACTIVA = MOVIMIENTO_ACTIVO * FPS_REFERENCIA  # anchos de hombro por segundo
_PASO_MAXIMO = 0.2  # un hueco largo entre cuadros (p. ej. sin pose) cuenta a lo sumo esto como actividad
_HOLGURA = 1e-6

# Reposo de cada persona. ALTURA_ACTIVA viene de personas de pie con los brazos caídos; sentada frente a un PC o
# un teléfono, la persona descansa las manos sobre la mesa o el regazo, a 0,3-0,7 anchos de hombro bajo los
# hombros: para esa regla seguía con las manos «levantadas», la seña nunca terminaba y se cortaba a los 4 s.
# Por eso el segmentador en vivo aprende dónde descansa cada mano: si la muñeca queda quieta un segundo, esa
# altura es su reposo, y la mano cuenta como levantada solo si sube MARGEN_REPOSO por encima de él. Un reposo
# nunca se aprende por encima de REPOSO_MAS_ALTO (más arriba es una pausa dentro de la seña, no un reposo), y
# nunca hace más estricta la regla general: para alguien de pie todo sigue igual.
SEGUNDOS_QUIETA = 1.0  # tiempo con la muñeca quieta para tomar su altura como reposo
VELOCIDAD_QUIETA = 0.6  # anchos de hombro por segundo: más despacio, la muñeca está quieta
REPOSO_MAS_ALTO = 0.3  # anchos de hombro bajo la línea de los hombros (a media altura del pecho)
MARGEN_REPOSO = 0.25  # cuánto debe subir la mano sobre su reposo para contar como levantada

_I_MUNECA = (N_POSE, N_POSE + N_MANO)  # inicio de cada mano en el vector; la muñeca es el punto 0


_I_MUNECAS_POSE = (10, 12)  # muñecas izq./der. dentro del bloque de pose (puntos 15 y 16)


def _munecas(f: np.ndarray) -> list[np.ndarray]:
    """Posiciones (x, y) de las muñecas de las manos detectadas en el cuadro."""
    return [f[i:i + 2] for i in _I_MUNECA if f[i + 42] > 0]


def _levantada(f: np.ndarray, munecas: list[np.ndarray]) -> bool:
    """Alguna muñeca (de la mano o, si la mano se perdió, de la pose) está por encima del reposo."""
    return any(m[1] < ALTURA_ACTIVA for m in munecas) or any(f[i + 1] < ALTURA_ACTIVA for i in _I_MUNECAS_POSE)


def actividad(cuadros: np.ndarray) -> np.ndarray:
    """Vector booleano: True en los cuadros donde alguna mano está levantada o se mueve."""
    activo = np.zeros(len(cuadros), dtype=bool)
    previas: list[np.ndarray] = []
    for t, f in enumerate(cuadros):
        if np.isnan(f[0]):
            previas = []
            continue
        munecas = _munecas(f)
        levantada = _levantada(f, munecas)
        movida = any(
            min(np.linalg.norm(m - p) for p in previas) > MOVIMIENTO_ACTIVO for m in munecas
        ) if previas and munecas else False
        activo[t] = levantada or movida
        previas = munecas
    return activo


def recortar_activo(cuadros: np.ndarray) -> np.ndarray | None:
    """Recorta la secuencia al tramo activo más largo (con margen). None si no hay seña."""
    act = actividad(cuadros)
    if not act.any():
        return None
    # Une huecos cortos (< CUADROS_FIN) dentro de una seña
    idx = np.flatnonzero(act)
    tramos, inicio = [], idx[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if b - a > CUADROS_FIN:
            tramos.append((inicio, a))
            inicio = b
    tramos.append((inicio, idx[-1]))
    ini, fin = max(tramos, key=lambda t: t[1] - t[0])
    ini, fin = max(ini - MARGEN, 0), min(fin + MARGEN, len(cuadros) - 1)
    if act[ini:fin + 1].sum() < MIN_ACTIVOS:
        return None
    tramo = cuadros[ini:fin + 1]
    return tramo[~np.isnan(tramo[:, 0])]


def remuestrear(cuadros: np.ndarray, n: int = LONGITUD_FIJA) -> np.ndarray:
    """Lleva la secuencia a n cuadros por interpolación lineal (independiente de la velocidad)."""
    t_orig = np.linspace(0, 1, len(cuadros))
    t_nuevo = np.linspace(0, 1, n)
    return np.stack([np.interp(t_nuevo, t_orig, cuadros[:, j]) for j in range(cuadros.shape[1])], axis=1)


def rellenar_manos(cuadros: np.ndarray) -> np.ndarray:
    """Interpola la mano en los cuadros donde MediaPipe la perdió entre dos detecciones."""
    s = cuadros.copy()
    t = np.arange(len(s))
    for i in _I_MUNECA:
        presente = s[:, i + 42] > 0
        if presente.sum() < 2 or presente.all():
            continue
        idx = np.flatnonzero(presente)
        hueco = ~presente & (t > idx[0]) & (t < idx[-1])
        for j in range(i, i + 42):
            s[hueco, j] = np.interp(t[hueco], idx, s[presente, j])
        s[hueco, i + 42] = 1
    return s


def forma_manos(r: np.ndarray) -> np.ndarray:
    """Forma de cada mano respecto a su muñeca, escalada por el largo de la palma (como en letras)."""
    partes = []
    for i in _I_MUNECA:
        puntos = r[:, i:i + 42].reshape(len(r), 21, 2)
        relativos = puntos - puntos[:, :1]
        escala = np.linalg.norm(relativos[:, 9], axis=1)[:, None, None] + 1e-6
        partes.append((relativos / escala).reshape(len(r), -1) * r[:, i + 42:i + 43])
    return np.concatenate(partes, axis=1)


def vector_secuencia(cuadros: np.ndarray) -> np.ndarray:
    """Vector fijo para el clasificador: posiciones, velocidades y forma de las manos.

    Las posiciones (respecto a los hombros) dicen dónde y cómo se mueve la mano;
    la forma dice la configuración de los dedos, que distingue señas de
    trayectoria parecida.
    """
    r = remuestrear(rellenar_manos(cuadros))
    return np.concatenate([r.ravel(), np.diff(r, axis=0).ravel(), forma_manos(r).ravel()]).astype(np.float32)


OTRA = "__otra__"  # clase de rechazo: movimientos que no son ninguna de las señas conocidas


@dataclass(frozen=True)
class Evaluacion:
    """Resultado de clasificar una seña: opciones ordenadas y probabilidad de «no es una seña conocida»."""

    opciones: list[Prediccion]  # señas conocidas, de la más a la menos probable
    prob_otra: float

    @property
    def mejor(self) -> Prediccion:
        return self.opciones[0]


class ClasificadorPalabras:
    """Carga modelo_palabras.pkl (generado por scripts/entrenar_palabras.py)."""

    def __init__(self, ruta: Path = config.RUTA_MODELO_PALABRAS) -> None:
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontró {ruta}. Ejecute primero: python scripts/entrenar_palabras.py"
            )
        paquete = joblib.load(ruta)
        self._modelo = paquete["modelo"]
        self._clases: list[str] = list(self._modelo.classes_)
        self.palabras: list[str] = [c for c in self._clases if c != OTRA]
        self.nombres: dict[str, str] = paquete.get("nombres", {})
        self.metadatos: dict = paquete.get("metadatos", {})

    def evaluar(self, cuadros: np.ndarray) -> Evaluacion:
        proba = self._modelo.predict_proba(vector_secuencia(cuadros).reshape(1, -1))[0]
        prob_otra = 0.0
        opciones = []
        for clave, p in zip(self._clases, proba):
            if clave == OTRA:
                prob_otra = float(p)
            else:
                opciones.append(Prediccion(self.nombres.get(clave, clave), float(p)))
        opciones.sort(key=lambda o: o.confianza, reverse=True)
        return Evaluacion(opciones, prob_otra)

    def predecir(self, cuadros: np.ndarray) -> Prediccion:
        """La seña conocida más probable (sin considerar el rechazo)."""
        return self.evaluar(cuadros).mejor


@dataclass
class EstadoSegmentador:
    grabando: bool
    cuadros: int  # cuadros en la seña en curso
    terminada: np.ndarray | None  # secuencia completa cuando la seña termina
    segundos: float = 0.0  # duración de la seña en curso
    inicio: float | None = None  # momento del primer cuadro de `terminada`


class SegmentadorSenas:
    """Máquina de estados reposo → seña → reposo sobre el flujo de cuadros en vivo, medida en segundos.

    Con `aprender_reposo` (lo normal en vivo) aprende a qué altura descansan las manos de la persona.
    """

    def __init__(self, aprender_reposo: bool = True) -> None:
        self.aprender_reposo = aprender_reposo
        self._reposo: list[float | None] = [None, None]  # altura de reposo aprendida de cada muñeca (izq., der.)
        self._quieta_desde: list[float | None] = [None, None]
        self._pose_previa: np.ndarray | None = None
        self._t_pose_previa: float | None = None
        # Un tramo con las manos levantadas pero sin ningún movimiento no es una seña: pasa al encender la cámara
        # con las manos sobre la mesa, antes de aprender ese reposo. Con reposo aprendido se descarta.
        self._se_movio = False  # en el cuadro actual
        self._con_movimiento = False  # en el tramo en curso
        self._previo: deque[tuple[float, np.ndarray]] = deque()
        self._actual: list[tuple[float, np.ndarray]] = []
        self._activos = 0.0  # segundos con alguna mano activa
        self._t_activo = 0.0  # último cuadro activo
        self._munecas_previas: list[np.ndarray] = []
        self._t_previo: float | None = None
        self._n = 0  # cuadros recibidos: reloj por omisión, a 30 cuadros/s

    @property
    def grabando(self) -> bool:
        return bool(self._actual)

    def reiniciar(self) -> None:
        self._previo.clear()
        self._actual = []
        self._activos = 0.0
        self._munecas_previas = []
        self._t_previo = None
        self._reposo = [None, None]
        self._quieta_desde = [None, None]
        self._pose_previa = None
        self._t_pose_previa = None
        self._se_movio = False
        self._con_movimiento = False

    @property
    def reposo(self) -> tuple[float | None, float | None]:
        """Altura de reposo aprendida de cada muñeca (anchos de hombro bajo los hombros), o None."""
        return self._reposo[0], self._reposo[1]

    def _aprender(self, f: np.ndarray, t: float) -> None:
        pose = np.array([f[i:i + 2] for i in _I_MUNECAS_POSE], np.float64)
        if self._pose_previa is not None and self._t_pose_previa is not None:
            dt = max(t - self._t_pose_previa, 1e-3)
            for k in range(2):
                velocidad = np.linalg.norm(pose[k] - self._pose_previa[k]) / dt
                if velocidad > VELOCIDAD_ACTIVA:
                    self._se_movio = True
                if velocidad >= VELOCIDAD_QUIETA:
                    self._quieta_desde[k] = None
                elif self._quieta_desde[k] is None:
                    self._quieta_desde[k] = self._t_pose_previa
                elif t - self._quieta_desde[k] >= SEGUNDOS_QUIETA - _HOLGURA and pose[k][1] >= REPOSO_MAS_ALTO:
                    y = float(pose[k][1])
                    self._reposo[k] = y if self._reposo[k] is None else 0.9 * self._reposo[k] + 0.1 * y
        self._pose_previa = pose
        self._t_pose_previa = t

    def _levantada(self, f: np.ndarray, munecas: list[np.ndarray]) -> bool:
        if not self.aprender_reposo:
            return _levantada(f, munecas)
        for k, (i_mano, i_pose) in enumerate(zip(_I_MUNECA, _I_MUNECAS_POSE)):
            reposo = self._reposo[k]
            umbral = ALTURA_ACTIVA if reposo is None else min(ALTURA_ACTIVA, reposo - MARGEN_REPOSO)
            if f[i_pose + 1] < umbral or (f[i_mano + 42] > 0 and f[i_mano + 1] < umbral):
                return True
        return False

    def _es_activo(self, f: np.ndarray, t: float) -> bool:
        munecas = _munecas(f)
        self._se_movio = False
        if self.aprender_reposo:
            self._aprender(f, t)
        levantada = self._levantada(f, munecas)
        movida = False
        if self._munecas_previas and munecas and self._t_previo is not None:
            dt = max(t - self._t_previo, 1e-3)
            movida = any(min(np.linalg.norm(m - p) for p in self._munecas_previas) / dt > VELOCIDAD_ACTIVA
                         for m in munecas)
        self._munecas_previas = munecas
        self._se_movio = self._se_movio or movida
        return levantada or movida

    def _duracion(self, t: float) -> float:
        return t - self._actual[0][0] if self._actual else 0.0

    def agregar(self, f: np.ndarray | None, t: float | None = None) -> EstadoSegmentador:
        """f = vector del cuadro (None si no hay pose: se ignora); t = momento del cuadro en segundos."""
        if t is None:
            t = self._n / FPS_REFERENCIA
        if f is None:
            return EstadoSegmentador(self.grabando, len(self._actual), None, self._duracion(t))
        self._n += 1
        paso = min(t - self._t_previo, _PASO_MAXIMO) if self._t_previo is not None else 1 / FPS_REFERENCIA
        activo = self._es_activo(f, t)
        self._t_previo = t
        terminada, inicio = None, None
        if not self._actual:
            if activo:
                self._actual = [(tp, fp) for tp, fp in self._previo if tp >= t - SEGUNDOS_MARGEN - _HOLGURA]
                self._actual.append((t, f))
                self._activos = paso
                self._t_activo = t
                self._con_movimiento = self._se_movio
            else:  # se guarda el reposo justo anterior, para empezar la seña un poco antes
                self._previo.append((t, f))
                while self._previo[0][0] < t - SEGUNDOS_MARGEN - _HOLGURA:
                    self._previo.popleft()
        else:
            self._actual.append((t, f))
            if activo:
                self._activos += paso
                self._t_activo = t
            self._con_movimiento = self._con_movimiento or self._se_movio
            quieto = t - self._t_activo >= SEGUNDOS_FIN - _HOLGURA
            if quieto or self._duracion(t) >= SEGUNDOS_MAX - _HOLGURA:
                cuadros = self._actual
                if quieto:  # sin el reposo del final, salvo un margen
                    cuadros = [(tc, fc) for tc, fc in cuadros if tc <= self._t_activo + SEGUNDOS_MARGEN + _HOLGURA]
                if self._activos >= SEGUNDOS_MIN_ACTIVOS - _HOLGURA and (self._con_movimiento or not self.aprender_reposo):
                    terminada = np.array([fc for _, fc in cuadros])
                    inicio = cuadros[0][0]
                self._actual = []
                self._previo.clear()
        return EstadoSegmentador(self.grabando, len(self._actual), terminada, self._duracion(t), inicio)
