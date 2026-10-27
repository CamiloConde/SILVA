"""VentanaPrincipal: interfaz de escritorio en PySide6 (Qt), con la identidad v2 de SILVA.

La cámara y MediaPipe corren en un hilo aparte (TrabajadorVideo): la ventana
solo recibe cada cuadro ya procesado y nunca se congela mientras se detecta.
Es el paralelismo del diagrama de actividades (Figura 6): una rama muestra el
video y la otra detecta la mano.

Diseño (docs: «SILVA - Propuesta de diseño 2»): papel de fondo, cámara en tinta,
azul para la acción y lo confirmado, ocre para «leyendo seña»; IBM Plex Sans.
"""

from __future__ import annotations

import contextlib
import importlib
import math
import os
import subprocess
import sys
import threading
import time
import traceback

import cv2
import numpy as np
from PySide6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF, QSettings, QSize, Qt, QThread, QTimer,
    QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QGuiApplication, QIcon, QImage, QKeySequence, QPainter,
    QPainterPath, QPen, QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QDialog, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from silva import __version__, config
from silva.animacion import AnimacionesSenas, AnimacionSena
from silva.captura_video import CamaraNoDisponibleError
from silva.controlador import MODO_LETRAS, MODO_PALABRAS, ControladorSILVA, PalabraPendiente, ResultadoCuadro
from silva.cuerpo import dibujar_cuerpo, evaluar_encuadre
from silva.detector_manos import dibujar_mano
from silva.muestras_propias import GrabadorMuestras
from silva.sugerencias import Sugerencias

# Identidad v2
TINTA = "#16181D"  # texto, cámara
GRAFITO = "#5B616B"  # texto secundario
LINEA = "#E3E1DA"  # bordes, divisiones
PAPEL = "#F7F6F2"  # fondo
AZUL = "#1F4FD8"  # acción, confirmado
OCRE = "#E8A317"  # leyendo seña
BLANCO = "#FFFFFF"
APAGADO = "#A9ADB4"  # letras que aún no se reconocen, controles inactivos
BORDE_BOTON = "#CFCCC3"
SANS = "IBM Plex Sans"
MONO = "IBM Plex Mono"

AVISO_POCA_LUZ = "Poca luz: los movimientos salen borrosos y se pierde la mano. Enciende una luz de frente."
AVISO_SIN_MANO = "Mantén la mano dentro del recuadro."
AVISO_SIN_PERSONA = "Colócate frente a la cámara: deben verse los hombros y las manos."
AVISO_BORDE = "Aléjate un poco: una mano se sale del cuadro."

HOJA_ESTILO = f"""
QWidget {{ background: transparent; color: {TINTA}; font-family: "{SANS}"; font-size: 10pt; }}
#raiz, QDialog {{ background: {PAPEL}; }}
#cabecera {{ background: {BLANCO}; border-bottom: 1px solid {LINEA}; }}
#marca_texto {{ font-size: 15pt; font-weight: 700; letter-spacing: 2px; }}
QPushButton#pestana {{ background: transparent; border: none; border-bottom: 3px solid transparent; border-radius: 0;
                       color: {GRAFITO}; padding: 19px 20px 16px 20px; font-size: 11pt; }}
QPushButton#pestana:hover {{ color: {TINTA}; }}
QPushButton#pestana:checked {{ color: {TINTA}; font-weight: 600; border-bottom: 3px solid {AZUL}; }}
QPushButton#pestana:disabled {{ color: {APAGADO}; }}
QPushButton#cabecera_enlace {{ background: transparent; border: none; color: {TINTA}; font-size: 11pt; padding: 8px 14px; }}
QPushButton#cabecera_enlace:hover {{ color: {AZUL}; }}

#panel {{ background: {BLANCO}; border-left: 1px solid {LINEA}; }}
#separador {{ background: {LINEA}; max-height: 1px; min-height: 1px; }}
#seccion {{ color: {GRAFITO}; font-size: 10.5pt; font-weight: 600; }}
#tenue {{ color: {GRAFITO}; font-size: 9.5pt; }}
#estado {{ color: {GRAFITO}; font-size: 10pt; }}
#info_camara {{ color: {GRAFITO}; font-size: 10pt; }}
#letra {{ font-size: 66pt; font-weight: 700; color: {TINTA}; }}
#letra[tam="palabra"] {{ font-size: 28pt; }}
#letra[dudosa="true"] {{ color: {APAGADO}; }}
#porcentaje {{ font-size: 20pt; font-weight: 500; }}
#letra_abc {{ font-size: 11pt; font-weight: 500; color: {TINTA}; padding: 2px; }}
#letra_abc[apagada="true"] {{ color: {APAGADO}; }}
#letra_abc[activo="true"] {{ color: {AZUL}; text-decoration: underline; }}
#palabra_voc {{ font-size: 10pt; color: {TINTA}; padding: 2px 4px; }}
#palabra_voc[activo="true"] {{ color: {AZUL}; text-decoration: underline; }}

#texto_zona {{ background: {BLANCO}; border-top: 1px solid {LINEA}; }}
#texto {{ font-size: 28pt; font-weight: 500; }}
#texto[grande="true"] {{ font-size: 40pt; }}
#texto[vacio="true"] {{ font-size: 12pt; font-weight: 400; color: {GRAFITO}; }}
QPushButton#enlace {{ background: transparent; border: none; color: {AZUL}; text-decoration: underline; padding: 2px 6px;
                      font-size: 11pt; border-radius: 0; }}
QPushButton#enlace:hover {{ color: {TINTA}; }}
QPushButton#enlace_gris {{ background: transparent; border: none; color: {GRAFITO}; padding: 2px 6px; font-size: 10.5pt;
                           border-radius: 0; }}
QPushButton#enlace_gris:hover {{ color: {TINTA}; }}
QPushButton#accion {{ background: transparent; border: none; color: {AZUL}; padding: 2px 8px; font-size: 10.5pt;
                      font-weight: 500; }}
QPushButton#accion:disabled {{ color: {APAGADO}; }}

#barra {{ background: {PAPEL}; border-top: 1px solid {LINEA}; }}
QPushButton {{ font-size: 11pt; border-radius: 4px; padding: 9px 22px; }}
QPushButton#primario {{ background: {TINTA}; color: {BLANCO}; font-weight: 600; border: 1px solid {TINTA}; }}
QPushButton#primario:hover {{ background: #2A2D35; }}
QPushButton#primario:disabled {{ background: {APAGADO}; border-color: {APAGADO}; }}
QPushButton#secundario {{ background: {BLANCO}; color: {TINTA}; border: 1px solid {BORDE_BOTON}; }}
QPushButton#secundario:hover {{ border-color: {TINTA}; }}
QPushButton#secundario:disabled {{ color: {APAGADO}; border-color: {LINEA}; }}
QPushButton#plano {{ background: transparent; border: none; color: {GRAFITO}; padding: 9px 12px; }}
QPushButton#plano:hover {{ color: {TINTA}; }}
QPushButton#plano:disabled {{ color: {APAGADO}; }}
QPushButton#azul {{ background: {AZUL}; border: 1px solid {AZUL}; padding: 9px 18px; }}
QPushButton#azul:hover {{ background: #1A43B8; }}
#azul_texto {{ color: {BLANCO}; font-weight: 600; font-size: 11pt; }}
#azul_atajo {{ color: #C9D5F7; font-family: "{MONO}"; font-size: 9.5pt; }}
#atajos {{ font-family: "{MONO}"; color: {GRAFITO}; font-size: 9.5pt; }}

#titulo {{ font-size: 16pt; font-weight: 600; }}
QTableWidget {{ background: {BLANCO}; border: 1px solid {LINEA}; gridline-color: {LINEA};
               selection-background-color: {AZUL}; selection-color: {BLANCO}; }}
QHeaderView::section {{ background: {PAPEL}; color: {GRAFITO}; border: none; border-bottom: 1px solid {LINEA};
                        padding: 6px; font-weight: 600; }}
QPlainTextEdit {{ background: {BLANCO}; border: 1px solid {LINEA}; border-radius: 4px; padding: 8px; font-size: 18pt;
                  selection-background-color: {AZUL}; }}
QPlainTextEdit:focus {{ border: 1px solid {AZUL}; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; color: {GRAFITO}; padding: 8px 16px; border-bottom: 3px solid transparent;
               font-size: 10.5pt; }}
QTabBar::tab:selected {{ color: {TINTA}; font-weight: 600; border-bottom: 3px solid {AZUL}; }}
QComboBox {{ background: {BLANCO}; border: 1px solid {BORDE_BOTON}; border-radius: 4px; padding: 6px 10px; min-width: 220px; }}
QComboBox QAbstractItemView {{ background: {BLANCO}; color: {TINTA}; selection-background-color: {AZUL};
                              selection-color: {BLANCO}; }}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {LINEA}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QToolTip {{ background: {TINTA}; color: {BLANCO}; border: none; padding: 4px; }}
"""

_fuentes_cargadas = False


def cargar_fuentes() -> None:
    """Registra IBM Plex Sans y Mono (recursos/fuentes): la app no depende de las fuentes del equipo."""
    global _fuentes_cargadas
    if _fuentes_cargadas:
        return
    for ruta in sorted(config.DIR_FUENTES.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ruta))
    _fuentes_cargadas = True


def fuente(tam: float, peso: QFont.Weight = QFont.Normal, familia: str = SANS) -> QFont:
    f = QFont(familia)
    f.setPointSizeF(tam)
    f.setWeight(peso)
    return f


def _repulir(widget: QWidget, **propiedades) -> None:
    """Cambia propiedades dinámicas y vuelve a aplicar la hoja de estilo."""
    for nombre, valor in propiedades.items():
        widget.setProperty(nombre, valor)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _etiqueta(texto: str = "", nombre: str | None = None) -> QLabel:
    etiqueta = QLabel(texto)
    if nombre:
        etiqueta.setObjectName(nombre)
    return etiqueta


def _boton(texto: str, nombre: str, accion) -> QPushButton:
    boton = QPushButton(texto)
    boton.setObjectName(nombre)
    boton.setCursor(Qt.PointingHandCursor)
    boton.setFocusPolicy(Qt.NoFocus)  # Espacio y Enter no "presionan" el botón enfocado
    boton.clicked.connect(accion)
    return boton


def _separador() -> QFrame:
    linea = QFrame()
    linea.setObjectName("separador")
    return linea


def componer_imagen(r: ResultadoCuadro) -> QImage:
    """Dibuja el esqueleto, espeja (vista tipo espejo) y convierte a QImage. Corre en el hilo de video."""
    cuadro = r.cuadro.copy()
    if r.cuerpo is not None:
        dibujar_cuerpo(cuadro, r.cuerpo)
    elif r.mano is not None:
        dibujar_mano(cuadro, r.mano)
    rgb = cv2.cvtColor(cv2.flip(cuadro, 1), cv2.COLOR_BGR2RGB)
    alto, ancho = rgb.shape[:2]
    return QImage(np.ascontiguousarray(rgb).data, ancho, alto, 3 * ancho, QImage.Format_RGB888).copy()


# ---------------------------------------------------------------------------- hilo de video
class TrabajadorVideo(QThread):
    iniciado = Signal(int)
    fallo = Signal(str)
    cuadro_listo = Signal(object, QImage)

    def __init__(self, ctrl: ControladorSILVA, candado: threading.Lock) -> None:
        super().__init__()
        self.ctrl = ctrl
        self.candado = candado
        self._parar = threading.Event()
        self.interfaz_libre = threading.Event()  # la ventana terminó de pintar el cuadro anterior
        self.interfaz_libre.set()

    def parar(self) -> None:
        self._parar.set()

    def run(self) -> None:
        try:
            with self.candado:
                self.ctrl.iniciar()
        except CamaraNoDisponibleError as error:
            self.fallo.emit(str(error))
            return
        self.iniciado.emit(self.ctrl.sesion_id)
        while not self._parar.is_set():
            with self.candado:
                r = self.ctrl.procesar_cuadro()
            if r is None:
                self.msleep(5)
                continue
            # Si la ventana va atrasada se salta el cuadro, salvo que traiga un evento (letra/palabra)
            hay_evento = r.letra_confirmada is not None or (r.cuerpo is not None and r.prediccion is not None)
            if self.interfaz_libre.is_set() or hay_evento:
                self.interfaz_libre.clear()
                self.cuadro_listo.emit(r, componer_imagen(r))


# --------------------------------------------------------------------------------- widgets
class BarraSegmentos(QWidget):
    """Estado de la detección en 5 segmentos: gris sin mano, ocre leyendo (k de 5 cuadros), azul confirmada."""

    def __init__(self, segmentos: int = 5) -> None:
        super().__init__()
        self.segmentos = segmentos
        self._llenos = 0
        self._color = OCRE
        self.setFixedHeight(6)

    def poner(self, llenos: int, color: str = OCRE) -> None:
        llenos = max(0, min(llenos, self.segmentos))
        if (llenos, color) != (self._llenos, self._color):
            self._llenos, self._color = llenos, color
            self.update()

    def value(self) -> int:  # compatibilidad: avance en % (como la barra anterior)
        return round(100 * self._llenos / self.segmentos)

    def paintEvent(self, _evento) -> None:
        p = QPainter(self)
        espacio = 6
        ancho = (self.width() - espacio * (self.segmentos - 1)) / self.segmentos
        for i in range(self.segmentos):
            p.fillRect(QRectF(i * (ancho + espacio), 0, ancho, self.height()),
                       QColor(self._color if i < self._llenos else LINEA))
        p.end()


class VideoWidget(QWidget):
    """Video sobre fondo tinta, con el recuadro o la silueta guía, el estado y los avisos superpuestos."""

    respuesta_cerrada = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._imagen: QImage | None = None
        self._respuesta: str | None = None
        self._pendiente: tuple[list[str], bool, float] | None = None  # (opciones, escrita, progreso)
        self._pendiente_desde = 0.0  # para la animación de entrada de la tarjeta
        self._guia: str | None = None  # "ok" | "ajustar" | None: silueta de encuadre (modo Palabras)
        self._recuadro = False  # modo Deletreo: recuadro donde va la mano
        self.animacion: AnimacionSena | None = None  # palabras a señas, junto a la respuesta
        self._alfa_respuesta = 1.0
        self._anim_respuesta = QVariantAnimation(self)
        self._anim_respuesta.setDuration(260)
        self._anim_respuesta.setStartValue(0.0)
        self._anim_respuesta.setEndValue(1.0)
        self._anim_respuesta.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_respuesta.valueChanged.connect(self._al_animar_respuesta)
        self._aviso = ""
        self._banda: str | None = None
        self._grabando = False
        self.setMinimumSize(480, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self) -> QSize:
        return QSize(860, 480)

    def poner_imagen(self, imagen: QImage) -> None:
        self._imagen = imagen
        self.update()

    def poner_aviso(self, texto: str) -> None:
        """Quita el video y muestra un mensaje centrado."""
        self._imagen, self._aviso, self._banda, self._grabando = None, texto, None, False
        self._pendiente = None
        self._guia = None
        self.update()

    def poner_banda(self, texto: str | None) -> None:
        if texto != self._banda:
            self._banda = texto
            self.update()

    def poner_recuadro(self, visible: bool) -> None:
        if visible != self._recuadro:
            self._recuadro = visible
            self.update()

    def poner_pendiente(self, opciones: list[str] | None, escrita: bool = True, progreso: float = 0.0) -> None:
        """RF-13: palabra escrita (con sus alternativas) o «¿Quisiste decir?», en grande sobre el video
        para que la vea también quien signa, a distancia."""
        nuevo = None if not opciones else (list(opciones), escrita, round(progreso, 2))
        if nuevo != self._pendiente:
            if self._pendiente is None or (nuevo is not None and nuevo[:2] != self._pendiente[:2]):
                self._pendiente_desde = time.monotonic()  # tarjeta nueva: entra deslizándose
            self._pendiente = nuevo
            self.update()

    def poner_guia(self, estado: str | None) -> None:
        """Silueta de dónde ubicarse: azul ("ok") u ocre ("ajustar"); None la oculta."""
        if estado != self._guia:
            self._guia = estado
            self.update()

    def usar_animaciones(self, animaciones: AnimacionesSenas) -> None:
        self.animacion = AnimacionSena(animaciones, self)
        self.animacion.hide()

    def resizeEvent(self, evento) -> None:
        if self.animacion is not None:
            ancho = int(self.width() * 0.36)
            self.animacion.setGeometry(self.width() - ancho - 24, 24, ancho, self.height() - 48)
        super().resizeEvent(evento)

    def poner_respuesta(self, texto: str | None, senas: list[str] | None = None) -> None:
        """RF-09: muestra en grande, sobre el video, la respuesta escrita por la persona oyente.

        RF-15: si el texto contiene palabras con seña conocida, a la derecha se anima cómo se hacen.
        """
        if self.animacion is not None:
            if texto is not None and senas:
                self.animacion.mostrar(senas)
                self.animacion.show()
                self.animacion.raise_()
            else:
                self.animacion.detener()
                self.animacion.hide()
        aparece = texto is not None and self._respuesta is None
        self._respuesta = texto
        self.setCursor(Qt.PointingHandCursor if texto else Qt.ArrowCursor)
        if aparece:
            self._anim_respuesta.start()  # fundido de entrada
        self.update()

    def _al_animar_respuesta(self, valor) -> None:
        self._alfa_respuesta = float(valor)
        self.update()

    @property
    def mostrando_respuesta(self) -> bool:
        return self._respuesta is not None

    def mousePressEvent(self, evento) -> None:
        if self._respuesta is not None:
            self.poner_respuesta(None)
            self.respuesta_cerrada.emit()
        super().mousePressEvent(evento)

    def poner_grabando(self, grabando: bool) -> None:
        if grabando != self._grabando:
            self._grabando = grabando
            self.update()

    def paintEvent(self, _evento) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        recorte = QPainterPath()
        recorte.addRoundedRect(QRectF(self.rect()), 6, 6)
        p.setClipPath(recorte)
        p.fillRect(self.rect(), QColor(TINTA))

        if self._respuesta is not None:  # la respuesta tapa todo lo demás
            self._pintar_respuesta(p)
            p.end()
            return

        if self._imagen is not None:
            escalada = self._imagen.size().scaled(self.size(), Qt.KeepAspectRatio)
            destino = QRect(QPoint(0, 0), escalada)
            destino.moveCenter(self.rect().center())
            p.drawImage(destino, self._imagen)
            if self._recuadro:
                self._pintar_recuadro(p, destino)
            if self._guia is not None:
                self._pintar_guia(p, destino)
            self._pintar_estado(p)
        else:
            p.setPen(QColor(APAGADO))
            p.setFont(fuente(12))
            p.drawText(self.rect().adjusted(24, 0, -24, 0), Qt.AlignCenter | Qt.TextWordWrap, self._aviso)

        if self._pendiente is not None:
            self._pintar_pendiente(p)
            p.setOpacity(1.0)

        if self._banda:
            p.setFont(fuente(10.5))
            metricas = QFontMetrics(p.font())
            ancho = min(metricas.horizontalAdvance(self._banda) + 40, self.width() - 32)
            alto = metricas.boundingRect(QRect(0, 0, ancho - 40, 200), Qt.TextWordWrap, self._banda).height() + 20
            # con una palabra pendiente abajo, el aviso sube para no taparla
            y = 16 if self._pendiente is not None else self.height() - alto - 16
            banda = QRectF(16, y, ancho, alto)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(22, 24, 29, 225))
            p.drawRoundedRect(banda, 4, 4)
            p.setBrush(QColor(OCRE))
            p.drawRect(QRectF(banda.left(), banda.top(), 3, banda.height()))
            p.setPen(QColor(PAPEL))
            p.drawText(banda.adjusted(18, 0, -14, 0), Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap, self._banda)
        p.end()

    def _pintar_estado(self, p: QPainter) -> None:
        """Una sola indicación arriba a la derecha: «en vivo» o «leyendo seña»."""
        texto, color = ("leyendo seña", OCRE) if self._grabando else ("en vivo", AZUL)
        p.setFont(fuente(10, QFont.Medium))
        ancho = QFontMetrics(p.font()).horizontalAdvance(texto)
        x = self.width() - ancho - 22
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawEllipse(QRectF(x - 14, 22, 8, 8))
        p.setPen(QColor(PAPEL))
        p.drawText(QRect(x, 14, ancho + 4, 24), Qt.AlignVCenter | Qt.AlignLeft, texto)

    def _pintar_recuadro(self, p: QPainter, d: QRect) -> None:
        """Recuadro donde va la mano en el deletreo (como en la propuesta de diseño)."""
        alto = d.height() * 0.8
        ancho = min(alto * 0.88, d.width() * 0.6)
        rect = QRectF(d.center().x() - ancho / 2, d.center().y() - alto / 2, ancho, alto)
        p.setPen(QPen(QColor(255, 255, 255, 110), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRect(rect)

    def _pintar_guia(self, p: QPainter, d: QRect) -> None:
        """Silueta (cabeza, hombros y torso) en la posición en que se grabaron los datos de entrenamiento."""
        ok = self._guia == "ok"
        color = QColor(AZUL if ok else OCRE)
        color.setAlpha(170 if ok else 220)
        lapiz = QPen(color, 2.2, Qt.DashLine)
        p.setPen(lapiz)
        p.setBrush(Qt.NoBrush)
        # proporciones medidas en LSC-54 (ver config.ENCUADRE_*), relativas a la imagen
        ancho_h = d.width() * sum(config.ENCUADRE_HOMBROS) / 2 * 0.95
        cx, y_h, y_n = d.center().x(), d.top() + 0.50 * d.height(), d.top() + 0.31 * d.height()
        radio = ancho_h * 0.32
        p.drawEllipse(QRectF(cx - radio, y_n - radio * 1.15, 2 * radio, 2.3 * radio))
        torso = QPainterPath()
        torso.moveTo(cx - ancho_h / 2 - 10, d.bottom())
        torso.lineTo(cx - ancho_h / 2, y_h)
        torso.quadTo(cx, y_h - radio * 0.6, cx + ancho_h / 2, y_h)
        torso.lineTo(cx + ancho_h / 2 + 10, d.bottom())
        p.drawPath(torso)
        p.setPen(Qt.NoPen)

    def _pintar_pendiente(self, p: QPainter) -> None:
        opciones, escrita, progreso = self._pendiente
        ancho = min(self.width() - 32, 520)
        # Entrada: sube 28 px y aparece en ~0,22 s (el video se repinta a 30 cuadros/s, así que se anima solo)
        t = min((time.monotonic() - self._pendiente_desde) / 0.22, 1.0)
        entrada = 1 - (1 - t) ** 3
        p.setOpacity(0.25 + 0.75 * entrada)
        tarjeta = QRectF((self.width() - ancho) / 2, self.height() - 128 + 28 * (1 - entrada), ancho, 112)
        color = QColor(AZUL if escrita else OCRE)
        p.setPen(QPen(QColor(LINEA), 1))
        p.setBrush(QColor(BLANCO))
        p.drawRoundedRect(tarjeta, 6, 6)
        interior = tarjeta.adjusted(20, 12, -20, -14)
        p.setFont(fuente(9, QFont.DemiBold))
        p.setPen(color)
        p.drawText(interior, Qt.AlignTop | Qt.AlignLeft, "ESCRITA" if escrita else "¿QUISISTE DECIR?")
        p.setPen(QColor(TINTA))
        if escrita:
            p.setFont(fuente(24, QFont.Bold))
            p.drawText(interior.adjusted(0, 12, 0, -20), Qt.AlignCenter, opciones[0].upper())
            pie = "¿No era?  " + "   ".join(f"{i + 2} {o}" for i, o in enumerate(opciones[1:])) + "   ·   X borrar"
        else:
            p.setFont(fuente(16, QFont.Medium))
            p.drawText(interior.adjusted(0, 12, 0, -20), Qt.AlignCenter,
                       "      ".join(f"{i + 1}  {o}" for i, o in enumerate(opciones)))
            pie = "Elige con 1, 2 o 3  ·  X descartar  ·  si nadie elige, no se escribe"
        p.setFont(fuente(9))
        p.setPen(QColor(GRAFITO))
        p.drawText(interior, Qt.AlignBottom | Qt.AlignHCenter, pie)
        # barra del plazo: se llena hasta que termina el tiempo para corregir (o la sugerencia desaparece)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawRect(QRectF(tarjeta.left(), tarjeta.bottom() - 3, ancho * progreso, 3))

    def _pintar_respuesta(self, p: QPainter) -> None:
        p.setOpacity(self._alfa_respuesta)
        p.fillRect(self.rect(), QColor(PAPEL))
        margen = 32
        p.setPen(QColor(AZUL))
        p.setFont(fuente(10, QFont.DemiBold))
        p.drawText(QRect(margen, margen, self.width() - 2 * margen, 24), Qt.AlignLeft, "RESPUESTA")
        con_senas = self.animacion is not None and self.animacion.isVisible()
        ancho_texto = int(self.width() * 0.6) if con_senas else self.width() - 2 * margen
        area = QRect(margen, margen + 36, ancho_texto - (margen if con_senas else 0), self.height() - 2 * margen - 76)
        # Letra tan grande como quepa (entre 18 y 60 pt), para leerla a distancia
        tam = 60
        while tam > 18:
            ocupado = QFontMetrics(fuente(tam, QFont.Medium)).boundingRect(
                area, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter, self._respuesta)
            if ocupado.height() <= area.height() and ocupado.width() <= area.width():
                break
            tam -= 2
        p.setFont(fuente(tam, QFont.Medium))
        p.setPen(QColor(TINTA))
        p.drawText(area, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter, self._respuesta)
        p.setPen(QColor(GRAFITO))
        p.setFont(fuente(10))
        p.drawText(QRect(margen, self.height() - margen - 20, self.width(), 20), Qt.AlignLeft,
                   "Clic sobre el video o Esc para cerrar")


class FlujoLayout(QLayout):
    """Acomoda los elementos en filas que saltan de línea (para las palabras disponibles)."""

    def __init__(self, espacio: int = 6) -> None:
        super().__init__()
        self._items = []
        self._espacio = espacio

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, ancho: int) -> int:
        return self._acomodar(QRect(0, 0, ancho, 0), solo_medir=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._acomodar(rect, solo_medir=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        tam = QSize()
        for item in self._items:
            tam = tam.expandedTo(item.minimumSize())
        return tam

    def _acomodar(self, rect: QRect, solo_medir: bool) -> int:
        x, y, alto_fila = rect.x(), rect.y(), 0
        for item in self._items:
            tam = item.sizeHint()
            if x + tam.width() > rect.right() + 1 and alto_fila > 0:
                x, y, alto_fila = rect.x(), y + alto_fila + self._espacio, 0
            if not solo_medir:
                item.setGeometry(QRect(QPoint(x, y), tam))
            x += tam.width() + self._espacio
            alto_fila = max(alto_fila, tam.height())
        return y + alto_fila - rect.y()


class BotonResponder(QPushButton):
    """«Responder  Ctrl+R»: el atajo en tipografía mono, como en la propuesta de diseño."""

    def __init__(self, accion) -> None:
        super().__init__()
        self.setObjectName("azul")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.clicked.connect(accion)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(20, 0, 20, 0)
        fila.setSpacing(10)
        for texto, nombre in (("Responder", "azul_texto"), ("Ctrl+R", "azul_atajo")):
            etiqueta = _etiqueta(texto, nombre)
            etiqueta.setAttribute(Qt.WA_TransparentForMouseEvents)
            fila.addWidget(etiqueta)
        self.setMinimumSize(190, 42)


# ---------------------------------------------------------------------------- ventana
class VentanaPrincipal(QWidget):
    def __init__(self, controlador: ControladorSILVA) -> None:
        super().__init__()
        cargar_fuentes()
        self.ctrl = controlador
        self._candado = threading.Lock()
        self._trabajador: TrabajadorVideo | None = None
        self._chips: dict[str, QLabel] = {}
        self._chip_activo: str | None = None
        self._dialogo_historial: QDialog | None = None
        self._entrenar: VentanaEntrenar | None = None
        self._confirmada_hasta = 0.0  # mientras tanto la barra queda azul: «confirmada y agregada al texto»
        self._ultima_resolucion = ""
        self._sugerencias = Sugerencias()
        try:
            self._animaciones: AnimacionesSenas | None = AnimacionesSenas()
        except FileNotFoundError:
            self._animaciones = None
        self.mostrar_error = self._mostrar_error  # reemplazable en pruebas

        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("SILVA")
        if config.RUTA_ICONO.exists():
            self.setWindowIcon(QIcon(str(config.RUTA_ICONO)))
        self.setStyleSheet(HOJA_ESTILO)
        self._construir()
        self._ajustes = DialogoAjustes(self)
        self._atajos()
        self._mostrar_inactivo()
        if self.ctrl.palabras_disponibles and self.ctrl.modo != MODO_PALABRAS:
            self.ctrl.cambiar_modo(MODO_PALABRAS)  # Palabras es el modo principal; Deletreo, el complemento
        self._aplicar_modo()
        self.resize(1280, 820)

    @property
    def combo_camara(self) -> QComboBox:
        return self._ajustes.combo_camara

    # --------------------------------------------------------------- construcción
    def _construir(self) -> None:
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._cabecera())

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        izquierda = QVBoxLayout()
        izquierda.setContentsMargins(24, 24, 24, 14)
        izquierda.setSpacing(10)
        self.video = VideoWidget()
        if self._animaciones is not None:
            self.video.usar_animaciones(self._animaciones)
        izquierda.addWidget(self.video, 1)
        fila = QHBoxLayout()
        self.lbl_fps = _etiqueta("", "info_camara")
        fila.addWidget(self.lbl_fps)
        fila.addStretch()
        self.btn_cambiar_camara = _boton("Cambiar cámara", "enlace", self.cambiar_camara)
        self.btn_cambiar_camara.setToolTip("Pasa a la siguiente cámara, por ejemplo el celular como cámara web\n"
                                           "(Enlace Móvil de Windows 11, DroidCam o Iriun). También en Ajustes.")
        fila.addWidget(self.btn_cambiar_camara)
        izquierda.addLayout(fila)
        cuerpo.addLayout(izquierda, 1)
        cuerpo.addWidget(self._panel_lateral())
        raiz.addLayout(cuerpo, 1)

        raiz.addWidget(self._zona_texto())
        raiz.addWidget(self._barra())

    def _cabecera(self) -> QFrame:
        cab = QFrame()
        cab.setObjectName("cabecera")
        fila = QHBoxLayout(cab)
        fila.setContentsMargins(26, 0, 22, 0)
        fila.setSpacing(0)
        if config.RUTA_MARCA.exists():
            marca = QLabel()
            marca.setPixmap(QPixmap(str(config.RUTA_MARCA)).scaledToHeight(26, Qt.SmoothTransformation))
            fila.addWidget(marca)
            fila.addSpacing(12)
        fila.addWidget(_etiqueta("SILVA", "marca_texto"))
        fila.addSpacing(40)
        self.grupo_modo = QButtonGroup(self)
        self.btn_modo: dict[str, QPushButton] = {}
        for modo, texto in ((MODO_PALABRAS, "Palabras"), (MODO_LETRAS, "Deletreo")):  # Palabras primero: el modo principal
            b = _boton(texto, "pestana", lambda _=False, m=modo: self.cambiar_modo(m))
            b.setCheckable(True)
            self.grupo_modo.addButton(b)
            fila.addWidget(b, 0, Qt.AlignBottom)
            self.btn_modo[modo] = b
        if not self.ctrl.palabras_disponibles:
            self.btn_modo[MODO_PALABRAS].setEnabled(False)
            self.btn_modo[MODO_PALABRAS].setToolTip("Falta modelos/modelo_palabras.pkl")
        fila.addStretch()
        fila.addWidget(_boton("Entrenar", "cabecera_enlace", self.ver_entrenar))
        fila.addWidget(_boton("Historial", "cabecera_enlace", self.ver_historial))
        fila.addWidget(_boton("Ajustes", "cabecera_enlace", self.ver_ajustes))
        return cab

    def _panel_lateral(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(370)
        v = QVBoxLayout(panel)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(0)

        self.lbl_titulo_det = _etiqueta("Letra detectada", "seccion")
        v.addWidget(self.lbl_titulo_det)
        fila = QHBoxLayout()
        self.lbl_letra = _etiqueta("–", "letra")
        self.lbl_letra.setMinimumHeight(110)
        self.lbl_letra.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_letra.setWordWrap(True)
        self._opacidad = QGraphicsOpacityEffect(self.lbl_letra)
        self._opacidad.setOpacity(1.0)
        self.lbl_letra.setGraphicsEffect(self._opacidad)
        self._animacion = QPropertyAnimation(self._opacidad, b"opacity", self)
        self._animacion.setDuration(320)
        self._animacion.setStartValue(0.15)
        self._animacion.setEndValue(1.0)
        self._animacion.setEasingCurve(QEasingCurve.OutCubic)
        fila.addWidget(self.lbl_letra, 1)
        columna = QVBoxLayout()
        columna.addStretch()
        self.lbl_conf = _etiqueta("", "porcentaje")
        self.lbl_conf.setAlignment(Qt.AlignRight)
        columna.addWidget(self.lbl_conf)
        self.lbl_conf_txt = _etiqueta("confianza", "tenue")
        self.lbl_conf_txt.setAlignment(Qt.AlignRight)
        columna.addWidget(self.lbl_conf_txt)
        columna.addSpacing(8)
        fila.addLayout(columna)
        v.addLayout(fila)
        v.addSpacing(6)
        self.barra_estable = BarraSegmentos(self.ctrl.buffer.cuadros_estables)
        v.addWidget(self.barra_estable)
        v.addSpacing(10)
        self.lbl_ultima = _etiqueta("", "estado")
        self.lbl_ultima.setWordWrap(True)
        self.lbl_ultima.setMinimumHeight(22)
        v.addWidget(self.lbl_ultima)
        v.addSpacing(20)
        v.addWidget(_separador())
        v.addSpacing(20)

        # Abecedario o vocabulario (QStackedWidget: el panel no cambia de alto al cambiar de modo)
        self.pila = QStackedWidget()
        self.pila.addWidget(self._abecedario())
        self.pila.addWidget(self._vocabulario())
        v.addWidget(self.pila, 1)
        return panel

    def _abecedario(self) -> QWidget:
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        letras = set(self.ctrl.letras)
        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("Abecedario", "seccion"))
        fila.addStretch()
        fila.addWidget(_etiqueta(f"{len(letras)} de {len(config.LETRAS)}", "tenue"))
        v.addLayout(fila)
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(4)
        rejilla.setVerticalSpacing(8)
        con_trazo = set(self.ctrl.clasificador_movimiento.letras) if self.ctrl.clasificador_movimiento else set()
        for i, letra in enumerate(config.LETRAS):
            etiqueta = _etiqueta(letra, "letra_abc")
            etiqueta.setAlignment(Qt.AlignCenter)
            etiqueta.setProperty("apagada", letra not in letras)
            if letra in con_trazo:
                etiqueta.setToolTip(f"La {letra} se hace con movimiento")
            rejilla.addWidget(etiqueta, i // 9, i % 9)
            self._chips[letra] = etiqueta
        v.addLayout(rejilla)
        nota = ("Las letras en gris aún no se reconocen." if len(letras) < len(config.LETRAS) else "")
        if con_trazo:
            nota += (" " if nota else "") + (f"{', '.join(sorted(con_trazo, key=config.LETRAS.index)[:-1])} y "
                                             f"{sorted(con_trazo, key=config.LETRAS.index)[-1]} se trazan: haz el "
                                             "movimiento y quédate quieto al final.")
        if nota:
            etiqueta = _etiqueta(nota, "tenue")
            etiqueta.setWordWrap(True)
            v.addWidget(etiqueta)
        v.addStretch()
        return caja

    def _vocabulario(self) -> QWidget:
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        palabras = sorted(self.ctrl.clasificador_palabras.nombres.values()) if self.ctrl.palabras_disponibles else []
        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("Vocabulario", "seccion"))
        fila.addStretch()
        fila.addWidget(_etiqueta(f"{len(palabras)} palabras", "tenue"))
        v.addLayout(fila)
        flujo_w = QWidget()
        flujo = FlujoLayout(4)
        flujo.setContentsMargins(0, 0, 4, 0)
        flujo_w.setLayout(flujo)
        desplazable = QScrollArea()  # si no caben todas, se desplazan sin agrandar el panel
        desplazable.setWidgetResizable(True)
        desplazable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        desplazable.setWidget(flujo_w)
        desplazable.viewport().setAutoFillBackground(False)
        flujo_w.setAutoFillBackground(False)
        for e in palabras:
            chip = _etiqueta(e, "palabra_voc")
            if self._animaciones is not None and e in self._animaciones.nombres:
                chip.setCursor(Qt.PointingHandCursor)
                chip.setToolTip(f"Ver cómo se hace la seña «{e}»")
                chip.mousePressEvent = lambda _ev, nombre=e: self.ver_sena(nombre)
            flujo.addWidget(chip)
            self._chips[e] = chip
        v.addWidget(desplazable, 1)
        nota = _etiqueta("Empieza con las manos abajo, haz la seña y vuelve a bajarlas. "
                         "Clic en una palabra para ver su seña.", "tenue")
        nota.setWordWrap(True)
        v.addWidget(nota)
        return caja

    def _zona_texto(self) -> QFrame:
        zona = QFrame()
        zona.setObjectName("texto_zona")
        v = QVBoxLayout(zona)
        v.setContentsMargins(26, 16, 26, 14)
        v.setSpacing(4)
        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("Texto", "seccion"))
        fila.addStretch()
        self.btn_voz = _boton("Leer en voz alta", "accion", self.leer_en_voz_alta)
        self.btn_copiar = _boton("Copiar", "accion", self.copiar)
        fila.addWidget(self.btn_voz)
        fila.addSpacing(8)
        fila.addWidget(self.btn_copiar)
        v.addLayout(fila)
        self.lbl_texto = _etiqueta("", "texto")
        self.lbl_texto.setWordWrap(True)
        self.lbl_texto.setTextFormat(Qt.RichText)
        self.lbl_texto.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_texto.setMinimumHeight(62)
        self.lbl_texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.lbl_texto)

        # «¿Quisiste decir?»: palabras para completar (Deletreo) …
        self.fila_sugerencias = QWidget()
        fs = QHBoxLayout(self.fila_sugerencias)
        fs.setContentsMargins(0, 0, 0, 0)
        fs.setSpacing(6)
        fs.addWidget(_etiqueta("¿Quisiste decir?", "estado"))
        self.btn_sugerencias = []
        for _ in range(3):
            b = _boton("", "enlace", lambda: None)
            b.clicked.disconnect()
            b.clicked.connect(lambda _=False, boton=b: self.completar(boton.text()))
            fs.addWidget(b)
            self.btn_sugerencias.append(b)
        fs.addStretch()
        v.addWidget(self.fila_sugerencias)

        # … o, en Palabras, las opciones de la palabra reconocida (RF-13)
        self.panel_pendiente = QWidget()
        fp = QHBoxLayout(self.panel_pendiente)
        fp.setContentsMargins(0, 0, 0, 0)
        fp.setSpacing(6)
        self.lbl_pendiente = _etiqueta("", "estado")
        fp.addWidget(self.lbl_pendiente)
        self.btn_opciones = []
        for i in range(3):
            b = _boton("", "enlace", lambda _=False, k=i: self.elegir(k))
            fp.addWidget(b)
            self.btn_opciones.append(b)
        fp.addSpacing(10)
        self.btn_confirmar = _boton("Era correcta", "enlace_gris", lambda: self.elegir(0))
        self.btn_descartar = _boton("Descartar", "enlace_gris", self.descartar)
        fp.addWidget(self.btn_confirmar)
        fp.addWidget(self.btn_descartar)
        fp.addStretch()
        self.panel_pendiente.hide()
        v.addWidget(self.panel_pendiente)
        alto = max(self.fila_sugerencias.sizeHint().height(), self.panel_pendiente.sizeHint().height())
        for w in (self.fila_sugerencias, self.panel_pendiente):
            w.setFixedHeight(alto)
        return zona

    def _barra(self) -> QFrame:
        barra = QFrame()
        barra.setObjectName("barra")
        fila = QHBoxLayout(barra)
        fila.setContentsMargins(24, 12, 24, 12)
        fila.setSpacing(8)
        self.btn_principal = _boton("", "primario", self.alternar)
        self.btn_principal.setMinimumWidth(110)
        fila.addWidget(self.btn_principal)
        self.btn_espacio = _boton("Espacio", "secundario", self.espacio)
        self.btn_borrar = _boton("Borrar letra", "secundario", self.borrar)
        self.btn_limpiar = _boton("Limpiar", "plano", self.limpiar)
        for b in (self.btn_espacio, self.btn_borrar, self.btn_limpiar):
            fila.addWidget(b)
        fila.addSpacing(16)
        self.lbl_atajos = _etiqueta("", "atajos")
        fila.addWidget(self.lbl_atajos)
        fila.addStretch()
        self.btn_responder = BotonResponder(self.responder)
        self.btn_responder.setToolTip("La persona oyente escribe su respuesta y se muestra en grande")
        fila.addWidget(self.btn_responder)
        return barra

    def _atajos(self) -> None:
        for tecla, accion in ((Qt.Key_Return, self.alternar), (Qt.Key_Enter, self.alternar),
                              (Qt.Key_Space, self.espacio), (Qt.Key_Backspace, self.borrar),
                              (Qt.Key_Delete, self.limpiar)):
            QShortcut(QKeySequence(tecla), self, activated=accion)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.responder)
        for i, tecla in enumerate((Qt.Key_1, Qt.Key_2, Qt.Key_3)):
            QShortcut(QKeySequence(tecla), self, activated=lambda k=i: self.elegir(k))
        QShortcut(QKeySequence(Qt.Key_X), self, activated=self.descartar)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=lambda: self.video.poner_respuesta(None))

    # -------------------------------------------------------------------- acciones
    @property
    def activo(self) -> bool:
        return self._trabajador is not None

    def alternar(self) -> None:
        if not self.btn_principal.isEnabled():
            return
        self.detener() if self.activo else self.iniciar()

    def iniciar(self) -> None:
        if self.activo:
            return
        self.video.poner_aviso("Encendiendo la cámara…")
        self.btn_principal.setEnabled(False)
        self._trabajador = TrabajadorVideo(self.ctrl, self._candado)
        self._trabajador.iniciado.connect(self._al_iniciar)
        self._trabajador.fallo.connect(self._al_fallar)
        self._trabajador.cuadro_listo.connect(self._pintar)
        self._trabajador.start()

    def _al_iniciar(self, _sesion_id: int) -> None:
        self.btn_principal.setEnabled(True)
        self.btn_principal.setText("Detener")
        self._ajustes.combo_camara.setEnabled(False)
        self.lbl_ultima.setText("")
        self._actualizar_texto()

    def _al_fallar(self, _mensaje: str) -> None:
        self._trabajador.wait()
        self._trabajador = None
        self.btn_principal.setEnabled(True)
        self._mostrar_inactivo()
        self.mostrar_error(
            "Cámara no disponible",
            "No se pudo abrir la cámara web.\n\nVerifica que esté conectada y que ninguna otra "
            "aplicación (Zoom, Teams, la app Cámara…) la esté usando.",
        )

    def detener(self) -> None:
        if not self.activo:
            return
        self._parar_trabajador()
        with self._candado:
            self.ctrl.detener()  # guarda la sesión y después libera la cámara (Figura 5)
        self._mostrar_inactivo()
        if self.ctrl.sesion_id is not None:  # al grabar muestras no hay sesión
            self.lbl_ultima.setText(f"Sesión #{self.ctrl.sesion_id} guardada en el historial")

    def _parar_trabajador(self) -> None:
        trabajador, self._trabajador = self._trabajador, None
        if trabajador is not None:
            trabajador.cuadro_listo.disconnect(self._pintar)
            trabajador.parar()
            trabajador.wait(3000)

    def cambiar_modo(self, modo: str) -> None:
        if modo == MODO_PALABRAS and not self.ctrl.palabras_disponibles:
            return
        if modo != self.ctrl.modo:
            with self._candado:
                self.ctrl.cambiar_modo(modo)
        self._aplicar_modo()

    def _aplicar_modo(self) -> None:
        palabras = self.ctrl.modo == MODO_PALABRAS
        self.btn_modo[self.ctrl.modo].setChecked(True)
        self.lbl_titulo_det.setText("Palabra detectada" if palabras else "Letra detectada")
        if self.pila.currentIndex() != (1 if palabras else 0):
            self.pila.setCurrentIndex(1 if palabras else 0)
            self._fundir(self.pila)
        self.btn_espacio.setVisible(not palabras)
        self.btn_borrar.setText("Borrar palabra" if palabras else "Borrar letra")
        self.lbl_atajos.setText("Enter iniciar/detener · 1 2 3 corregir · X borrar · Supr limpiar" if palabras else
                                "Enter iniciar/detener · Espacio · Retroceso · Supr limpiar")
        self.video.poner_recuadro(False)
        self._poner_letra("–", dudosa=True)
        self.lbl_ultima.setText("")
        self._poner_confianza(None)
        self._resaltar(None)
        self.barra_estable.poner(0)
        self.video.poner_grabando(False)
        self._mostrar_pendiente(None, 0.0)
        self._actualizar_texto()
        if self._entrenar is not None:
            self._entrenar.refrescar()

    def _fundir(self, widget: QWidget, ms: int = 280) -> None:
        """Animación de entrada: el widget aparece con un fundido."""
        efecto = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(efecto)
        anim = QPropertyAnimation(efecto, b"opacity", widget)
        anim.setDuration(ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))  # sin efecto permanente (más liviano)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _cambiar_camara(self, indice: int) -> None:
        if not self.activo:
            self.ctrl.captura.indice = indice
            self._mostrar_info_camara()

    def cambiar_camara(self) -> None:
        """Pasa a la siguiente cámara (1 → 2 → 3 → 4 → 1); si está encendida, la reinicia con la nueva."""
        estaba = self.activo
        if estaba:
            self.detener()
        combo = self._ajustes.combo_camara
        combo.setCurrentIndex((combo.currentIndex() + 1) % combo.count())
        if estaba:
            self.iniciar()

    def espacio(self) -> None:
        if self.ctrl.modo == MODO_PALABRAS:  # en Palabras, Espacio da por buena la palabra
            self.elegir(0)
            return
        with self._candado:
            self.ctrl.buffer.agregar_espacio()
        self._actualizar_texto()

    def completar(self, palabra: str) -> None:
        """«¿Quisiste decir?»: completa la palabra que se está deletreando."""
        if not palabra:
            return
        with self._candado:
            self.ctrl.buffer.completar(palabra)
        self._actualizar_texto()

    def elegir(self, opcion: int) -> None:
        """RF-13: elige una opción de la palabra pendiente (0 = la más probable)."""
        with self._candado:
            pendiente = self.ctrl.pendiente
            escrita = self.ctrl.confirmar_pendiente(opcion)
        if escrita is not None:
            self._mostrar_pendiente(None, 0.0)
            self._confirmar(escrita, pendiente.opciones[opcion].confianza)

    def descartar(self) -> None:
        with self._candado:
            self.ctrl.descartar_pendiente()
        self._mostrar_pendiente(None, 0.0)
        self._actualizar_texto()

    def borrar(self) -> None:
        with self._candado:
            self.ctrl.buffer.borrar_ultima()
        self._actualizar_texto()

    def limpiar(self) -> None:
        with self._candado:
            self.ctrl.buffer.limpiar()
        self._actualizar_texto()

    def copiar(self) -> None:
        with self._candado:
            texto = self.ctrl.buffer.texto.strip()
        if texto:
            QGuiApplication.clipboard().setText(texto)
            self.lbl_ultima.setText("Texto copiado")

    def leer_en_voz_alta(self) -> None:
        """Lee el texto con la voz de Windows (sin internet), en un hilo para no congelar la ventana."""
        with self._candado:
            texto = self.ctrl.buffer.texto.strip().lower()
        if not texto or sys.platform != "win32":
            return
        guion = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                 "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es*' } | "
                 "Select-Object -First 1; if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
                 "$s.Speak([Console]::In.ReadToEnd())")

        def hablar() -> None:
            try:  # el texto va por la entrada estándar, nunca dentro del comando
                subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", guion], input=texto,
                               text=True, encoding="utf-8", timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            except (OSError, subprocess.SubprocessError):
                pass

        threading.Thread(target=hablar, daemon=True).start()

    def closeEvent(self, evento) -> None:
        self._parar_trabajador()
        with self._candado:
            self.ctrl.cerrar()
        for dialogo in (self._dialogo_historial, self._ajustes, self._entrenar):
            if dialogo is not None:
                dialogo.close()
        evento.accept()

    # ------------------------------------------------------------- cuadros de video
    def _pintar(self, r: ResultadoCuadro, imagen: QImage) -> None:
        try:
            if not self.activo:
                return
            self.video.poner_imagen(imagen)
            alto, ancho = r.cuadro.shape[:2]
            self._ultima_resolucion = f"{ancho}×{alto}"
            self._mostrar_info_camara(r.fps)
            if r.cuerpo is not None:
                self._pintar_palabras(r)
            else:
                self._pintar_letras(r)
            if self._entrenar is not None and self._entrenar.isVisible():
                self._entrenar.cuadro(r)
        finally:
            if self._trabajador is not None:
                self._trabajador.interfaz_libre.set()

    def _pintar_letras(self, r: ResultadoCuadro) -> None:
        self.video.poner_grabando(r.trazando)
        self.video.poner_guia(None)
        self.video.poner_recuadro(True)
        estables = self.ctrl.buffer.cuadros_estables
        if r.letra_confirmada is not None:  # RF-08
            self._confirmar(r.letra_confirmada, r.prediccion.confianza)
            return
        confirmando = time.monotonic() < self._confirmada_hasta
        if r.trazando:  # la letra se decide al terminar el trazo
            self.video.poner_banda(None)
            self._poner_letra("…", dudosa=True)
            self._poner_confianza(None)
            self._resaltar(None)
            self.barra_estable.poner(int(time.monotonic() * 6) % (estables + 1))
            self.lbl_ultima.setText("Leyendo el trazo de la letra…")
        elif r.prediccion is None:
            # RF-06; con poca luz se dice la causa probable
            self.video.poner_banda(AVISO_POCA_LUZ if r.brillo < config.BRILLO_MINIMO else AVISO_SIN_MANO)
            if not confirmando:
                self._poner_letra("–", dudosa=True)
                self._poner_confianza(None)
                self._resaltar(None)
                self.barra_estable.poner(0)
                self.lbl_ultima.setText("Sin mano en el recuadro")
        else:
            self.video.poner_banda(None)
            p = r.prediccion
            aceptable = p.confianza >= self.ctrl.buffer.umbral
            if confirmando and r.progreso == 0:
                return  # se deja ver un momento «confirmada y agregada al texto»
            self._poner_letra(p.letra, dudosa=not aceptable)
            self._poner_confianza(p.confianza)
            self._resaltar(p.letra if aceptable else None)
            k = round(r.progreso * estables)
            self.barra_estable.poner(k)
            self.lbl_ultima.setText(f"Leyendo seña · {k} de {estables} cuadros" if aceptable else
                                    "Seña poco clara: sostén la mano quieta")

    def _pintar_palabras(self, r: ResultadoCuadro) -> None:
        self.video.poner_grabando(r.grabando_sena)
        self.video.poner_recuadro(False)
        if r.letra_confirmada is not None:  # escrita apenas se reconoce
            self._confirmar(r.letra_confirmada, self.ctrl.ultima_confianza or 0.0)
        self._mostrar_pendiente(r.pendiente, r.ahora)
        if r.grabando_sena:
            self.barra_estable.poner(max(1, math.ceil(r.progreso * 120 / 9)))
            self.lbl_ultima.setText("Leyendo seña…")
        elif r.pendiente is None and time.monotonic() >= self._confirmada_hasta:
            self.barra_estable.poner(0)
            self.lbl_ultima.setText("Manos abajo · haz la seña y vuelve a bajarlas")
        encuadre = evaluar_encuadre(r.cuerpo)
        # La silueta guía solo en reposo (sin seña ni palabra pendiente), para no tapar la seña
        en_reposo = not r.grabando_sena and r.pendiente is None
        self.video.poner_guia(("ajustar" if (encuadre or r.cuerpo.pose is None) else "ok") if en_reposo else None)
        if r.brillo < config.BRILLO_MINIMO:
            self.video.poner_banda(AVISO_POCA_LUZ)
        elif r.cuerpo.pose is None:
            self.video.poner_banda(AVISO_SIN_PERSONA)
        elif encuadre and en_reposo:
            self.video.poner_banda(f"{encuadre} (ubícate dentro de la silueta).")
        elif _mano_en_borde(r.cuerpo):
            self.video.poner_banda(AVISO_BORDE)
        else:
            self.video.poner_banda(None)

    def _mostrar_pendiente(self, pendiente: PalabraPendiente | None, ahora: float) -> None:
        if pendiente is None:
            self.panel_pendiente.hide()
            self.video.poner_pendiente(None)
            self._actualizar_sugerencias()
            return
        self.fila_sugerencias.hide()
        opciones = [o.letra for o in pendiente.opciones]
        self.video.poner_pendiente(opciones, pendiente.automatica, pendiente.progreso(ahora))
        mejor = pendiente.opciones[0]
        self._poner_letra(mejor.letra, dudosa=not pendiente.automatica)
        self._poner_confianza(mejor.confianza)
        if pendiente.automatica:
            self.lbl_pendiente.setText("¿No era?")
            self.barra_estable.poner(self.barra_estable.segmentos, AZUL)
            self.lbl_ultima.setText("Palabra escrita · si no era, elige otra abajo")
        else:
            self.lbl_pendiente.setText("¿Quisiste decir?")
            self.barra_estable.poner(2)
            self.lbl_ultima.setText("Seña dudosa · elige una opción abajo")
        inicio = 1 if pendiente.automatica else 0  # si ya se escribió, se ofrecen las otras
        for i, b in enumerate(self.btn_opciones):
            if inicio <= i < len(pendiente.opciones):
                b.setText(f"{pendiente.opciones[i].letra.upper()}")
                b.setToolTip(f"Tecla {i + 1} · {pendiente.opciones[i].confianza:.0%}")
                b.show()
            else:
                b.hide()
        self.btn_confirmar.setVisible(pendiente.automatica)
        self.btn_descartar.setText("Borrar" if pendiente.automatica else "Descartar")
        self.panel_pendiente.show()

    def _confirmar(self, texto: str, confianza: float) -> None:
        palabras = self.ctrl.modo == MODO_PALABRAS
        self._poner_letra(texto, dudosa=False)
        self._poner_confianza(confianza)
        self._resaltar(texto)
        self.barra_estable.poner(self.barra_estable.segmentos, AZUL)
        self.lbl_ultima.setText(f"Palabra «{texto}» escrita" if palabras else
                                f"Letra {texto} confirmada y agregada al texto")
        self._confirmada_hasta = time.monotonic() + 0.8
        self._actualizar_texto()
        self._animacion.stop()
        self._animacion.start()

    # ------------------------------------------------------------------ utilidades
    def _poner_letra(self, texto: str, dudosa: bool) -> None:
        tam = "palabra" if self.ctrl.modo == MODO_PALABRAS and texto not in ("–", "…") else "letra"
        self.lbl_letra.setText(texto)
        if self.lbl_letra.property("dudosa") != dudosa or self.lbl_letra.property("tam") != tam:
            _repulir(self.lbl_letra, dudosa=dudosa, tam=tam)

    def _poner_confianza(self, confianza: float | None) -> None:
        self.lbl_conf.setText("" if confianza is None else f"{confianza:.0%}")
        self.lbl_conf_txt.setVisible(confianza is not None)

    def _resaltar(self, clave: str | None) -> None:
        if clave == self._chip_activo:
            return
        if self._chip_activo in self._chips:
            _repulir(self._chips[self._chip_activo], activo=False)
        if clave in self._chips:
            _repulir(self._chips[clave], activo=True)
        self._chip_activo = clave

    def _mostrar_info_camara(self, fps: float | None = None) -> None:
        i = getattr(self.ctrl.captura, "indice", 0)
        nombre = "Cámara integrada" if i == 0 else f"Cámara {i + 1}"
        if self.activo and fps is not None:
            self.lbl_fps.setText(f"{nombre} · {self._ultima_resolucion} · {fps:.0f} fps")
        else:
            self.lbl_fps.setText(f"{nombre} · apagada")

    def _actualizar_texto(self) -> None:
        with self._candado:
            texto = self.ctrl.buffer.texto
        if texto:
            cursor = f'<span style="color:{AZUL}; font-weight:400">|</span>' if self.activo else ""
            self.lbl_texto.setText(_html(texto) + cursor)
        else:
            unidad = "palabras" if self.ctrl.modo == MODO_PALABRAS else "letras"
            self.lbl_texto.setText(f"Las {unidad} confirmadas aparecerán aquí.")
        if self.lbl_texto.property("vacio") != (not texto):
            _repulir(self.lbl_texto, vacio=not texto)
        self.btn_borrar.setEnabled(bool(texto))
        self.btn_limpiar.setEnabled(bool(texto))
        self.btn_copiar.setEnabled(bool(texto.strip()))
        self.btn_voz.setEnabled(bool(texto.strip()) and sys.platform == "win32")
        self._actualizar_sugerencias()

    def _actualizar_sugerencias(self) -> None:
        if self.ctrl.modo != MODO_LETRAS or self.panel_pendiente.isVisible():
            self.fila_sugerencias.hide()
            return
        with self._candado:
            en_curso = self.ctrl.buffer.palabra_en_curso
        opciones = self._sugerencias.para(en_curso)
        for b, o in zip(self.btn_sugerencias, opciones + [""] * 3):
            b.setText(o)
            b.setVisible(bool(o))
        self.fila_sugerencias.setVisible(bool(opciones))

    def _mostrar_inactivo(self) -> None:
        self.btn_principal.setText("Iniciar")
        self.video.poner_aviso("Presiona «Iniciar» para encender la cámara")
        self._ajustes.combo_camara.setEnabled(True) if hasattr(self, "_ajustes") else None
        self._mostrar_pendiente(None, 0.0)
        self._mostrar_info_camara()
        self._poner_letra("–", dudosa=True)
        self._poner_confianza(None)
        self._resaltar(None)
        self.barra_estable.poner(0)
        self._actualizar_texto()

    def _mostrar_error(self, titulo: str, mensaje: str) -> None:
        QMessageBox.critical(self, titulo, mensaje)

    def ver_entrenar(self) -> None:
        if self._entrenar is None:
            self._entrenar = VentanaEntrenar(self)
        self._entrenar.show()
        self._entrenar.raise_()

    def ver_ajustes(self) -> None:
        self._ajustes.show()
        self._ajustes.raise_()

    def poner_texto_grande(self, grande: bool) -> None:
        _repulir(self.lbl_texto, grande=grande)

    def ver_historial(self) -> None:
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Historial")
        dialogo.setStyleSheet(HOJA_ESTILO)
        dialogo.resize(820, 480)
        v = QVBoxLayout(dialogo)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(_etiqueta("Historial", "titulo"))
        with self._candado:
            sesiones = self.ctrl.historial.listar_sesiones()
            respuestas = self.ctrl.historial.listar_respuestas()
        pestanas = QTabWidget()
        pestanas.addTab(self._tabla("tabla_sesiones", ["#", "Inicio", "Texto traducido"],
                                    [(str(s.id), s.inicio.replace("T", "  "), s.texto or "(vacía)") for s in sesiones]),
                        f"Sesiones ({len(sesiones)})")
        pestanas.addTab(self._tabla("tabla_respuestas", ["Momento", "Sesión", "Respuesta de la persona oyente"],
                                    [(m.replace("T", "  "), "—" if sid is None else f"#{sid}", t)
                                     for m, t, sid in respuestas]),
                        f"Respuestas ({len(respuestas)})")
        v.addWidget(pestanas)
        self._dialogo_historial = dialogo
        dialogo.show()

    @staticmethod
    def _tabla(nombre: str, columnas: list[str], filas: list[tuple[str, ...]]) -> QTableWidget:
        tabla = QTableWidget(len(filas), len(columnas))
        tabla.setObjectName(nombre)
        tabla.setHorizontalHeaderLabels(columnas)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.setShowGrid(False)
        cab = tabla.horizontalHeader()
        for i in range(len(columnas) - 1):
            cab.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        cab.setSectionResizeMode(len(columnas) - 1, QHeaderView.Stretch)
        for f, fila in enumerate(filas):
            for c, valor in enumerate(fila):
                tabla.setItem(f, c, QTableWidgetItem(valor))
        return tabla

    def ver_sena(self, nombre: str) -> None:
        """RF-15: muestra en una ventana la animación de la seña de una palabra (para aprenderla o mostrarla)."""
        dialogo = QDialog(self)
        dialogo.setWindowTitle(f"Seña: {nombre}")
        dialogo.setStyleSheet(HOJA_ESTILO)
        dialogo.resize(380, 470)
        v = QVBoxLayout(dialogo)
        v.setContentsMargins(16, 16, 16, 16)
        animacion = AnimacionSena(self._animaciones, dialogo)
        animacion.mostrar([nombre])
        v.addWidget(animacion)
        nota = _etiqueta("Vista de frente, como la verías frente a ti. Grabación de LSC-54 (Mora-Zarate, 2025).",
                         "tenue")
        nota.setWordWrap(True)
        v.addWidget(nota)
        self._dialogo_sena = dialogo
        dialogo.show()

    def responder(self) -> None:
        """RF-09: la persona oyente escribe y la respuesta se muestra en grande sobre el video."""
        dialogo = DialogoRespuesta(self, self._animaciones)
        self._dialogo_respuesta = dialogo
        dialogo.respuesta_lista.connect(self.mostrar_respuesta)
        dialogo.show()

    def mostrar_respuesta(self, texto: str) -> None:
        with self._candado:
            self.ctrl.historial.registrar_respuesta(self.ctrl.sesion_id if self.activo else None, texto)
        senas = self._animaciones.buscar(texto) if self._animaciones is not None else []
        self.video.poner_respuesta(texto, senas)


class DialogoAjustes(QDialog):
    """Ajustes: cámara (el celular puede servir de cámara web) y tamaño del texto."""

    def __init__(self, ventana: VentanaPrincipal) -> None:
        super().__init__(ventana)
        self.setWindowTitle("Ajustes")
        self.setStyleSheet(HOJA_ESTILO)
        self.resize(460, 260)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)
        v.addWidget(_etiqueta("Ajustes", "titulo"))
        v.addSpacing(6)
        v.addWidget(_etiqueta("Cámara", "seccion"))
        self.combo_camara = QComboBox()
        self.combo_camara.setFocusPolicy(Qt.NoFocus)
        self.combo_camara.addItems(["Cámara integrada", "Cámara 2", "Cámara 3", "Cámara 4"])
        self.combo_camara.setCurrentIndex(getattr(ventana.ctrl.captura, "indice", 0))
        self.combo_camara.currentIndexChanged.connect(ventana._cambiar_camara)
        v.addWidget(self.combo_camara)
        nota = _etiqueta("El celular también sirve de cámara web (Enlace Móvil de Windows 11, DroidCam o Iriun): "
                         "se puede ubicar más lejos y apuntar mejor. Cambia la cámara con la cámara apagada.", "tenue")
        nota.setWordWrap(True)
        v.addWidget(nota)
        v.addSpacing(6)
        v.addWidget(_etiqueta("Tamaño del texto", "seccion"))
        self.combo_tamano = QComboBox()
        self.combo_tamano.addItems(["Normal", "Grande (para leer a distancia)"])
        self.combo_tamano.currentIndexChanged.connect(lambda i: ventana.poner_texto_grande(i == 1))
        v.addWidget(self.combo_tamano)
        v.addStretch()


class TrabajadorEntrenamiento(QThread):
    """Reentrena los modelos en un hilo aparte (scripts/entrenar_con_muestras.py --rapido), dentro de la misma app:
    así funciona igual desde el código que desde el ejecutable, que no tiene un Python aparte."""

    texto = Signal(str)
    terminado = Signal(bool, str)

    class _Escritor:
        def __init__(self, emitir) -> None:
            self._emitir = emitir

        def write(self, t: str) -> int:
            if t:
                self._emitir(t)
            return len(t)

        def flush(self) -> None:
            pass

    def run(self) -> None:
        escritor = self._Escritor(self.texto.emit)
        try:
            carpeta = str((config.DIR_RECURSOS if config.EMPAQUETADO else config.RAIZ_PROYECTO) / "scripts")
            if carpeta not in sys.path:
                sys.path.insert(0, carpeta)
            with contextlib.redirect_stdout(escritor), contextlib.redirect_stderr(escritor):
                importlib.import_module("entrenar_con_muestras").main(["--rapido"])
            self.terminado.emit(True, "")
        except SystemExit as e:  # p. ej. «No hay muestras»
            self.terminado.emit(e.code in (0, None), str(e))
        except Exception as e:  # noqa: BLE001 (se muestra al usuario)
            self.texto.emit(traceback.format_exc())
            self.terminado.emit(False, str(e))


CUADROS_TOMA_LETRA = 30  # letra quieta: cuadros por muestra…
SEGUNDOS_PREPARAR_LETRA = 0.6  # …tras dejar este tiempo para formar la seña


class VentanaEntrenar(QDialog):
    """Entrenar: grabar muestras propias con la cámara y reentrenar los modelos (scripts/entrenar_con_muestras.py).

    Mientras está abierta, el controlador reconoce pero no escribe (ctrl.entrenando) y cada seña o trazo terminado
    llega a `cuadro`. Solo se guardan los puntos del cuerpo y las manos, nunca la imagen. Las muestras quedan en el
    mismo formato que las de la app del teléfono, así que el mismo script entrena con todas juntas.
    """

    def __init__(self, ventana: VentanaPrincipal) -> None:
        super().__init__(ventana)
        self.ventana = ventana
        self.ctrl = ventana.ctrl
        self.setWindowTitle("Entrenar")
        self.setStyleSheet(HOJA_ESTILO)
        self.resize(480, 760)
        self.grabador = GrabadorMuestras()
        self.grabando = False
        self._clave: str | None = None
        self._entrenamiento: TrabajadorEntrenamiento | None = None
        self._preferencias = QSettings("SILVA", "SILVA")
        self._reiniciar_toma()

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(8)
        v.addWidget(_etiqueta("Entrenar con sus señas", "titulo"))
        nota = _etiqueta("Graben cada seña unas 5 veces por persona, con la cámara y en el lugar donde van a usar "
                         "SILVA. Solo se guardan los puntos del cuerpo y las manos, nunca la imagen.", "tenue")
        nota.setWordWrap(True)
        v.addWidget(nota)
        v.addWidget(_etiqueta("¿Quién graba?", "seccion"))
        self.persona = QLineEdit(str(self._preferencias.value("persona", "")))
        self.persona.setPlaceholderText("Nombre o apodo (sirve para medir con personas nuevas)")
        self.persona.textChanged.connect(lambda t: self._preferencias.setValue("persona", t.strip()))
        v.addWidget(self.persona)
        self.lbl_modo = _etiqueta("", "seccion")
        v.addWidget(self.lbl_modo)
        self.lista = QListWidget()
        self.lista.currentItemChanged.connect(self._elegir)
        v.addWidget(self.lista, 1)
        self.aviso = _etiqueta("", "tenue")
        self.aviso.setWordWrap(True)
        self.aviso.setMinimumHeight(44)
        v.addWidget(self.aviso)
        self.barra = QProgressBar()
        self.barra.setRange(0, CUADROS_TOMA_LETRA)
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(6)
        self.barra.hide()
        v.addWidget(self.barra)
        fila = QHBoxLayout()
        self.btn_grabar = _boton("Grabar", "primario", self.alternar_grabacion)
        self.btn_borrar = _boton("Borrar última", "secundario", self.borrar_ultima)
        fila.addWidget(self.btn_grabar, 1)
        fila.addWidget(self.btn_borrar, 1)
        v.addLayout(fila)
        self.lbl_total = _etiqueta("", "tenue")
        v.addWidget(self.lbl_total)
        v.addWidget(_separador())
        v.addWidget(_etiqueta("Reentrenar los modelos", "seccion"))
        nota2 = _etiqueta("Con todas las muestras grabadas (también las que lleguen del teléfono) reentrena los tres "
                          "modelos y mide si los reconoce mejor. Tarda unos minutos; no cierres SILVA mientras tanto.",
                          "tenue")
        nota2.setWordWrap(True)
        v.addWidget(nota2)
        fila2 = QHBoxLayout()
        self.btn_entrenar = _boton("Entrenar los modelos ahora", "secundario", self.entrenar_modelos)
        fila2.addWidget(self.btn_entrenar, 1)
        fila2.addWidget(_boton("Abrir la carpeta", "plano", self.abrir_carpeta))
        v.addLayout(fila2)
        self.btn_originales = _boton("Volver a los modelos originales", "enlace_gris", self.volver_a_los_originales)
        v.addWidget(self.btn_originales, 0, Qt.AlignLeft)
        self.registro = QPlainTextEdit()
        self.registro.setReadOnly(True)
        self.registro.setStyleSheet("font-family: 'IBM Plex Mono', Consolas; font-size: 9pt;")
        self.registro.hide()
        v.addWidget(self.registro, 1)
        self.refrescar()
        self._actualizar_modelos_propios()

    # ------------------------------------------------------------- qué se graba
    def _palabras(self) -> bool:
        return self.ctrl.modo == MODO_PALABRAS

    def _tipo(self, clave: str) -> str:
        if self._palabras():
            return "palabra"
        return "letra" if clave in config.LETRAS_ESTATICAS else "trazo"

    def _nombre(self, clave: str) -> str:
        return self.ctrl.clasificador_palabras.nombres.get(clave, clave) if self._palabras() else clave

    def _texto_item(self, clave: str) -> str:
        n = self.grabador.cuantas(self._tipo(clave), clave)
        trazo = "  ↝ (se traza)" if self._tipo(clave) == "trazo" else ""
        return f"{self._nombre(clave)}{trazo}" + (f"   ·   {n} muestras" if n else "")

    def refrescar(self) -> None:
        """Lista de palabras o letras según el modo de la ventana principal."""
        self.detener_grabacion()
        palabras = self._palabras()
        self.lbl_modo.setText("Palabras (cambia a Deletreo arriba, en la ventana principal)" if palabras
                              else "Letras (cambia a Palabras arriba, en la ventana principal)")
        if palabras:
            clasif = self.ctrl.clasificador_palabras
            claves = sorted(clasif.palabras, key=lambda k: clasif.nombres.get(k, k)) if clasif else []
        else:
            claves = list(config.LETRAS)
        self.lista.blockSignals(True)
        self.lista.clear()
        for clave in claves:
            item = QListWidgetItem(self._texto_item(clave))
            item.setData(Qt.UserRole, clave)
            self.lista.addItem(item)
        self.lista.blockSignals(False)
        self._clave = None
        self.aviso.setText("Elige una palabra para grabarla." if palabras else "Elige una letra para grabarla.")
        self._actualizar_total()

    def _elegir(self, item: QListWidgetItem | None, _anterior=None) -> None:
        self.detener_grabacion()
        self._clave = item.data(Qt.UserRole) if item else None
        if self._clave is None:
            return
        nombre = self._nombre(self._clave)
        self.aviso.setText({
            "palabra": f"Toca «Grabar» y haz «{nombre}» varias veces, bajando las manos entre una y otra.",
            "trazo": f"Toca «Grabar» y traza la {nombre} varias veces; quédate quieto al terminar cada una.",
            "letra": f"Toca «Grabar» y sostén la {nombre} quieta hasta que se llene la barra.",
        }[self._tipo(self._clave)])

    def _actualizar_total(self) -> None:
        self.lbl_total.setText(f"{self.grabador.total} muestras en {self.grabador.carpeta}")
        self.btn_borrar.setEnabled(not self.grabando)
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            item.setText(self._texto_item(item.data(Qt.UserRole)))

    # ------------------------------------------------------------- grabar
    def alternar_grabacion(self) -> None:
        if self.grabando:
            self.detener_grabacion()
            return
        if self._clave is None:
            self.aviso.setText("Elige primero qué vas a grabar.")
            return
        if not self.persona.text().strip():
            self.aviso.setText("Escribe quién graba (tu nombre o un apodo): sirve para medir si el modelo funciona "
                               "con personas nuevas.")
            self.persona.setFocus()
            return
        self.grabando = True
        self._reiniciar_toma()
        self.btn_grabar.setText("Detener")
        self.btn_borrar.setEnabled(False)
        nombre = self._nombre(self._clave)
        tipo = self._tipo(self._clave)
        self.barra.setVisible(tipo == "letra")
        self.aviso.setText({
            "palabra": f"Grabando: haz «{nombre}» y baja las manos. Repite las veces que quieras.",
            "trazo": f"Grabando: traza la {nombre} y quédate quieto. Repite las veces que quieras.",
            "letra": f"Forma la {nombre} dentro del recuadro y sostenla…",
        }[tipo])
        if not self.ventana.activo:
            self.ventana.iniciar()

    def detener_grabacion(self) -> None:
        self.grabando = False
        self._reiniciar_toma()
        if hasattr(self, "btn_grabar"):
            self.btn_grabar.setText("Grabar")
            self.btn_borrar.setEnabled(True)
            self.barra.hide()

    def _reiniciar_toma(self) -> None:
        self._toma_cuadros: list[np.ndarray] = []
        self._toma_puntos: list[np.ndarray] = []
        self._toma_izquierdas = 0
        self._toma_aciertos = 0
        self._toma_inicio: float | None = None
        if hasattr(self, "barra"):
            self.barra.setValue(0)

    def cuadro(self, r: ResultadoCuadro) -> None:
        """Cada cuadro de la cámara mientras la ventana está abierta (VentanaPrincipal._pintar)."""
        clave = self._clave
        if not self.grabando or clave is None:
            return
        persona, nombre, tipo = self.persona.text().strip(), self._nombre(clave), self._tipo(clave)
        entendio = (f" · el modelo actual entendió «{r.prediccion.letra}» ({r.prediccion.confianza:.0%})"
                    if r.prediccion else "")
        if tipo == "palabra" and r.sena_terminada is not None:
            if not self.grabador.palabra(clave, persona, r.sena_terminada, r.fps):
                self.aviso.setText("No se guardó: la seña duró 4 segundos sin que se viera el final. Baja las manos "
                                   "del todo (sobre las piernas o a los lados) al terminar cada seña.")
                return
            n = self.grabador.cuantas(tipo, clave)
            self.aviso.setText(f"Muestra {n} de «{nombre}» guardada{entendio}. Haz la siguiente.")
        elif tipo == "trazo" and r.trazo is not None:
            self.grabador.trazo(clave, persona, *r.trazo)
            n = self.grabador.cuantas(tipo, clave)
            self.aviso.setText(f"Muestra {n} de la {nombre} guardada{entendio}. Haz la siguiente.")
        elif tipo == "letra" and r.mano is not None and r.puntos_mano is not None:
            ahora = time.monotonic()
            if self._toma_inicio is None:
                self._toma_inicio = ahora
            if ahora - self._toma_inicio < SEGUNDOS_PREPARAR_LETRA:  # se deja formar la seña
                return
            self._toma_cuadros.append(np.asarray(r.mano.caracteristicas, np.float32))
            self._toma_puntos.append(r.puntos_mano)
            self._toma_izquierdas += int(r.mano.es_izquierda)
            self._toma_aciertos += int(r.prediccion is not None and r.prediccion.letra == clave)
            n = len(self._toma_cuadros)
            self.barra.setValue(n)
            if n < CUADROS_TOMA_LETRA:
                return
            self.grabador.letra(clave, persona, self._toma_cuadros, self._toma_puntos, self._toma_izquierdas * 2 > n)
            acierto = self._toma_aciertos / n
            total = self.grabador.cuantas(tipo, clave)
            self.detener_grabacion()
            self.aviso.setText(f"Muestra {total} de la {nombre} guardada · el modelo actual la reconoció en el "
                               f"{acierto:.0%} de los cuadros. Toca «Grabar» para otra (mejor moviendo un poco la mano).")
        else:
            return
        self._actualizar_total()

    def borrar_ultima(self) -> None:
        borrada = self.grabador.borrar_ultima()
        self.aviso.setText(f"Se borró la última muestra ({borrada[0]} «{borrada[1]}»)." if borrada
                           else "No hay muestras de esta sesión para borrar.")
        self._actualizar_total()

    def abrir_carpeta(self) -> None:
        self.grabador.carpeta.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.grabador.carpeta))  # noqa: S606 (Windows)

    # ------------------------------------------------------------- reentrenar
    def entrenar_modelos(self) -> None:
        if self._entrenamiento is not None:
            return
        if self.grabador.total == 0:
            self.aviso.setText("Primero graba algunas muestras.")
            return
        self.detener_grabacion()
        if self.ventana.activo:
            self.ventana.detener()  # entrenar ocupa el procesador: la cámara iría muy lenta
        self.registro.clear()
        self.registro.show()
        self.btn_entrenar.setEnabled(False)
        self.btn_entrenar.setText("Entrenando… (no cierres SILVA)")
        self._entrenamiento = TrabajadorEntrenamiento(self)
        self._entrenamiento.texto.connect(self._agregar_registro)
        self._entrenamiento.terminado.connect(self._al_terminar_entrenamiento)
        self._entrenamiento.start()

    def _agregar_registro(self, texto: str) -> None:
        self.registro.moveCursor(self.registro.textCursor().MoveOperation.End)
        self.registro.insertPlainText(texto)
        self.registro.ensureCursorVisible()

    def _al_terminar_entrenamiento(self, ok: bool, detalle: str) -> None:
        self._entrenamiento.wait()
        self._entrenamiento = None
        self.btn_entrenar.setEnabled(True)
        self.btn_entrenar.setText("Entrenar los modelos ahora")
        self._actualizar_modelos_propios()
        if ok:
            QMessageBox.information(
                self, "Entrenar",
                "Listo. Cierra y vuelve a abrir SILVA para usar los modelos nuevos.\n\n"
                "Para el teléfono quedó un paquete silva_modelo_<fecha>.zip (en Descargas, o en dist si abriste SILVA "
                "desde el código): pásalo al teléfono e impórtalo en Entrenar → Más… → Importar modelo.")
        else:
            QMessageBox.warning(self, "Entrenar", f"El entrenamiento falló: {detalle}\n\nEl detalle está en el registro.")

    def _actualizar_modelos_propios(self) -> None:
        """En el ejecutable, «Volver a los modelos originales» aparece si hay modelos entrenados aquí."""
        propios = config.EMPAQUETADO and any(config.DIR_MODELOS_PROPIOS.glob("*.pkl"))
        self.btn_originales.setVisible(bool(propios))

    def volver_a_los_originales(self) -> None:
        respuesta = QMessageBox.question(
            self, "Entrenar", "¿Borrar los modelos entrenados con sus muestras y volver a los que trae SILVA? "
            "Las muestras grabadas no se borran.")
        if respuesta != QMessageBox.Yes:
            return
        for modelo in config.DIR_MODELOS_PROPIOS.glob("*.pkl"):
            modelo.unlink()
        self._actualizar_modelos_propios()
        QMessageBox.information(self, "Entrenar", "Listo. Cierra y vuelve a abrir SILVA para usar los modelos originales.")

    # ------------------------------------------------------------- abrir y cerrar
    def showEvent(self, evento) -> None:
        with self.ventana._candado:
            self.ctrl.entrenando = True
        super().showEvent(evento)

    def hideEvent(self, evento) -> None:
        self.detener_grabacion()
        with self.ventana._candado:
            self.ctrl.entrenando = False
        super().hideEvent(evento)


class DialogoRespuesta(QDialog):
    respuesta_lista = Signal(str)

    def __init__(self, padre: QWidget, animaciones: AnimacionesSenas | None = None) -> None:
        super().__init__(padre)
        self._animaciones = animaciones
        self.setWindowTitle("Responder")
        self.setStyleSheet(HOJA_ESTILO)
        self.resize(640, 320)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)
        v.addWidget(_etiqueta("Responder por escrito", "titulo"))
        nota = _etiqueta("Escribe tu respuesta: se mostrará en grande sobre el video para que la persona sorda la lea.",
                         "estado")
        nota.setWordWrap(True)
        v.addWidget(nota)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Escribe aquí")
        v.addWidget(self.editor, 1)
        self.lbl_senas = _etiqueta("", "estado")
        self.lbl_senas.setWordWrap(True)
        v.addWidget(self.lbl_senas)
        self.editor.textChanged.connect(self._actualizar_senas)
        self._actualizar_senas()
        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("Ctrl+Enter para mostrar", "atajos"))
        fila.addStretch()
        fila.addWidget(_boton("Cancelar", "secundario", self.reject))
        self.btn_mostrar = _boton("Mostrar en grande", "primario", self._mostrar)
        fila.addWidget(self.btn_mostrar)
        v.addLayout(fila)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._mostrar)
        self.editor.setFocus()

    def _actualizar_senas(self) -> None:
        if self._animaciones is None:
            self.lbl_senas.setText("")
            return
        senas = self._animaciones.buscar(self.editor.toPlainText())
        self.lbl_senas.setText("También se mostrará en señas: " + " · ".join(senas) if senas else
                               "Las palabras con seña conocida (hola, gracias, por favor…) se mostrarán también en señas.")

    def _mostrar(self) -> None:
        texto = self.editor.toPlainText().strip()
        if texto:
            self.respuesta_lista.emit(texto)
            self.accept()


def _html(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _mano_en_borde(c) -> bool:
    """La mano (o la muñeca estimada por la pose) toca o sale del borde de la imagen."""
    for mano in (c.mano_izquierda, c.mano_derecha):
        if mano is not None and any(lm.x < 0.03 or lm.x > 0.97 or lm.y < 0.03 for lm in mano):
            return True
    if c.pose is not None:
        return any(not (0.0 <= c.pose[i].x <= 1.0 and 0.0 <= c.pose[i].y <= 1.0) for i in (15, 16))
    return False
