"""Letras con movimiento del alfabeto de LSC (G, H, J, M, N, Ñ, P, Q, S, Z).

El clasificador de letras estáticas mira un solo cuadro; estas letras dependen de la trayectoria.
Aquí se segmenta el movimiento de la mano en vivo y se clasifica cada movimiento completo:

1. `SegmentadorLetras`: cuando la mano empieza a moverse (traslación o cambio de forma) se graban
   los cuadros hasta que vuelve a quedarse quieta.
2. `caracteristicas_secuencia`: el movimiento se remuestrea a 6 cuadros, como las señas de LSC70
   con que se entrenó (scripts/entrenar_letras_movimiento.py), y se describe con la forma de la
   mano en cada cuadro y la trayectoria de la muñeca, en tamaños de mano.
3. `ClasificadorMovimiento`: decide entre las 27 letras. Solo se escriben las letras con movimiento
   y solo si la muñeca se desplazó: pasar de una letra estática a otra cambia la forma de la mano
   pero casi no la mueve de lugar. Las estáticas las sigue resolviendo el otro modelo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from silva import config
from silva.modelo import Prediccion

CUADROS = 6  # cada seña de LSC70 son 6 imágenes a lo largo del movimiento
OTRA = "__otra__"  # el movimiento no es una letra con trazo (p. ej. pasar de una letra a otra)
LETRAS_MOVIMIENTO = [l for l in config.LETRAS if l not in config.LETRAS_ESTATICAS]


def a_isotropicas(puntos: np.ndarray, ancho: int, alto: int) -> np.ndarray:
    """Coordenadas de imagen (0-1) → mismas unidades en x e y (la x se multiplica por ancho/alto)."""
    salida = np.array(puntos, np.float32, copy=True)
    salida[..., 0] *= ancho / alto
    return salida


def remuestrear(puntos: np.ndarray, n: int = CUADROS) -> np.ndarray:
    """(T, 21, 2) → (n, 21, 2) por interpolación lineal en el tiempo."""
    t = len(puntos)
    if t == n:
        return puntos.astype(np.float32)
    origen = np.linspace(0, t - 1, n)
    i0 = np.floor(origen).astype(int)
    i1 = np.minimum(i0 + 1, t - 1)
    f = (origen - i0)[:, None, None]
    return ((1 - f) * puntos[i0] + f * puntos[i1]).astype(np.float32)


def caracteristicas_secuencia(puntos: np.ndarray, izquierda: bool) -> np.ndarray:
    """Vector fijo de un movimiento: (T, 21, 2) en coordenadas isotrópicas → 264 valores.

    - forma de la mano en cada uno de los 6 cuadros (21 puntos respecto a la muñeca, en tamaños de mano);
    - trayectoria de la muñeca respecto al primer cuadro (en tamaños de mano);
    - recorrido total y desplazamiento neto.
    La x se espeja para la mano izquierda, como en `normalizar_landmarks`.
    """
    p = remuestrear(np.asarray(puntos, np.float32))
    if izquierda:
        p = p.copy()
        p[..., 0] = -p[..., 0]
    muneca = p[:, 0:1, :]
    escalas = np.linalg.norm(p[:, 9] - p[:, 0], axis=1)
    escalas = np.where(escalas > 1e-6, escalas, 1.0)
    forma = (p - muneca) / escalas[:, None, None]
    escala = float(np.median(escalas))
    trayectoria = (p[:, 0] - p[0, 0]) / escala
    pasos = np.linalg.norm(np.diff(trayectoria, axis=0), axis=1)
    return np.concatenate([
        forma.reshape(-1),
        trayectoria[1:].reshape(-1),
        [pasos.sum(), np.linalg.norm(trayectoria[-1])],
    ]).astype(np.float32)


@dataclass(frozen=True)
class EstadoMovimiento:
    moviendo: bool
    terminado: tuple[np.ndarray, bool] | None = None  # (puntos, es_izquierda) de un movimiento completo


FPS_REFERENCIA = 30  # los umbrales de config están en «por cuadro a 30 cuadros/s»
_HOLGURA = 1e-6


class SegmentadorLetras:
    """Detecta el tramo en que la mano se mueve.

    El movimiento de un cuadro es el desplazamiento medio de los 21 puntos respecto al cuadro
    anterior, en tamaños de mano: incluye trasladar la mano y cambiar su forma. Una letra estática
    sostenida queda muy por debajo del umbral; trazar la J o la Z, muy por encima.

    Se mide en segundos (como silva.palabras.SegmentadorSenas): los umbrales se calibraron a 30 cuadros/s y
    un teléfono procesa unos 19. Contando cuadros, el movimiento por cuadro crecía y el trazo empezaba con
    cualquier gesto, y la pausa final se alargaba. Sin reloj se supone 30 cuadros/s: da lo mismo que antes.
    """

    def __init__(self, umbral_inicio: float = config.MOVIMIENTO_INICIO,
                 umbral_fin: float = config.MOVIMIENTO_FIN,
                 cuadros_quieto: int = config.CUADROS_QUIETO,
                 min_cuadros: int = config.MIN_CUADROS_MOVIMIENTO,
                 max_cuadros: int = config.MAX_CUADROS_MOVIMIENTO) -> None:
        self.umbral_inicio = umbral_inicio
        self.umbral_fin = umbral_fin
        self.cuadros_quieto = cuadros_quieto
        self.min_cuadros = min_cuadros
        self.max_cuadros = max_cuadros
        self.reiniciar()

    def reiniciar(self) -> None:
        self._anterior: np.ndarray | None = None
        self._t_anterior: float | None = None
        self._previos: list[tuple[float, np.ndarray]] = []  # los últimos cuadros quietos: el inicio del trazo
        self._grabados: list[np.ndarray] = []
        self._tiempos: list[float] = []
        self._izquierda: list[bool] = []
        self._ultimo_movimiento = -1  # índice en _grabados del último cuadro que se movió
        self._moviendo = False
        self._velocidades: list[float] = []
        self._n = 0  # cuadros recibidos: reloj por omisión, a 30 cuadros/s

    @property
    def moviendo(self) -> bool:
        return self._moviendo

    def agregar(self, puntos: np.ndarray | None, izquierda: bool = False, t: float | None = None) -> EstadoMovimiento:
        """Puntos isotrópicos (21, 2) de la mano en este cuadro, o None si no se ve; t = momento en segundos."""
        if t is None:
            t = self._n / FPS_REFERENCIA
        self._n += 1
        if puntos is None:
            # una mano rápida sale borrosa y MediaPipe la pierde un instante: el trazo sigue si vuelve pronto
            if self._moviendo and self._t_anterior is not None and t - self._t_anterior <= config.SEGUNDOS_SIN_MANO_TRAZO:
                return EstadoMovimiento(True)
            terminado = self._cerrar()  # sin mano: el movimiento en curso termina aquí
            self._anterior, self._t_anterior, self._previos, self._velocidades = None, None, [], []
            return EstadoMovimiento(False, terminado)

        velocidad = 0.0  # desplazamiento por cuadro a 30 cuadros/s (en tamaños de mano)
        if self._anterior is not None and self._t_anterior is not None:
            escala = max(float(np.linalg.norm(puntos[9] - puntos[0])), 1e-6)
            dt = max(t - self._t_anterior, 1e-3)
            velocidad = float(np.linalg.norm(puntos - self._anterior, axis=1).mean()) / escala / (dt * FPS_REFERENCIA)
        self._anterior, self._t_anterior = puntos, t
        self._velocidades = (self._velocidades + [velocidad])[-3:]
        media = float(np.mean(self._velocidades))

        if not self._moviendo:
            self._previos = (self._previos + [(t, puntos)])[-3:]
            if len(self._velocidades) == 3 and media >= self.umbral_inicio:
                self._moviendo = True
                self._tiempos = [tp for tp, _ in self._previos]
                self._grabados = [p for _, p in self._previos]
                self._izquierda = [izquierda] * len(self._grabados)
                self._ultimo_movimiento = len(self._grabados) - 1
            return EstadoMovimiento(self._moviendo)

        self._grabados.append(puntos)
        self._tiempos.append(t)
        self._izquierda.append(izquierda)
        if velocidad >= self.umbral_fin:
            self._ultimo_movimiento = len(self._grabados) - 1
        quieto = t - self._tiempos[self._ultimo_movimiento] >= self.cuadros_quieto / FPS_REFERENCIA - _HOLGURA
        if quieto or t - self._tiempos[0] >= (self.max_cuadros - 1) / FPS_REFERENCIA - _HOLGURA:
            terminado = self._cerrar()
            self._previos = [(t, puntos)]
            return EstadoMovimiento(False, terminado)
        return EstadoMovimiento(True)

    def _cerrar(self) -> tuple[np.ndarray, bool] | None:
        if not self._moviendo:
            return None
        self._moviendo = False
        # sin la cola quieta del final, salvo un cuadro (donde termina el trazo)
        fin = min(self._ultimo_movimiento + 2, len(self._grabados))
        grabados, tiempos = self._grabados[:fin], self._tiempos[:fin]
        izquierda = bool(np.mean(self._izquierda) >= 0.5)
        self._grabados, self._tiempos, self._izquierda, self._ultimo_movimiento = [], [], [], -1
        if tiempos[-1] - tiempos[0] < (self.min_cuadros - 1) / FPS_REFERENCIA - _HOLGURA:
            return None
        return np.stack(grabados), izquierda


class ClasificadorMovimiento:
    """Carga `modelo_letras_movimiento.pkl` (scripts/entrenar_letras_movimiento.py)."""

    def __init__(self, ruta_modelo: Path = config.RUTA_MODELO_LETRAS_MOVIMIENTO) -> None:
        if not ruta_modelo.exists():
            raise FileNotFoundError(
                f"No se encontró {ruta_modelo}. Ejecute: python scripts/entrenar_letras_movimiento.py")
        paquete = joblib.load(ruta_modelo)
        self._modelo = paquete["modelo"]
        self.clases: list[str] = list(self._modelo.classes_)
        self.metadatos: dict = paquete.get("metadatos", {})
        self.letras: list[str] = [l for l in LETRAS_MOVIMIENTO if l in self.clases]

    def predecir(self, puntos: np.ndarray, izquierda: bool) -> Prediccion:
        """Letra más probable del movimiento y su probabilidad; OTRA si la muñeca casi no se desplazó."""
        x = caracteristicas_secuencia(puntos, izquierda)
        if x[-2] < config.RECORRIDO_MINIMO:  # recorrido de la muñeca
            return Prediccion(OTRA, 1.0)
        proba = self._modelo.predict_proba(x.reshape(1, -1))[0]
        i = int(np.argmax(proba))
        return Prediccion(self.clases[i], float(proba[i]))
