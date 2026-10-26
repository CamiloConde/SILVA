"""ControladorSILVA: orquesta el ciclo captura → detección → clasificación → texto."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np

from silva.buffer_texto import BufferTexto
from silva.captura_video import CapturaVideo
from silva.clasificador import Clasificador
from silva.cuerpo import CuadroCuerpo, DetectorCuerpo, caracteristicas_cuadro
from silva.detector_manos import DetectorManos
from silva.modelo import Mano, Prediccion
from silva.palabras import MAX_CUADROS, ClasificadorPalabras, SegmentadorSenas
from silva.repositorio_historial import RepositorioHistorial

MODO_LETRAS = "letras"
MODO_PALABRAS = "palabras"
# Resolución pedida a la cámara en cada modo. Las palabras usan 16:9 porque muchas cámaras de
# portátil recortan los lados en 4:3 y en este modo hace falta ver hombros y brazos (los videos de
# LSC-54 también son 16:9). Las letras siguen en 4:3, el formato con que se entrenó su modelo.
RESOLUCION = {MODO_LETRAS: (640, 480), MODO_PALABRAS: (1280, 720)}
# Si la misma palabra sale dos veces casi seguidas, es casi siempre una seña partida
# en dos (la mano se perdió un instante), no una repetición: se escribe una sola vez.
CUADROS_REPETICION = 20
SEGUNDOS_CONFIRMACION = 2.5  # una palabra provisional se escribe sola tras este tiempo si nadie la corrige
SEGUNDOS_SUGERENCIA = 6.0  # un «¿Quiso decir…?» desaparece sin escribir nada tras este tiempo


@dataclass(frozen=True)
class PalabraPendiente:
    """Palabra reconocida que aún no se escribe, para que alguien pueda confirmarla o corregirla.

    - provisional (`automatica=True`): la seña es segura; se escribe sola al vencer el plazo.
    - sugerencia (`automatica=False`): la seña es dudosa; solo se escribe si alguien elige una opción.
    """

    opciones: tuple[Prediccion, ...]  # hasta 3, de la más a la menos probable
    automatica: bool
    creada: float
    vence: float

    def progreso(self, ahora: float) -> float:
        """Fracción del plazo ya transcurrida (0 → 1)."""
        return min(max((ahora - self.creada) / (self.vence - self.creada), 0.0), 1.0)


@dataclass
class ResultadoCuadro:
    cuadro: np.ndarray
    mano: Mano | None
    prediccion: Prediccion | None
    letra_confirmada: str | None
    texto: str
    progreso: float
    fps: float
    cuerpo: CuadroCuerpo | None = None  # solo en modo Palabras
    grabando_sena: bool = False  # modo Palabras: hay una seña en curso
    pendiente: PalabraPendiente | None = None  # modo Palabras: palabra por confirmar o sugerencia
    ahora: float = 0.0
    brillo: float = 128.0  # brillo medio de la imagen (0-255): con poca luz se pierde el seguimiento

    @property
    def mano_detectada(self) -> bool:
        if self.cuerpo is not None:
            return self.cuerpo.hay_mano
        return self.mano is not None


class ControladorSILVA:
    def __init__(
        self,
        captura: CapturaVideo,
        detector: DetectorManos,
        clasificador: Clasificador,
        historial: RepositorioHistorial,
        buffer: BufferTexto | None = None,
        detector_cuerpo: DetectorCuerpo | None = None,
        clasificador_palabras: ClasificadorPalabras | None = None,
        umbral_palabras: float = 0.5,
        umbral_sugerencia: float = 0.12,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self.captura = captura
        self.detector = detector
        self.clasificador = clasificador
        self.historial = historial
        self.buffer = buffer or BufferTexto()
        self.detector_cuerpo = detector_cuerpo
        self.clasificador_palabras = clasificador_palabras
        self.umbral_palabras = umbral_palabras
        self.umbral_sugerencia = umbral_sugerencia
        self._reloj = reloj
        self.segmentador = SegmentadorSenas()
        self.pendiente: PalabraPendiente | None = None
        self._ultima_palabra: str | None = None
        self._cuadros_desde_palabra = 0
        self.modo = MODO_LETRAS
        self.activo = False
        self.sesion_id: int | None = None
        self.ultima_confianza: float | None = None
        self._t0 = time.monotonic()
        self._fps = 0.0
        self._t_anterior: float | None = None

    @property
    def palabras_disponibles(self) -> bool:
        return self.detector_cuerpo is not None and self.clasificador_palabras is not None

    def cambiar_modo(self, modo: str) -> None:
        if modo == MODO_PALABRAS and not self.palabras_disponibles:
            raise RuntimeError("El modo Palabras no está disponible (falta el modelo)")
        self._cerrar_pendiente()
        self.modo = modo
        self.segmentador.reiniciar()
        self.buffer.reiniciar_deteccion()
        self.captura.configurar(*RESOLUCION[modo])

    def iniciar(self) -> None:
        """CU-01. El modelo ya está cargado (en el constructor); aquí se abre la cámara."""
        if self.activo:
            return
        self.captura.configurar(*RESOLUCION[self.modo])
        self.captura.abrir()  # puede lanzar CamaraNoDisponibleError
        self.buffer.limpiar()
        self.segmentador.reiniciar()
        self.pendiente = None
        self.ultima_confianza = None
        self.sesion_id = self.historial.iniciar_sesion()
        self._t_anterior = None
        self.activo = True

    def procesar_cuadro(self) -> ResultadoCuadro | None:
        """CU-02 y CU-03: procesa un cuadro. Devuelve None si no está activo o no hay imagen."""
        if not self.activo:
            return None
        cuadro = self.captura.leer_cuadro()
        if cuadro is None:
            return None
        marca_ms = int((time.monotonic() - self._t0) * 1000)
        if self.modo == MODO_PALABRAS:
            return self._procesar_palabras(cuadro, marca_ms)

        mano = self.detector.detectar(cuadro, marca_ms)
        prediccion = self.clasificador.predecir(mano.caracteristicas) if mano else None

        confirmada = self.buffer.procesar(prediccion)
        if confirmada is not None:
            self.ultima_confianza = prediccion.confianza
            self.historial.registrar_letra(self.sesion_id, confirmada, prediccion.confianza)

        return ResultadoCuadro(
            cuadro=cuadro,
            mano=mano,
            prediccion=prediccion,
            letra_confirmada=confirmada,
            texto=self.buffer.texto,
            progreso=self.buffer.progreso,
            fps=self._medir_fps(),
            brillo=_brillo(cuadro),
        )

    def _procesar_palabras(self, cuadro: np.ndarray, marca_ms: int) -> ResultadoCuadro:
        ahora = self._reloj()
        cuerpo = self.detector_cuerpo.detectar(cuadro, marca_ms)
        estado = self.segmentador.agregar(caracteristicas_cuadro(cuerpo))
        self._cuadros_desde_palabra += 1
        confirmada = None

        # La pendiente se resuelve al vencer su plazo o cuando empieza una seña nueva
        # (seguir signando = aceptar la provisional e ignorar la sugerencia).
        if self.pendiente is not None and (estado.grabando or ahora >= self.pendiente.vence):
            confirmada = self._cerrar_pendiente()

        prediccion = None
        if estado.terminada is not None:
            evaluacion = self.clasificador_palabras.evaluar(estado.terminada)
            prediccion = evaluacion.mejor
            repetida = (prediccion.letra == self._ultima_palabra
                        and self._cuadros_desde_palabra - len(estado.terminada) < CUADROS_REPETICION)
            segura = prediccion.confianza >= self.umbral_palabras and prediccion.confianza >= evaluacion.prob_otra
            dudosa = (prediccion.confianza >= self.umbral_sugerencia
                      and prediccion.confianza >= 0.5 * evaluacion.prob_otra)
            if not repetida and (segura or dudosa):
                if self.pendiente is not None:  # caso raro: dos señas sin cuadro intermedio
                    confirmada = self._cerrar_pendiente() or confirmada
                plazo = SEGUNDOS_CONFIRMACION if segura else SEGUNDOS_SUGERENCIA
                self.pendiente = PalabraPendiente(tuple(evaluacion.opciones[:3]), segura, ahora, ahora + plazo)
                self._ultima_palabra = prediccion.letra
                self._cuadros_desde_palabra = 0

        return ResultadoCuadro(
            cuadro=cuadro,
            mano=None,
            prediccion=prediccion,
            letra_confirmada=confirmada,
            texto=self.buffer.texto,
            progreso=min(estado.cuadros / MAX_CUADROS, 1.0),
            fps=self._medir_fps(),
            cuerpo=cuerpo,
            grabando_sena=estado.grabando,
            pendiente=self.pendiente,
            ahora=ahora,
            brillo=_brillo(cuadro),
        )

    # ---------------------------------------------------- corrección (RF-13)
    def confirmar_pendiente(self, opcion: int = 0) -> str | None:
        """Escribe la opción elegida (0 = la más probable) de la palabra pendiente."""
        if self.pendiente is None or opcion >= len(self.pendiente.opciones):
            return None
        elegida = self.pendiente.opciones[opcion]
        self.pendiente = None
        self._ultima_palabra = elegida.letra
        self.buffer.agregar_palabra(elegida.letra)
        self.ultima_confianza = elegida.confianza
        self.historial.registrar_letra(self.sesion_id, elegida.letra, elegida.confianza)
        return elegida.letra

    def descartar_pendiente(self) -> None:
        if self.pendiente is not None:
            self._ultima_palabra = None  # permite volver a hacer la misma seña de inmediato
        self.pendiente = None

    def _cerrar_pendiente(self) -> str | None:
        """La provisional se escribe; la sugerencia se descarta."""
        if self.pendiente is None:
            return None
        if self.pendiente.automatica:
            return self.confirmar_pendiente(0)
        self.pendiente = None
        return None

    def detener(self) -> None:
        """CU-05: primero se guarda el texto y después se libera la cámara (Figura 5)."""
        if not self.activo:
            return
        self._cerrar_pendiente()
        self.activo = False
        self.historial.guardar_sesion(self.sesion_id, self.buffer.texto)
        self.captura.liberar()

    def cerrar(self) -> None:
        """Cierre de la aplicación: detener, cerrar historial y liberar recursos."""
        if self.activo:
            self._cerrar_pendiente()
            self.historial.guardar_sesion(self.sesion_id, self.buffer.texto)
            self.activo = False
        self.historial.cerrar()
        self.captura.liberar()
        self.detector.cerrar()
        if self.detector_cuerpo is not None:
            self.detector_cuerpo.cerrar()

    def _medir_fps(self) -> float:
        ahora = time.monotonic()
        if self._t_anterior is not None:
            dt = ahora - self._t_anterior
            if dt > 0:
                instantaneo = 1.0 / dt
                self._fps = instantaneo if self._fps == 0 else 0.9 * self._fps + 0.1 * instantaneo
        self._t_anterior = ahora
        return self._fps


def _brillo(cuadro: np.ndarray) -> float:
    """Brillo medio (0-255) sobre una versión pequeña del cuadro: menos de 1 ms."""
    pequeno = cv2.resize(cuadro, (64, 48), interpolation=cv2.INTER_AREA)
    return float(pequeno.mean())
