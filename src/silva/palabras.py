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
MIN_ACTIVOS = 6  # cuadros activos mínimos para considerar que hubo una seña (~0,2 s)
MAX_CUADROS = 120  # ~4 s: si no termina, se clasifica igual
CUADROS_FIN = 8  # cuadros seguidos en reposo (~0,27 s) para dar la seña por terminada
MARGEN = 2  # cuadros de reposo que se conservan antes y después

# Una mano está "activa" si la muñeca está por encima de esta altura (en anchos de
# hombro bajo la línea de los hombros; y crece hacia abajo). En LSC-54 las muñecas
# en reposo están a ~1,36 (percentil 5: 0,86) y durante la seña a ~0,03.
ALTURA_ACTIVA = 0.8
MOVIMIENTO_ACTIVO = 0.12  # desplazamiento de la muñeca por cuadro (anchos de hombro)

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


class ClasificadorPalabras:
    """Carga modelo_palabras.pkl (generado por scripts/entrenar_palabras.py)."""

    def __init__(self, ruta: Path = config.RUTA_MODELO_PALABRAS) -> None:
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontró {ruta}. Ejecute primero: python scripts/entrenar_palabras.py"
            )
        paquete = joblib.load(ruta)
        self._modelo = paquete["modelo"]
        self.palabras: list[str] = list(self._modelo.classes_)
        self.nombres: dict[str, str] = paquete.get("nombres", {})
        self.metadatos: dict = paquete.get("metadatos", {})

    def predecir(self, cuadros: np.ndarray) -> Prediccion:
        proba = self._modelo.predict_proba(vector_secuencia(cuadros).reshape(1, -1))[0]
        i = int(np.argmax(proba))
        clave = self.palabras[i]
        return Prediccion(self.nombres.get(clave, clave), float(proba[i]))


@dataclass
class EstadoSegmentador:
    grabando: bool
    cuadros: int  # cuadros en la seña en curso
    terminada: np.ndarray | None  # secuencia completa cuando la seña termina


class SegmentadorSenas:
    """Máquina de estados reposo → seña → reposo sobre el flujo de cuadros en vivo."""

    def __init__(self) -> None:
        self._previo: deque[np.ndarray] = deque(maxlen=MARGEN)
        self._actual: list[np.ndarray] = []
        self._reposo = 0
        self._activos = 0
        self._munecas_previas: list[np.ndarray] = []

    @property
    def grabando(self) -> bool:
        return bool(self._actual)

    def reiniciar(self) -> None:
        self._previo.clear()
        self._actual = []
        self._reposo = 0
        self._activos = 0
        self._munecas_previas = []

    def _es_activo(self, f: np.ndarray) -> bool:
        munecas = _munecas(f)
        levantada = _levantada(f, munecas)
        movida = bool(self._munecas_previas and munecas) and any(
            min(np.linalg.norm(m - p) for p in self._munecas_previas) > MOVIMIENTO_ACTIVO for m in munecas
        )
        self._munecas_previas = munecas
        return levantada or movida

    def agregar(self, f: np.ndarray | None) -> EstadoSegmentador:
        if f is None:  # sin pose en este cuadro: se ignora
            return EstadoSegmentador(self.grabando, len(self._actual), None)

        activo = self._es_activo(f)
        terminada = None
        if not self._actual:
            if activo:
                self._actual = [*self._previo, f]
                self._reposo = 0
                self._activos = 1
            else:
                self._previo.append(f)
        else:
            self._actual.append(f)
            self._reposo = 0 if activo else self._reposo + 1
            self._activos += int(activo)
            if self._reposo >= CUADROS_FIN or len(self._actual) >= MAX_CUADROS:
                seq = np.array(self._actual)
                if self._reposo >= CUADROS_FIN:
                    seq = seq[: len(seq) - self._reposo + MARGEN]
                if self._activos >= MIN_ACTIVOS:
                    terminada = seq
                self._actual = []
                self._previo.clear()
                self._reposo = 0
        return EstadoSegmentador(self.grabando, len(self._actual), terminada)
