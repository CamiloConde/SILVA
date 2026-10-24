"""VentanaPrincipal: interfaz de escritorio en PySide6 (Qt).

La cámara y MediaPipe corren en un hilo aparte (TrabajadorVideo): la ventana
solo recibe cada cuadro ya procesado y nunca se congela mientras se detecta.
Es el paralelismo del diagrama de actividades (Figura 6): una rama muestra el
video y la otra detecta la mano.
"""

from __future__ import annotations

import threading
import time

import cv2
import numpy as np
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QIcon, QImage, QKeySequence, QPainter, QPainterPath, QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QDialog, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLayout, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from silva import __version__, config
from silva.captura_video import CamaraNoDisponibleError
from silva.controlador import MODO_LETRAS, MODO_PALABRAS, ControladorSILVA, ResultadoCuadro
from silva.cuerpo import dibujar_cuerpo
from silva.detector_manos import dibujar_mano

# Paleta (tema oscuro)
FONDO = "#0b1120"
TARJETA = "#151e32"
TARJETA_2 = "#1e293b"
BORDE = "#26334a"
TEXTO = "#f1f5f9"
SUAVE = "#94a3b8"
TENUE = "#64748b"
ACENTO = "#3b82f6"
OK = "#22c55e"
ALERTA = "#f59e0b"
PELIGRO = "#ef4444"
VIDEO_FONDO = "#020617"

HOJA_ESTILO = f"""
QWidget {{ background: transparent; color: {TEXTO}; font-family: "Segoe UI"; font-size: 10pt; }}
#raiz {{ background: {FONDO}; }}
#tarjeta {{ background: {TARJETA}; border: 1px solid {BORDE}; border-radius: 14px; }}
#titulo {{ font-size: 20pt; font-weight: 700; letter-spacing: 1px; }}
#subtitulo {{ color: {SUAVE}; font-size: 11pt; }}
#seccion {{ color: {TENUE}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
#suave {{ color: {SUAVE}; }}
#tenue {{ color: {TENUE}; font-size: 9pt; }}

#selector {{ background: {TARJETA}; border: 1px solid {BORDE}; border-radius: 10px; }}
QPushButton#modo {{ background: transparent; color: {SUAVE}; border: none; border-radius: 7px;
                    padding: 6px 18px; font-weight: 600; }}
QPushButton#modo:hover {{ color: {TEXTO}; }}
QPushButton#modo:checked {{ background: {ACENTO}; color: white; }}
QPushButton#modo:disabled {{ color: {TENUE}; }}

#pastilla {{ border-radius: 12px; padding: 4px 14px; font-weight: 600; background: {TARJETA_2}; }}
#pastilla[estado="apagada"] {{ color: {TENUE}; }}
#pastilla[estado="conectando"] {{ color: {ALERTA}; }}
#pastilla[estado="vivo"] {{ color: {OK}; background: rgba(34, 197, 94, 0.12); }}

#detectada {{ background: {TARJETA_2}; border-radius: 12px; border: 2px solid transparent; }}
#detectada[confirmada="true"] {{ border: 2px solid {OK}; }}
#letra {{ font-weight: 700; color: {TEXTO}; font-size: 64pt; }}
#letra[tam="palabra"] {{ font-size: 24pt; }}
#letra[dudosa="true"] {{ color: {TENUE}; }}

QProgressBar {{ background: {TARJETA_2}; border: none; border-radius: 4px; max-height: 8px; min-height: 8px; }}
QProgressBar::chunk {{ border-radius: 4px; background: {ACENTO}; }}
QProgressBar#conf::chunk {{ background: {OK}; }}
QProgressBar#conf[baja="true"]::chunk {{ background: {ALERTA}; }}
#valorconf {{ font-weight: 700; }}
#valorconf[baja="true"] {{ color: {ALERTA}; }}
#valorconf[alta="true"] {{ color: {OK}; }}
#ultima {{ color: {OK}; }}

#chip {{ background: {TARJETA_2}; color: {SUAVE}; border-radius: 7px; padding: 3px 8px; font-weight: 600;
         font-size: 9pt; }}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDE}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
#chip[activo="true"] {{ background: {ACENTO}; color: white; }}

#texto {{ font-family: "Cascadia Mono", "Consolas"; font-size: 22pt; font-weight: 700; }}
#texto[vacio="true"] {{ font-family: "Segoe UI"; font-size: 12pt; font-weight: 400; color: {TENUE}; }}

QPushButton {{ border: none; border-radius: 9px; padding: 9px 18px; font-weight: 600; }}
QPushButton#primario {{ background: {ACENTO}; color: white; }}
QPushButton#primario:hover {{ background: #2563eb; }}
QPushButton#primario[peligro="true"] {{ background: {PELIGRO}; }}
QPushButton#primario[peligro="true"]:hover {{ background: #dc2626; }}
QPushButton#primario:disabled {{ background: {TARJETA_2}; color: {TENUE}; }}
QPushButton#secundario {{ background: {TARJETA_2}; color: {TEXTO}; }}
QPushButton#secundario:hover {{ background: {BORDE}; }}
QPushButton#secundario:disabled {{ background: {TARJETA}; color: {TENUE}; }}

QDialog {{ background: {FONDO}; }}
QTableWidget {{ background: {TARJETA}; border: 1px solid {BORDE}; border-radius: 10px; gridline-color: {BORDE};
               selection-background-color: {ACENTO}; }}
QHeaderView::section {{ background: {TARJETA_2}; color: {SUAVE}; border: none; padding: 6px; font-weight: 600; }}
QPlainTextEdit {{ background: {TARJETA}; border: 1px solid {BORDE}; border-radius: 10px; padding: 8px;
                  font-size: 20pt; selection-background-color: {ACENTO}; }}
QPlainTextEdit:focus {{ border: 1px solid {ACENTO}; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: {TARJETA}; color: {SUAVE}; padding: 7px 16px; border-radius: 7px; margin-right: 4px;
               font-weight: 600; }}
QTabBar::tab:selected {{ background: {ACENTO}; color: white; }}
QToolTip {{ background: {TARJETA_2}; color: {TEXTO}; border: 1px solid {BORDE}; }}
"""


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


def _tarjeta() -> QFrame:
    marco = QFrame()
    marco.setObjectName("tarjeta")
    return marco


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
            hay_evento = r.letra_confirmada is not None or r.descartada is not None
            if self.interfaz_libre.is_set() or hay_evento:
                self.interfaz_libre.clear()
                self.cuadro_listo.emit(r, componer_imagen(r))


# --------------------------------------------------------------------------------- widgets
class VideoWidget(QWidget):
    """Muestra el video con esquinas redondeadas y los avisos superpuestos."""

    respuesta_cerrada = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._imagen: QImage | None = None
        self._respuesta: str | None = None
        self._aviso = ""
        self._banda: str | None = None
        self._grabando = False
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self) -> QSize:
        return QSize(720, 540)

    def poner_imagen(self, imagen: QImage) -> None:
        self._imagen = imagen
        self.update()

    def poner_aviso(self, texto: str) -> None:
        """Quita el video y muestra un mensaje centrado."""
        self._imagen, self._aviso, self._banda, self._grabando = None, texto, None, False
        self.update()

    def poner_banda(self, texto: str | None) -> None:
        if texto != self._banda:
            self._banda = texto
            self.update()

    def poner_respuesta(self, texto: str | None) -> None:
        """RF-09: muestra en grande, sobre el video, la respuesta escrita por la persona oyente."""
        self._respuesta = texto
        self.setCursor(Qt.PointingHandCursor if texto else Qt.ArrowCursor)
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
        marco = QRectF(self.rect())
        recorte = QPainterPath()
        recorte.addRoundedRect(marco, 14, 14)
        p.setClipPath(recorte)
        p.fillRect(self.rect(), QColor(VIDEO_FONDO))

        if self._imagen is not None:
            escalada = self._imagen.size().scaled(self.size(), Qt.KeepAspectRatio)
            destino = QRect(QPoint(0, 0), escalada)
            destino.moveCenter(self.rect().center())
            p.drawImage(destino, self._imagen)
        else:
            centro = self.rect().center()
            p.setPen(QColor(TENUE))
            p.setFont(QFont("Segoe UI Emoji", 30))
            p.drawText(QRect(0, centro.y() - 70, self.width(), 60), Qt.AlignCenter, "📷")
            p.setPen(QColor(SUAVE))
            p.setFont(QFont("Segoe UI", 12))
            p.drawText(QRect(20, centro.y() - 5, self.width() - 40, 40), Qt.AlignCenter, self._aviso)

        if self._respuesta is not None:  # la respuesta tapa todo lo demás
            self._pintar_respuesta(p)
            p.end()
            return

        if self._grabando:
            pastilla = QRectF(14, 14, 170, 32)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(127, 29, 29, 210))
            p.drawRoundedRect(pastilla, 16, 16)
            p.setBrush(QColor("#f87171"))
            p.drawEllipse(QRectF(28, 24, 12, 12))
            p.setPen(QColor("#fee2e2"))
            p.setFont(QFont("Segoe UI Semibold", 10))
            p.drawText(pastilla.adjusted(34, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, "Grabando seña")

        if self._banda:
            p.setFont(QFont("Segoe UI Semibold", 11))
            banda = QRectF(16, self.height() - 62, self.width() - 32, 44)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(120, 53, 15, 225))
            p.drawRoundedRect(banda, 12, 12)
            p.setPen(QColor("#fde68a"))
            p.drawText(banda.adjusted(12, 0, -12, 0), Qt.AlignCenter | Qt.TextWordWrap, self._banda)

        p.end()

    def _pintar_respuesta(self, p: QPainter) -> None:
        p.fillRect(self.rect(), QColor(2, 6, 23, 235))
        margen = 28
        p.setPen(QColor(SUAVE))
        p.setFont(QFont("Segoe UI Semibold", 11))
        p.drawText(QRect(margen, margen, self.width() - 2 * margen, 24), Qt.AlignLeft,
                   "💬  RESPUESTA DE LA PERSONA OYENTE")
        area = QRect(margen, margen + 40, self.width() - 2 * margen, self.height() - 2 * margen - 80)
        # Letra tan grande como quepa (entre 18 y 60 pt), para leerla a distancia
        tam = 60
        while tam > 18:
            ocupado = QFontMetrics(QFont("Segoe UI Semibold", tam)).boundingRect(
                area, Qt.TextWordWrap | Qt.AlignCenter, self._respuesta)
            if ocupado.height() <= area.height() and ocupado.width() <= area.width():
                break
            tam -= 2
        p.setFont(QFont("Segoe UI Semibold", tam))
        p.setPen(QColor(TEXTO))
        p.drawText(area, Qt.TextWordWrap | Qt.AlignCenter, self._respuesta)
        p.setPen(QColor(TENUE))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRect(0, self.height() - margen - 20, self.width(), 20), Qt.AlignCenter,
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


# ---------------------------------------------------------------------------- ventana
class VentanaPrincipal(QWidget):
    def __init__(self, controlador: ControladorSILVA) -> None:
        super().__init__()
        self.ctrl = controlador
        self._candado = threading.Lock()
        self._trabajador: TrabajadorVideo | None = None
        self._chips: dict[str, QLabel] = {}
        self._chip_activo: str | None = None
        self._aviso_temporal: tuple[str, float] | None = None
        self._dialogo_historial: QDialog | None = None
        self.mostrar_error = self._mostrar_error  # reemplazable en pruebas

        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(f"SILVA {__version__} — Traductor de señas a texto")
        if config.RUTA_ICONO.exists():
            self.setWindowIcon(QIcon(str(config.RUTA_ICONO)))
        self.setStyleSheet(HOJA_ESTILO)
        self._construir()
        self._atajos()
        self._mostrar_inactivo()
        self._aplicar_modo()
        self.resize(1180, 820)

    # --------------------------------------------------------------- construcción
    def _construir(self) -> None:
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 18, 22, 18)
        raiz.setSpacing(14)

        # Encabezado
        cab = QHBoxLayout()
        cab.addWidget(_etiqueta("SILVA", "titulo"))
        cab.addSpacing(8)
        cab.addWidget(_etiqueta("Traductor de señas LSC a texto", "subtitulo"), 0, Qt.AlignBottom)
        cab.addSpacing(24)
        selector = QFrame()
        selector.setObjectName("selector")
        fila_sel = QHBoxLayout(selector)
        fila_sel.setContentsMargins(3, 3, 3, 3)
        fila_sel.setSpacing(2)
        self.grupo_modo = QButtonGroup(self)
        self.btn_modo: dict[str, QPushButton] = {}
        for modo, texto in ((MODO_LETRAS, "Deletreo"), (MODO_PALABRAS, "Palabras")):
            b = _boton(texto, "modo", lambda _=False, m=modo: self.cambiar_modo(m))
            b.setCheckable(True)
            self.grupo_modo.addButton(b)
            fila_sel.addWidget(b)
            self.btn_modo[modo] = b
        if not self.ctrl.palabras_disponibles:
            self.btn_modo[MODO_PALABRAS].setEnabled(False)
            self.btn_modo[MODO_PALABRAS].setToolTip("Falta modelos/modelo_palabras.pkl")
        cab.addWidget(selector, 0, Qt.AlignVCenter)
        cab.addStretch()
        self.lbl_pastilla = _etiqueta("", "pastilla")
        cab.addWidget(self.lbl_pastilla, 0, Qt.AlignVCenter)
        self.lbl_fps = _etiqueta("", "tenue")
        self.lbl_fps.setMinimumWidth(56)
        self.lbl_fps.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cab.addWidget(self.lbl_fps, 0, Qt.AlignVCenter)
        raiz.addLayout(cab)

        # Cuerpo: video + panel lateral
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(14)
        self.video = VideoWidget()
        cuerpo.addWidget(self.video, 1)
        cuerpo.addWidget(self._panel_lateral())
        raiz.addLayout(cuerpo, 1)

        # Texto de la sesión
        caja = _tarjeta()
        v = QVBoxLayout(caja)
        v.setContentsMargins(20, 12, 20, 14)
        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("TEXTO DE LA SESIÓN", "seccion"))
        fila.addStretch()
        self.lbl_sesion = _etiqueta("", "tenue")
        fila.addWidget(self.lbl_sesion)
        v.addLayout(fila)
        self.lbl_texto = _etiqueta("", "texto")
        self.lbl_texto.setWordWrap(True)
        self.lbl_texto.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_texto.setMinimumHeight(84)
        self.lbl_texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.lbl_texto)
        raiz.addWidget(caja)

        # Botones
        barra = QHBoxLayout()
        barra.setSpacing(8)
        self.btn_principal = _boton("", "primario", self.alternar)
        self.btn_principal.setMinimumWidth(130)
        barra.addWidget(self.btn_principal)
        barra.addSpacing(16)
        self.btn_espacio = _boton("␣  Espacio", "secundario", self.espacio)
        self.btn_borrar = _boton("⌫  Borrar", "secundario", self.borrar)
        self.btn_limpiar = _boton("Limpiar", "secundario", self.limpiar)
        for b in (self.btn_espacio, self.btn_borrar, self.btn_limpiar):
            barra.addWidget(b)
        barra.addStretch()
        barra.addWidget(_etiqueta("Enter: iniciar/detener · Espacio · Retroceso · Supr · Ctrl+R: responder",
                                  "tenue"))
        barra.addSpacing(12)
        self.btn_responder = _boton("💬  Responder", "secundario", self.responder)
        self.btn_responder.setToolTip("La persona oyente escribe su respuesta y se muestra en grande (Ctrl+R)")
        barra.addWidget(self.btn_responder)
        barra.addWidget(_boton("🕘  Historial", "secundario", self.ver_historial))
        raiz.addLayout(barra)

    def _panel_lateral(self) -> QFrame:
        panel = _tarjeta()
        panel.setFixedWidth(330)
        v = QVBoxLayout(panel)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(6)

        self.lbl_titulo_det = _etiqueta("LETRA DETECTADA", "seccion")
        v.addWidget(self.lbl_titulo_det)
        self.marco_detectada = QFrame()
        self.marco_detectada.setObjectName("detectada")
        self.marco_detectada.setFixedHeight(150)
        dentro = QVBoxLayout(self.marco_detectada)
        self.lbl_letra = _etiqueta("–", "letra")
        self.lbl_letra.setAlignment(Qt.AlignCenter)
        self.lbl_letra.setWordWrap(True)
        dentro.addWidget(self.lbl_letra)
        self._opacidad = QGraphicsOpacityEffect(self.lbl_letra)
        self._opacidad.setOpacity(1.0)
        self.lbl_letra.setGraphicsEffect(self._opacidad)
        self._animacion = QPropertyAnimation(self._opacidad, b"opacity", self)
        self._animacion.setDuration(320)
        self._animacion.setStartValue(0.15)
        self._animacion.setEndValue(1.0)
        self._animacion.setEasingCurve(QEasingCurve.OutCubic)
        v.addWidget(self.marco_detectada)
        v.addSpacing(10)

        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("Confianza", "suave"))
        fila.addStretch()
        self.lbl_conf = _etiqueta("—", "valorconf")
        fila.addWidget(self.lbl_conf)
        v.addLayout(fila)
        self.barra_conf = QProgressBar()
        self.barra_conf.setObjectName("conf")
        self.barra_conf.setTextVisible(False)
        v.addWidget(self.barra_conf)
        v.addSpacing(8)

        fila = QHBoxLayout()
        self.lbl_estable_tit = _etiqueta("Estabilidad", "suave")
        fila.addWidget(self.lbl_estable_tit)
        fila.addStretch()
        self.lbl_estable_info = _etiqueta("", "tenue")
        fila.addWidget(self.lbl_estable_info)
        v.addLayout(fila)
        self.barra_estable = QProgressBar()
        self.barra_estable.setTextVisible(False)
        v.addWidget(self.barra_estable)
        v.addSpacing(8)

        self.lbl_ultima = _etiqueta("", "ultima")
        self.lbl_ultima.setWordWrap(True)
        self.lbl_ultima.setMinimumHeight(22)
        v.addWidget(self.lbl_ultima)
        v.addSpacing(8)

        # Letras o palabras disponibles (QStackedWidget: el panel no cambia de alto al cambiar de modo)
        self.pila = QStackedWidget()
        self.pila.addWidget(self._lista_disponibles(
            "LETRAS DISPONIBLES", list(getattr(self.ctrl.clasificador, "letras", []))))
        palabras = sorted(self.ctrl.clasificador_palabras.nombres.values()) if self.ctrl.palabras_disponibles else []
        self.pila.addWidget(self._lista_disponibles(
            "PALABRAS DISPONIBLES", palabras, "Empiece con las manos abajo, haga la seña y vuelva a bajarlas."))
        v.addWidget(self.pila, 1)
        return panel

    def _lista_disponibles(self, titulo: str, elementos: list[str], consejo: str = "") -> QWidget:
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(_etiqueta(titulo, "seccion"))
        flujo_w = QWidget()
        flujo = FlujoLayout(5)
        flujo.setContentsMargins(0, 4, 4, 0)
        flujo_w.setLayout(flujo)
        desplazable = QScrollArea()  # si no caben todas, se desplazan sin agrandar el panel
        desplazable.setWidgetResizable(True)
        desplazable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        desplazable.setWidget(flujo_w)
        desplazable.viewport().setAutoFillBackground(False)
        flujo_w.setAutoFillBackground(False)
        for e in elementos:
            chip = _etiqueta(e, "chip")
            if len(e) == 1:
                chip.setMinimumWidth(30)
                chip.setAlignment(Qt.AlignCenter)
            flujo.addWidget(chip)
            self._chips[e] = chip
        v.addWidget(desplazable, 1)
        if consejo:
            nota = _etiqueta(consejo, "tenue")
            nota.setWordWrap(True)
            v.addSpacing(6)
            v.addWidget(nota)
        return caja

    def _atajos(self) -> None:
        for tecla, accion in ((Qt.Key_Return, self.alternar), (Qt.Key_Enter, self.alternar),
                              (Qt.Key_Space, self.espacio), (Qt.Key_Backspace, self.borrar),
                              (Qt.Key_Delete, self.limpiar)):
            QShortcut(QKeySequence(tecla), self, activated=accion)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.responder)
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
        self._poner_pastilla("●  Conectando", "conectando")
        self.btn_principal.setEnabled(False)
        self._trabajador = TrabajadorVideo(self.ctrl, self._candado)
        self._trabajador.iniciado.connect(self._al_iniciar)
        self._trabajador.fallo.connect(self._al_fallar)
        self._trabajador.cuadro_listo.connect(self._pintar)
        self._trabajador.start()

    def _al_iniciar(self, sesion_id: int) -> None:
        self.btn_principal.setEnabled(True)
        self.btn_principal.setText("■  Detener")
        _repulir(self.btn_principal, peligro=True)
        self._poner_pastilla("●  En vivo", "vivo")
        self.lbl_sesion.setText(f"Sesión #{sesion_id}")
        self.lbl_ultima.setText("")
        self._actualizar_texto()

    def _al_fallar(self, _mensaje: str) -> None:
        self._trabajador.wait()
        self._trabajador = None
        self.btn_principal.setEnabled(True)
        self._mostrar_inactivo()
        self.mostrar_error(
            "Cámara no disponible",
            "No se pudo abrir la cámara web.\n\nVerifique que esté conectada y que ninguna otra "
            "aplicación (Zoom, Teams, la app Cámara…) la esté usando.",
        )

    def detener(self) -> None:
        if not self.activo:
            return
        self._parar_trabajador()
        with self._candado:
            self.ctrl.detener()  # guarda la sesión y después libera la cámara (Figura 5)
        self._mostrar_inactivo()
        self.lbl_sesion.setText(f"Sesión #{self.ctrl.sesion_id} guardada en el historial ✓")

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
        self.lbl_titulo_det.setText("PALABRA DETECTADA" if palabras else "LETRA DETECTADA")
        self.lbl_estable_tit.setText("Seña en curso" if palabras else "Estabilidad")
        self.lbl_estable_info.setText(
            "" if palabras else f"{self.ctrl.buffer.cuadros_estables} cuadros para confirmar")
        self.pila.setCurrentIndex(1 if palabras else 0)
        self.btn_espacio.setVisible(not palabras)
        self._poner_letra("–", dudosa=True)
        self.lbl_ultima.setText("")
        self._poner_confianza(None)
        self._resaltar(None)
        self.barra_estable.setValue(0)
        self.video.poner_grabando(False)
        self._aviso_temporal = None
        self._actualizar_texto()

    def espacio(self) -> None:
        with self._candado:
            self.ctrl.buffer.agregar_espacio()
        self._actualizar_texto()

    def borrar(self) -> None:
        with self._candado:
            self.ctrl.buffer.borrar_ultima()
        self._actualizar_texto()

    def limpiar(self) -> None:
        with self._candado:
            self.ctrl.buffer.limpiar()
        self._actualizar_texto()

    def closeEvent(self, evento) -> None:
        self._parar_trabajador()
        with self._candado:
            self.ctrl.cerrar()
        if self._dialogo_historial is not None:
            self._dialogo_historial.close()
        evento.accept()

    # ------------------------------------------------------------- cuadros de video
    def _pintar(self, r: ResultadoCuadro, imagen: QImage) -> None:
        try:
            if not self.activo:
                return
            self.video.poner_imagen(imagen)
            self.lbl_fps.setText(f"{r.fps:.0f} FPS")
            if r.cuerpo is not None:
                self._pintar_palabras(r)
            else:
                self._pintar_letras(r)
        finally:
            if self._trabajador is not None:
                self._trabajador.interfaz_libre.set()

    def _pintar_letras(self, r: ResultadoCuadro) -> None:
        self.video.poner_grabando(False)
        if r.prediccion is None:
            self.video.poner_banda("✋  No se detecta la mano")  # RF-06
            self._poner_letra("–", dudosa=True)
            self._poner_confianza(None)
            self._resaltar(None)
        else:
            self.video.poner_banda(None)
            p = r.prediccion
            aceptable = p.confianza >= self.ctrl.buffer.umbral
            self._poner_letra(p.letra, dudosa=not aceptable)
            self._poner_confianza(p.confianza)
            self._resaltar(p.letra if aceptable else None)
        self.barra_estable.setValue(int(r.progreso * 100))
        if r.letra_confirmada is not None:  # RF-08
            self._confirmar(r.letra_confirmada, r.prediccion.confianza, "Última confirmada")

    def _pintar_palabras(self, r: ResultadoCuadro) -> None:
        self.video.poner_grabando(r.grabando_sena)
        self.barra_estable.setValue(int(r.progreso * 100) if r.grabando_sena else 0)
        if r.descartada is not None:
            d = r.descartada
            self._aviso_temporal = (f"No se reconoció la seña (parecía «{d.letra}», {d.confianza:.0%}). Repítala",
                                    time.monotonic() + 2.5)
            self._poner_letra(d.letra, dudosa=True)
            self._poner_confianza(d.confianza)
        if r.letra_confirmada is not None:
            self._aviso_temporal = None
            self._confirmar(r.letra_confirmada, r.prediccion.confianza, "Última palabra")
        if r.cuerpo.pose is None:
            self.video.poner_banda("🧍  Colóquese frente a la cámara: deben verse los hombros y las manos")
        elif self._aviso_temporal and time.monotonic() < self._aviso_temporal[1]:
            self.video.poner_banda(self._aviso_temporal[0])
        else:
            self.video.poner_banda(None)

    def _confirmar(self, texto: str, confianza: float, rotulo: str) -> None:
        self._poner_letra(texto, dudosa=False)
        self._poner_confianza(confianza)
        self._resaltar(texto)
        self.lbl_ultima.setText(f"✓  {rotulo}: {texto}  ·  {confianza:.0%}")
        self._actualizar_texto()
        # Realce breve: la tarjeta se enmarca en verde y el texto aparece con un fundido
        _repulir(self.marco_detectada, confirmada=True)
        QTimer.singleShot(650, lambda: _repulir(self.marco_detectada, confirmada=False))
        self._animacion.stop()
        self._animacion.start()

    # ------------------------------------------------------------------ utilidades
    def _poner_letra(self, texto: str, dudosa: bool) -> None:
        tam = "palabra" if self.ctrl.modo == MODO_PALABRAS and texto != "–" else "letra"
        self.lbl_letra.setText(texto)
        if self.lbl_letra.property("dudosa") != dudosa or self.lbl_letra.property("tam") != tam:
            _repulir(self.lbl_letra, dudosa=dudosa, tam=tam)

    def _poner_confianza(self, confianza: float | None) -> None:
        if confianza is None:
            self.barra_conf.setValue(0)
            self.lbl_conf.setText("—")
            _repulir(self.lbl_conf, baja=False, alta=False)
            return
        umbral = self.ctrl.umbral_palabras if self.ctrl.modo == MODO_PALABRAS else self.ctrl.buffer.umbral
        aceptable = confianza >= umbral
        self.barra_conf.setValue(int(confianza * 100))
        self.lbl_conf.setText(f"{confianza:.0%}")
        if self.barra_conf.property("baja") != (not aceptable):
            _repulir(self.barra_conf, baja=not aceptable)
        _repulir(self.lbl_conf, baja=not aceptable, alta=aceptable)

    def _resaltar(self, clave: str | None) -> None:
        if clave == self._chip_activo:
            return
        if self._chip_activo in self._chips:
            _repulir(self._chips[self._chip_activo], activo=False)
        if clave in self._chips:
            _repulir(self._chips[clave], activo=True)
        self._chip_activo = clave

    def _poner_pastilla(self, texto: str, estado: str) -> None:
        self.lbl_pastilla.setText(texto)
        _repulir(self.lbl_pastilla, estado=estado)

    def _actualizar_texto(self) -> None:
        with self._candado:
            texto = self.ctrl.buffer.texto
        if texto:
            self.lbl_texto.setText(texto + ("▏" if self.activo else ""))
        else:
            unidad = "palabras" if self.ctrl.modo == MODO_PALABRAS else "letras"
            self.lbl_texto.setText(f"Las {unidad} confirmadas aparecerán aquí")
        if self.lbl_texto.property("vacio") != (not texto):
            _repulir(self.lbl_texto, vacio=not texto)
        self.btn_borrar.setEnabled(bool(texto))
        self.btn_limpiar.setEnabled(bool(texto))

    def _mostrar_inactivo(self) -> None:
        self.btn_principal.setText("▶  Iniciar")
        _repulir(self.btn_principal, peligro=False)
        self.video.poner_aviso("Presione «Iniciar» para encender la cámara")
        self._poner_pastilla("●  Cámara apagada", "apagada")
        self.lbl_fps.setText("")
        self._poner_letra("–", dudosa=True)
        self._poner_confianza(None)
        self._resaltar(None)
        self.barra_estable.setValue(0)
        self._aviso_temporal = None
        self._actualizar_texto()

    def _mostrar_error(self, titulo: str, mensaje: str) -> None:
        QMessageBox.critical(self, titulo, mensaje)

    def ver_historial(self) -> None:
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Historial")
        dialogo.setStyleSheet(HOJA_ESTILO)
        dialogo.resize(780, 460)
        v = QVBoxLayout(dialogo)
        v.setContentsMargins(18, 16, 18, 16)
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

    def responder(self) -> None:
        """RF-09: la persona oyente escribe y la respuesta se muestra en grande sobre el video."""
        dialogo = DialogoRespuesta(self)
        self._dialogo_respuesta = dialogo
        dialogo.respuesta_lista.connect(self.mostrar_respuesta)
        dialogo.show()

    def mostrar_respuesta(self, texto: str) -> None:
        with self._candado:
            self.ctrl.historial.registrar_respuesta(self.ctrl.sesion_id if self.activo else None, texto)
        self.video.poner_respuesta(texto)


class DialogoRespuesta(QDialog):
    respuesta_lista = Signal(str)

    def __init__(self, padre: QWidget) -> None:
        super().__init__(padre)
        self.setWindowTitle("Responder")
        self.setStyleSheet(HOJA_ESTILO)
        self.resize(620, 300)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(10)
        v.addWidget(_etiqueta("Responder a la persona sorda", "titulo"))
        nota = _etiqueta("Escriba su respuesta; se mostrará en grande sobre el video para que la lea.", "suave")
        nota.setWordWrap(True)
        v.addWidget(nota)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Por ejemplo: «Siga, el médico lo atiende en 5 minutos»")
        v.addWidget(self.editor, 1)
        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("Ctrl+Enter para mostrar", "tenue"))
        fila.addStretch()
        fila.addWidget(_boton("Cancelar", "secundario", self.reject))
        self.btn_mostrar = _boton("Mostrar en grande", "primario", self._mostrar)
        fila.addWidget(self.btn_mostrar)
        v.addLayout(fila)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._mostrar)
        self.editor.setFocus()

    def _mostrar(self) -> None:
        texto = self.editor.toPlainText().strip()
        if texto:
            self.respuesta_lista.emit(texto)
            self.accept()
