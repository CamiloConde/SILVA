"""Detección de cuerpo + ambas manos y características para señas con movimiento (modo Palabras).

A diferencia de las letras, en una palabra importa dónde está la mano respecto
al cuerpo (frente, pecho, mentón) y cómo se mueve. Por eso cada cuadro se
describe en un sistema de referencia centrado en los hombros:
  origen = punto medio entre los hombros, escala = ancho de hombros.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from silva import config
from silva.modelo import Landmark

# Índices de MediaPipe Pose usados: nariz, hombros, codos y muñecas (izq./der. de la persona)
POSE_USADOS = [0, 11, 12, 13, 14, 15, 16]
ESPEJO_POSE = [0, 2, 1, 4, 3, 6, 5]  # posición de cada punto al espejar (izquierda <-> derecha)
MUNECA_IZQ, MUNECA_DER = 15, 16

N_POSE = len(POSE_USADOS) * 2
N_MANO = 21 * 2 + 1  # 21 puntos (x, y) + bandera de presencia
N_CARACTERISTICAS_CUADRO = N_POSE + 2 * N_MANO  # 100


@dataclass
class CuadroCuerpo:
    """Resultado de un cuadro: pose (33 puntos) y manos asignadas a cada lado de la persona."""

    pose: list[Landmark] | None
    mano_izquierda: list[Landmark] | None
    mano_derecha: list[Landmark] | None
    aspecto: float  # ancho / alto de la imagen

    @property
    def hay_mano(self) -> bool:
        return self.mano_izquierda is not None or self.mano_derecha is not None


def asignar_manos(pose: list[Landmark] | None, manos: list[list[Landmark]]):
    """Asigna cada mano detectada al lado de la persona según la muñeca de la pose más cercana.

    No se usa la etiqueta de lateralidad de MediaPipe porque depende de si la
    imagen está espejada, y eso cambia entre videos y cámara web.
    """
    if not manos:
        return None, None
    if pose is None:  # sin pose: la mano más a la derecha de la imagen es la izquierda de la persona
        ordenadas = sorted(manos, key=lambda m: m[0].x)
        if len(ordenadas) == 1:
            return (ordenadas[0], None) if ordenadas[0][0].x > 0.5 else (None, ordenadas[0])
        return ordenadas[1], ordenadas[0]
    def dist(mano, muneca):
        return (mano[0].x - muneca.x) ** 2 + (mano[0].y - muneca.y) ** 2

    mi, md = pose[MUNECA_IZQ], pose[MUNECA_DER]
    if len(manos) == 1:
        m = manos[0]
        return (m, None) if dist(m, mi) <= dist(m, md) else (None, m)
    a, b = manos[0], manos[1]
    if dist(a, mi) + dist(b, md) <= dist(b, mi) + dist(a, md):
        return a, b
    return b, a


def caracteristicas_cuadro(c: CuadroCuerpo) -> np.ndarray | None:
    """Vector de 100 valores del cuadro, o None si no hay pose (no hay referencia corporal)."""
    if c.pose is None:
        return None
    a = c.aspecto

    def xy(lm: Landmark) -> tuple[float, float]:
        return lm.x * a, lm.y  # unidades proporcionales (independiente de 4:3 o 16:9)

    hi, hd = np.array(xy(c.pose[11])), np.array(xy(c.pose[12]))
    origen = (hi + hd) / 2
    escala = float(np.linalg.norm(hi - hd))
    if escala < 1e-6:
        return None

    def normalizar(puntos: list[Landmark]) -> np.ndarray:
        return ((np.array([xy(p) for p in puntos]) - origen) / escala).ravel()

    partes = [normalizar([c.pose[i] for i in POSE_USADOS])]
    for mano in (c.mano_izquierda, c.mano_derecha):
        if mano is None:
            partes.append(np.zeros(N_MANO))
        else:
            partes.append(np.append(normalizar(mano), 1.0))
    return np.concatenate(partes).astype(np.float32)


def espejar(secuencia: np.ndarray) -> np.ndarray:
    """Espeja una secuencia (T x 100): simula a una persona zurda/diestra."""
    s = secuencia.copy()
    pose = s[:, :N_POSE].reshape(len(s), -1, 2)[:, ESPEJO_POSE]
    pose[..., 0] *= -1
    izq = s[:, N_POSE:N_POSE + N_MANO].copy()
    der = s[:, N_POSE + N_MANO:].copy()
    for mano in (izq, der):
        mano[:, 0:42:2] *= -1 * (mano[:, 42:43] > 0)  # solo si la mano está presente
    s[:, :N_POSE] = pose.reshape(len(s), -1)
    s[:, N_POSE:N_POSE + N_MANO] = der
    s[:, N_POSE + N_MANO:] = izq
    return s


class DetectorCuerpo:
    """Pose y ambas manos con MediaPipe.

    - La pose y las manos se calculan en paralelo (MediaPipe libera el GIL): ~17 ms en vez de ~29.
    - Si se pierde una mano que está en uso, se busca en un recorte ampliado alrededor de la muñeca
      que da la pose (`config.RECUPERAR_MANOS`): con la mano pequeña en la imagen o borrosa, el
      detector de palmas de MediaPipe falla mucho más que sobre la mano ampliada.
    """

    def __init__(
        self,
        ruta_manos: Path = config.RUTA_MODELO_MANOS,
        ruta_pose: Path = config.RUTA_MODELO_POSE,
        recuperar: bool = config.RECUPERAR_MANOS,
    ) -> None:
        for ruta in (ruta_manos, ruta_pose):
            if not ruta.exists():
                raise FileNotFoundError(f"No se encontró el modelo de MediaPipe en {ruta}")
        self._manos = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ruta_manos)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=config.CONFIANZA_MANOS_PALABRAS,
            min_hand_presence_confidence=config.CONFIANZA_MANOS_PALABRAS,
            min_tracking_confidence=config.CONFIANZA_MANOS_PALABRAS,
        ))
        self._pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ruta_pose)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
        ))
        # uno por lado, para buscar las dos manos a la vez
        self._recuperadores = [vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ruta_manos)),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=config.CONFIANZA_RECUPERACION,
            min_hand_presence_confidence=config.CONFIANZA_RECUPERACION,
        )) for _ in range(2)] if recuperar else []
        self._hilos = ThreadPoolExecutor(max_workers=2)
        self._ultimo_ms = -1

    def detectar(self, cuadro_bgr: np.ndarray, marca_tiempo_ms: int) -> CuadroCuerpo:
        marca_tiempo_ms = max(marca_tiempo_ms, self._ultimo_ms + 1)
        self._ultimo_ms = marca_tiempo_ms
        alto, ancho = cuadro_bgr.shape[:2]
        rgb = cv2.cvtColor(cuadro_bgr, cv2.COLOR_BGR2RGB)
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        en_curso = self._hilos.submit(self._pose.detect_for_video, imagen, marca_tiempo_ms)
        r_manos = self._manos.detect_for_video(imagen, marca_tiempo_ms)
        r_pose = en_curso.result()
        pose = [Landmark(p.x, p.y) for p in r_pose.pose_landmarks[0]] if r_pose.pose_landmarks else None
        manos = [[Landmark(p.x, p.y) for p in m] for m in r_manos.hand_landmarks]
        izquierda, derecha = asignar_manos(pose, manos)
        if self._recuperadores and pose is not None:
            izquierda, derecha = self._recuperar(rgb, pose, izquierda, derecha)
        return CuadroCuerpo(pose, izquierda, derecha, ancho / alto)

    def _recuperar(self, rgb: np.ndarray, pose: list[Landmark], izquierda, derecha):
        """Busca las manos perdidas que están en uso; las dos a la vez si faltan ambas."""
        alto, ancho = rgb.shape[:2]
        hombros = float(np.hypot((pose[11].x - pose[12].x) * ancho, (pose[11].y - pose[12].y) * alto))
        if hombros < 8:
            return izquierda, derecha
        altura_hombros = (pose[11].y + pose[12].y) / 2 * alto
        tareas = {}
        for lado, (mano, puntos, otra) in enumerate(((izquierda, MANO_POSE_IZQ, derecha),
                                                     (derecha, MANO_POSE_DER, izquierda))):
            if mano is not None or pose[puntos[0]].y * alto > altura_hombros + 1.2 * hombros:
                continue  # la mano está detectada, o abajo en reposo
            tareas[lado] = self._hilos.submit(self._buscar_en_recorte, self._recuperadores[lado], rgb,
                                              pose, puntos, otra, hombros)
        if 0 in tareas:
            izquierda = tareas[0].result()
        if 1 in tareas:
            derecha = tareas[1].result()
        return izquierda, derecha

    @staticmethod
    def _buscar_en_recorte(detector, rgb, pose, puntos, otra, hombros) -> list[Landmark] | None:
        alto, ancho = rgb.shape[:2]
        centro = np.mean([(pose[i].x * ancho, pose[i].y * alto) for i in puntos], axis=0)
        lado = config.RECORTE_RECUPERACION * hombros
        x0, y0 = int(centro[0] - lado / 2), int(centro[1] - lado / 2)
        x1, y1 = int(x0 + lado), int(y0 + lado)
        # la parte del recorte que cae fuera de la imagen queda negra
        recorte = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
        ax0, ay0, ax1, ay1 = max(x0, 0), max(y0, 0), min(x1, ancho), min(y1, alto)
        if ax1 <= ax0 or ay1 <= ay0:
            return None
        recorte[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = rgb[ay0:ay1, ax0:ax1]
        recorte = cv2.resize(recorte, (config.TAM_RECORTE, config.TAM_RECORTE), interpolation=cv2.INTER_LINEAR)
        r = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=recorte))
        if not r.hand_landmarks:
            return None
        mano = [Landmark((x0 + p.x * (x1 - x0)) / ancho, (y0 + p.y * (y1 - y0)) / alto) for p in r.hand_landmarks[0]]
        muneca = pose[puntos[0]]
        if np.hypot((mano[0].x - muneca.x) * ancho, (mano[0].y - muneca.y) * alto) > 0.6 * lado:
            return None  # no es la mano de esta muñeca
        if otra is not None:  # ¿encontró otra vez la otra mano? (con las manos juntas, la muñeca sola no basta)
            distancia = np.mean([np.hypot((m.x - o.x) * ancho, (m.y - o.y) * alto) for m, o in zip(mano, otra)])
            if distancia < 0.05 * lado:
                return None
        return mano

    def cerrar(self) -> None:
        self._manos.close()
        self._pose.close()
        for r in self._recuperadores:
            r.close()
        self._hilos.shutdown(wait=False)


POSE_CONEXIONES = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24)]
# Puntos de la mano que también estima la pose: muñeca, meñique, índice y pulgar (izq./der. de la persona)
MANO_POSE_IZQ = (15, 17, 19, 21)
MANO_POSE_DER = (16, 18, 20, 22)


def _dibujar_mano_aproximada(cuadro_bgr: np.ndarray, puntos: list[tuple[int, int]], color) -> None:
    alto, ancho = cuadro_bgr.shape[:2]
    if not all(-ancho < x < 2 * ancho and -alto < y < 2 * alto for x, y in puntos):
        return
    muneca, menique, indice, pulgar = puntos
    for destino in (menique, indice, pulgar):
        cv2.line(cuadro_bgr, muneca, destino, (150, 150, 150), 1, cv2.LINE_AA)
    cv2.line(cuadro_bgr, menique, indice, (150, 150, 150), 1, cv2.LINE_AA)
    for q in puntos:
        cv2.circle(cuadro_bgr, q, 4, color, 1, cv2.LINE_AA)  # círculos huecos = posición aproximada


def dibujar_cuerpo(cuadro_bgr: np.ndarray, c: CuadroCuerpo) -> None:
    """Dibuja hombros, brazos y ambas manos sobre el cuadro (in situ)."""
    from silva.detector_manos import CONEXIONES_MANO

    alto, ancho = cuadro_bgr.shape[:2]

    def px(lm: Landmark) -> tuple[int, int]:
        return int(lm.x * ancho), int(lm.y * alto)

    if c.pose is not None:
        for a, b in POSE_CONEXIONES:
            cv2.line(cuadro_bgr, px(c.pose[a]), px(c.pose[b]), (150, 148, 145), 2, cv2.LINE_AA)
    for mano, color, puntos_pose in ((c.mano_izquierda, (245, 245, 245), MANO_POSE_IZQ),
                                     (c.mano_derecha, (245, 245, 245), MANO_POSE_DER)):
        if mano is None:
            # MediaPipe perdió la mano (movimiento rápido, desenfoque): se dibuja la mano aproximada
            # que da el esqueleto del cuerpo, para que el seguimiento no "desaparezca" en pantalla.
            if c.pose is not None:
                _dibujar_mano_aproximada(cuadro_bgr, [px(c.pose[i]) for i in puntos_pose], color)
            continue
        puntos = [px(lm) for lm in mano]
        for a, b in CONEXIONES_MANO:
            cv2.line(cuadro_bgr, puntos[a], puntos[b], (205, 203, 200), 2, cv2.LINE_AA)
        for p in puntos:
            cv2.circle(cuadro_bgr, p, 3, color, cv2.FILLED, cv2.LINE_AA)


def evaluar_encuadre(c: CuadroCuerpo) -> str | None:
    """Indicación para ubicarse como en los videos de entrenamiento, o None si el encuadre es bueno.

    Las indicaciones laterales son desde el punto de vista de la persona: en la imagen de la cámara
    (sin espejo) x crece hacia la izquierda de la persona.
    """
    if c.pose is None:
        return None
    hi, hd, nariz = c.pose[11], c.pose[12], c.pose[0]
    ancho = abs(hi.x - hd.x) * c.aspecto / (16 / 9)  # en proporción de una imagen 16:9
    centro_x = (hi.x + hd.x) / 2
    altura_hombros = (hi.y + hd.y) / 2
    if ancho < config.ENCUADRE_HOMBROS[0]:
        return "Acércate un poco a la cámara"
    if ancho > config.ENCUADRE_HOMBROS[1]:
        return "Aléjate un poco: las manos deben caber en la imagen"
    if centro_x > config.ENCUADRE_CENTRO_X[1]:
        return "Muévete un poco hacia tu derecha"
    if centro_x < config.ENCUADRE_CENTRO_X[0]:
        return "Muévete un poco hacia tu izquierda"
    if nariz.y < config.ENCUADRE_NARIZ_Y_MIN:
        return "Baja un poco la cámara (o inclínala hacia abajo)"
    if altura_hombros > config.ENCUADRE_HOMBROS_Y_MAX:
        return "Sube un poco la cámara"
    return None
