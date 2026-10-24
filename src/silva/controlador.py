"""ControladorSILVA: orquesta el ciclo captura → detección → clasificación → texto."""

from __future__ import annotations

import time
from dataclasses import dataclass

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
# Si la misma palabra sale dos veces casi seguidas, es casi siempre una seña partida
# en dos (la mano se perdió un instante), no una repetición: se escribe una sola vez.
CUADROS_REPETICION = 20


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
    descartada: Prediccion | None = None  # modo Palabras: seña terminada pero con confianza baja

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
    ) -> None:
        self.captura = captura
        self.detector = detector
        self.clasificador = clasificador
        self.historial = historial
        self.buffer = buffer or BufferTexto()
        self.detector_cuerpo = detector_cuerpo
        self.clasificador_palabras = clasificador_palabras
        self.umbral_palabras = umbral_palabras
        self.segmentador = SegmentadorSenas()
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
        self.modo = modo
        self.segmentador.reiniciar()
        self.buffer.reiniciar_deteccion()

    def iniciar(self) -> None:
        """CU-01. El modelo ya está cargado (en el constructor); aquí se abre la cámara."""
        if self.activo:
            return
        self.captura.abrir()  # puede lanzar CamaraNoDisponibleError
        self.buffer.limpiar()
        self.segmentador.reiniciar()
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
        )

    def _procesar_palabras(self, cuadro: np.ndarray, marca_ms: int) -> ResultadoCuadro:
        cuerpo = self.detector_cuerpo.detectar(cuadro, marca_ms)
        estado = self.segmentador.agregar(caracteristicas_cuadro(cuerpo))

        prediccion = confirmada = descartada = None
        self._cuadros_desde_palabra += 1
        if estado.terminada is not None:
            prediccion = self.clasificador_palabras.predecir(estado.terminada)
            repetida = (prediccion.letra == self._ultima_palabra
                        and self._cuadros_desde_palabra - len(estado.terminada) < CUADROS_REPETICION)
            if repetida:
                prediccion = None
            elif prediccion.confianza >= self.umbral_palabras:
                self._ultima_palabra = prediccion.letra
                self._cuadros_desde_palabra = 0
                confirmada = prediccion.letra
                self.buffer.agregar_palabra(confirmada)
                self.ultima_confianza = prediccion.confianza
                self.historial.registrar_letra(self.sesion_id, confirmada, prediccion.confianza)
            else:
                descartada = prediccion

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
            descartada=descartada,
        )

    def detener(self) -> None:
        """CU-05: primero se guarda el texto y después se libera la cámara (Figura 5)."""
        if not self.activo:
            return
        self.activo = False
        self.historial.guardar_sesion(self.sesion_id, self.buffer.texto)
        self.captura.liberar()

    def cerrar(self) -> None:
        """Cierre de la aplicación: detener, cerrar historial y liberar recursos."""
        if self.activo:
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
