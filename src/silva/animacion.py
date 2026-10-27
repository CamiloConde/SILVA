"""Palabras a señas: animación de esqueleto de cada palabra del vocabulario.

Sirve en el sentido contrario a la traducción: la persona oyente escribe (Responder) y, además del
texto, ve cómo se hace cada seña conocida; también se puede ver la seña de cualquier palabra de la
lista. Las animaciones salen de grabaciones de LSC-54 (scripts/generar_animaciones.py): son solo
puntos (pose + manos, en anchos de hombro respecto al centro de los hombros), no video.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from silva import config
from silva.cuerpo import N_MANO, N_POSE

# Formas alternativas que también activan una seña
VARIANTES = {"como estas": "¿Cómo está?", "buen dia": "Buenos días", "de nada": "De nada", "lo siento": "Lo siento"}


def normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9ñ ]", " ", sin_tildes).split())


def _suavizar(cuadros: np.ndarray) -> np.ndarray:
    """Promedio móvil (¼, ½, ¼) en el tiempo: quita el temblor de los puntos de la grabación."""
    s = cuadros.astype(np.float32).copy()
    s[1:-1] = 0.25 * cuadros[:-2] + 0.5 * cuadros[1:-1] + 0.25 * cuadros[2:]
    for i in (N_POSE + 42, N_POSE + N_MANO + 42):  # la presencia de cada mano no se promedia
        s[:, i] = cuadros[:, i]
    return s


# Colores de la figura animada
PIEL, PIEL_BORDE, ROPA, PELO = "#D9A27F", "#B4795A", "#1F4FD8", "#16181D"
MANGA, MANGA_BORDE = "#3A66E6", "#15379A"  # el brazo se distingue de la camisa cuando pasa por delante del pecho
DEDOS = ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))


def dibujar_persona(p: QPainter, f: np.ndarray, punto, escala: float) -> None:
    """Una persona de frente (cabeza, camisa con mangas y manos con dedos) en la posición del cuadro f.

    f: 100 valores (pose y ambas manos, en anchos de hombro respecto al centro de los hombros).
    """
    pose = f[:N_POSE].reshape(-1, 2)  # nariz, hombro izq., hombro der., codos, muñecas
    redondo = (Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    # torso (la camisa) y cuello
    hi, hd = pose[1], pose[2]
    torso = QPainterPath(punto(*hi))
    for x, y in (hd, (hd[0] * 0.85, 2.2), (hi[0] * 0.85, 2.2)):
        torso.lineTo(punto(x, y))
    torso.closeSubpath()
    p.setPen(QPen(QColor(ROPA), escala * 0.2, *redondo))
    p.setBrush(QColor(ROPA))
    p.drawPath(torso)
    cuello = punto(pose[0][0], -0.05)
    p.setPen(QPen(QColor(PIEL), escala * 0.2, *redondo))
    p.drawLine(cuello, punto(pose[0][0], pose[0][1] + 0.1))
    # cabeza: cara, pelo y ojos
    cabeza = punto(pose[0][0], pose[0][1] - 0.05)
    rx, ry = 0.27 * escala, 0.33 * escala
    caja = QRectF(cabeza.x() - rx, cabeza.y() - ry, 2 * rx, 2 * ry)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(PIEL))
    p.drawEllipse(caja)
    p.setBrush(QColor(PELO))
    p.drawChord(caja.adjusted(-0.02 * escala, -0.03 * escala, 0.02 * escala, 0), 20 * 16, 140 * 16)
    for dx in (-0.1, 0.1):
        p.drawEllipse(punto(pose[0][0] + dx, pose[0][1] - 0.04), 0.025 * escala, 0.03 * escala)
    # brazos con manga larga; el antebrazo llega a la muñeca de la mano (si se ve), así no queda separado de ella
    p.setBrush(Qt.NoBrush)
    for (hombro, codo, muneca), inicio in (((1, 3, 5), N_POSE), ((2, 4, 6), N_POSE + N_MANO)):
        fin = f[inicio:inicio + 2] if f[inicio + 42] > 0 else pose[muneca]
        brazo = [punto(*pose[hombro]), punto(*pose[codo]), punto(*fin)]
        for color, grosor in ((MANGA_BORDE, 0.27), (MANGA, 0.22)):
            p.setPen(QPen(QColor(color), escala * grosor, *redondo))
            p.drawPolyline(brazo)
    # manos: palma y dedos con contorno (sin puntos)
    for inicio, muneca in ((N_POSE, 5), (N_POSE + N_MANO, 6)):
        if f[inicio + 42] <= 0:  # sin mano en este cuadro: un puño en la muñeca
            p.setPen(QPen(QColor(PIEL_BORDE), max(escala * 0.012, 1)))
            p.setBrush(QColor(PIEL))
            p.drawEllipse(punto(*pose[muneca]), 0.09 * escala, 0.09 * escala)
            continue
        m = f[inicio:inicio + 42].reshape(21, 2)
        palma = float(np.hypot(*(m[9] - m[0])))
        ancho_dedo = max(palma * 0.24 * escala, 2.5)
        contorno = QPainterPath(punto(*m[0]))
        for k in (1, 5, 9, 13, 17):
            contorno.lineTo(punto(*m[k]))
        contorno.closeSubpath()
        for color, grosor in ((PIEL_BORDE, ancho_dedo * 1.3), (PIEL, ancho_dedo)):
            p.setPen(QPen(QColor(color), grosor, *redondo))
            p.setBrush(QColor(color))
            p.drawPath(contorno)
            for dedo in DEDOS:
                p.drawPolyline([punto(*m[k]) for k in dedo])


class AnimacionesSenas:
    def __init__(self, ruta: Path = config.RUTA_ANIMACIONES) -> None:
        d = np.load(ruta)
        self.nombres: list[str] = [str(n) for n in d["nombres"]]
        self._cuadros = {n: _suavizar(a) for n, a in zip(self.nombres, d["animaciones"])}
        self._por_forma = {normalizar(n): n for n in self.nombres}
        self._por_forma.update({k: v for k, v in VARIANTES.items() if v in self._cuadros})
        self._largo_max = max(len(f.split()) for f in self._por_forma)

    def cuadros(self, nombre: str) -> np.ndarray:
        return self._cuadros[nombre]

    def buscar(self, texto: str) -> list[str]:
        """Señas conocidas que aparecen en el texto, en orden (las frases largas primero: «muchas gracias»)."""
        palabras = normalizar(texto).split()
        encontradas, i = [], 0
        while i < len(palabras):
            for largo in range(min(self._largo_max, len(palabras) - i), 0, -1):
                nombre = self._por_forma.get(" ".join(palabras[i:i + largo]))
                if nombre is not None:
                    encontradas.append(nombre)
                    i += largo
                    break
            else:
                i += 1
        return encontradas


class AnimacionSena(QWidget):
    """Dibuja en bucle una o varias señas (figura de esqueleto, vista de frente)."""

    def __init__(self, animaciones: AnimacionesSenas, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._animaciones = animaciones
        self._lista: list[str] = []
        self._actual = 0
        self._cuadro = 0
        self._pausa = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._avanzar)
        self.setAttribute(Qt.WA_TranslucentBackground)

    @property
    def senas(self) -> list[str]:
        return list(self._lista)

    def mostrar(self, nombres: list[str]) -> None:
        self._lista = [n for n in nombres if n in self._animaciones.nombres]
        self._actual, self._cuadro, self._pausa = 0, 0, 0
        if self._lista:
            self._timer.start(33)  # ~30 cuadros/s, la velocidad de la grabación
        else:
            self._timer.stop()
        self.update()

    def detener(self) -> None:
        self._timer.stop()
        self._lista = []

    def _avanzar(self) -> None:
        total = len(self._animaciones.cuadros(self._lista[self._actual]))
        if self._cuadro < total - 1:
            self._cuadro += 1
        elif self._pausa < 18:  # ~0,6 s quieto al final de cada seña
            self._pausa += 1
        else:
            self._actual = (self._actual + 1) % len(self._lista)
            self._cuadro, self._pausa = 0, 0
        self.update()

    def paintEvent(self, _evento) -> None:
        if not self._lista:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ancho, alto = self.width(), self.height()
        p.setPen(QPen(QColor("#E3E1DA"), 1))  # identidad v2: tarjeta blanca con borde de línea
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(0.5, 0.5, ancho - 1, alto - 1), 6, 6)
        p.setPen(Qt.NoPen)

        nombre = self._lista[self._actual]
        f = self._animaciones.cuadros(nombre)[self._cuadro]
        escala = min(ancho / 4.6, (alto - 70) / 4.6)
        origen = QPointF(ancho / 2, 30 + (alto - 70) * 0.44)

        def punto(x: float, y: float) -> QPointF:
            return QPointF(origen.x() + x * escala, origen.y() + y * escala)

        dibujar_persona(p, f, punto, escala)
        # rótulo
        p.setPen(QColor("#16181D"))
        p.setFont(QFont("IBM Plex Sans", 15, QFont.DemiBold))
        p.drawText(QRectF(0, alto - 58, ancho, 30), Qt.AlignCenter, nombre)
        p.setPen(QColor("#5B616B"))
        p.setFont(QFont("IBM Plex Mono", 9))
        pie = "SEÑA EN LSC" if len(self._lista) == 1 else f"SEÑA {self._actual + 1} DE {len(self._lista)} EN LSC"
        p.drawText(QRectF(0, alto - 30, ancho, 20), Qt.AlignCenter, pie)
        p.end()
