"""ControladorSILVA: orquesta el ciclo captura → detección → clasificación → texto."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np

from silva import config
from silva.buffer_texto import BufferTexto
from silva.captura_video import CapturaVideo
from silva.clasificador import Clasificador
from silva.cuerpo import CuadroCuerpo, DetectorCuerpo, caracteristicas_cuadro
from silva.detector_manos import DetectorManos
from silva.letras_movimiento import LETRAS_MOVIMIENTO, ClasificadorMovimiento, SegmentadorLetras, a_isotropicas
from silva.modelo import Mano, Prediccion
from silva.palabras import SEGUNDOS_MAX, ClasificadorPalabras, SegmentadorSenas
from silva.repositorio_historial import RepositorioHistorial

MODO_LETRAS = "letras"
MODO_PALABRAS = "palabras"
# Resolución pedida a la cámara en cada modo. Las palabras usan 16:9 porque muchas cámaras de
# portátil recortan los lados en 4:3 y en este modo hace falta ver hombros y brazos (los videos de
# LSC-54 también son 16:9). Se piden 640×360 y no 1280×720: muchas cámaras web entregan 1280×720 sin
# comprimir a solo 10 cuadros/s (medido: 9,9 fps contra 29,8 fps, con la misma vista), y de todos modos
# la imagen se procesaba a 640 de ancho. Las letras siguen en 4:3, el formato con que se entrenó su modelo.
RESOLUCION = {MODO_LETRAS: (640, 480), MODO_PALABRAS: (640, 360)}
# Si la misma palabra sale dos veces casi seguidas, es casi siempre una seña partida
# en dos (la mano se perdió un instante), no una repetición: se escribe una sola vez.
# Es la pausa entre la palabra escrita y el comienzo de la siguiente seña (antes, 20 cuadros a 30 cuadros/s
# contando el reposo final de la seña, que son 8 cuadros: queda 12 cuadros = 0,4 s).
SEGUNDOS_REPETICION = 0.4
SEGUNDOS_CORRECCION = 3.0  # tras escribir una palabra, durante este tiempo se puede cambiar (1-3) o borrar (X)
SEGUNDOS_SUGERENCIA = 6.0  # un «¿Quiso decir…?» desaparece sin escribir nada tras este tiempo


@dataclass(frozen=True)
class PalabraPendiente:
    """Palabra reconocida con sus opciones, para que alguien pueda corregirla.

    - escrita (`automatica=True`): la seña es segura y ya se escribió; hasta que vence el plazo se
      puede cambiar por otra opción o borrar.
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
    trazando: bool = False  # modo Deletreo: la mano está trazando una letra con movimiento
    # al entrenar (grabar muestras): lo que se guarda
    sena_terminada: np.ndarray | None = None  # Palabras: la seña completa (100 valores por cuadro)
    puntos_mano: np.ndarray | None = None  # Deletreo: la mano en coordenadas isotrópicas
    trazo: tuple | None = None  # Deletreo: (puntos, izquierda) de un trazo terminado

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
        clasificador_movimiento: ClasificadorMovimiento | None = None,
        umbral_movimiento: float = config.UMBRAL_MOVIMIENTO,
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
        self.clasificador_movimiento = clasificador_movimiento
        self.umbral_movimiento = umbral_movimiento
        self.segmentador_letras = SegmentadorLetras()
        self._t_estatica: float | None = None  # cuándo se escribió la última letra estática
        self._t_inicio_trazo: float | None = None
        self.pendiente: PalabraPendiente | None = None
        # Al entrenar (grabar muestras propias) se reconoce igual, para mostrar qué entiende el modelo,
        # pero no se escribe nada ni se guarda una sesión: cada seña o trazo terminado va en el resultado.
        self.entrenando = False
        self._ultima_palabra: str | None = None
        self._t_palabra = float("-inf")  # cuándo se escribió (o sugirió) la última palabra
        self.modo = MODO_LETRAS
        self.activo = False
        self.sesion_id: int | None = None
        self.ultima_confianza: float | None = None
        self._t0 = time.monotonic()
        self._fps = 0.0
        self._t_anterior: float | None = None

    @property
    def letras(self) -> list[str]:
        """Letras que reconoce el modo Deletreo, en orden alfabético."""
        letras = set(getattr(self.clasificador, "letras", []))
        if self.clasificador_movimiento is not None:
            letras |= set(self.clasificador_movimiento.letras)
        return [l for l in config.LETRAS if l in letras]

    @property
    def palabras_disponibles(self) -> bool:
        return self.detector_cuerpo is not None and self.clasificador_palabras is not None

    def cambiar_modo(self, modo: str) -> None:
        if modo == MODO_PALABRAS and not self.palabras_disponibles:
            raise RuntimeError("El modo Palabras no está disponible (falta el modelo)")
        self._cerrar_pendiente()
        self.modo = modo
        self.segmentador.reiniciar()
        self.segmentador_letras.reiniciar()
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
        self.segmentador_letras.reiniciar()
        self._t_estatica = None
        self.pendiente = None
        self.ultima_confianza = None
        self.sesion_id = None if self.entrenando else self.historial.iniciar_sesion()
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
        if self.entrenando:
            return self._letras_al_entrenar(cuadro, mano, prediccion)

        trazo = self._seguir_trazo(mano, cuadro, prediccion)
        if trazo is not None:  # letra con movimiento
            confirmada, prediccion = trazo.letra, trazo
        elif self.segmentador_letras.moviendo:  # mientras traza no se confirman letras estáticas
            self.buffer.pausar()
            confirmada = None
        else:
            confirmada = self.buffer.procesar(prediccion)
            if confirmada is not None:
                self._t_estatica = self._reloj()
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
            trazando=self.segmentador_letras.moviendo,
        )

    def _letras_al_entrenar(self, cuadro: np.ndarray, mano: Mano | None, prediccion: Prediccion | None) -> ResultadoCuadro:
        alto, ancho = cuadro.shape[:2]
        puntos = None
        if mano is not None:
            puntos = a_isotropicas(np.array([(l.x, l.y) for l in mano.landmarks], np.float32), ancho, alto)
        estado = self.segmentador_letras.agregar(puntos, mano.es_izquierda if mano else False)
        if estado.terminado is not None and self.clasificador_movimiento is not None:
            prediccion = self.clasificador_movimiento.predecir(*estado.terminado)
        return ResultadoCuadro(cuadro=cuadro, mano=mano, prediccion=prediccion, letra_confirmada=None,
                               texto=self.buffer.texto, progreso=0.0, fps=self._medir_fps(), brillo=_brillo(cuadro),
                               trazando=self.segmentador_letras.moviendo, puntos_mano=puntos, trazo=estado.terminado)

    def _seguir_trazo(self, mano: Mano | None, cuadro: np.ndarray, estatica: Prediccion | None) -> Prediccion | None:
        """Letras con movimiento: sigue la mano y, al terminar un trazo, lo clasifica.

        Devuelve la letra escrita, o None. Si justo antes del trazo se escribió una letra estática
        (la forma con que empieza, como la I de la J), se reemplaza por la letra con movimiento.
        """
        if self.clasificador_movimiento is None:
            return None
        alto, ancho = cuadro.shape[:2]
        puntos = None
        if mano is not None:
            puntos = a_isotropicas(np.array([(l.x, l.y) for l in mano.landmarks], np.float32), ancho, alto)
        antes = self.segmentador_letras.moviendo
        estado = self.segmentador_letras.agregar(puntos, mano.es_izquierda if mano else False)
        if estado.moviendo and not antes:
            self._t_inicio_trazo = self._reloj()
        if estado.terminado is None:
            return None
        prediccion = self.clasificador_movimiento.predecir(*estado.terminado)
        if prediccion.letra not in LETRAS_MOVIMIENTO or prediccion.confianza < self.umbral_movimiento:
            return None
        if (self._t_estatica is not None and self._t_inicio_trazo is not None
                and self._t_inicio_trazo - self._t_estatica <= config.SEGUNDOS_INICIO_TRAZO
                and self.buffer.ultima not in (None, " ")):
            self.buffer.borrar_ultima()
        self._t_estatica = None
        # la forma con que termina el trazo no debe escribirse como letra estática al sostenerla
        self.buffer.agregar_letra(prediccion.letra, bloquear=estatica.letra if estatica else None)
        return prediccion

    def _procesar_palabras(self, cuadro: np.ndarray, marca_ms: int) -> ResultadoCuadro:
        ahora = self._reloj()
        cuerpo = self.detector_cuerpo.detectar(cuadro, marca_ms)
        estado = self.segmentador.agregar(caracteristicas_cuadro(cuerpo), ahora)
        if self.entrenando:
            terminada = estado.terminada
            return ResultadoCuadro(
                cuadro=cuadro, mano=None,
                prediccion=self.clasificador_palabras.evaluar(terminada).mejor if terminada is not None else None,
                letra_confirmada=None, texto=self.buffer.texto, progreso=min(estado.segundos / SEGUNDOS_MAX, 1.0),
                fps=self._medir_fps(), cuerpo=cuerpo, grabando_sena=estado.grabando, ahora=ahora,
                brillo=_brillo(cuadro), sena_terminada=terminada)
        confirmada = None

        # La pendiente se resuelve al vencer su plazo o cuando empieza una seña nueva
        # (seguir signando = aceptar la provisional e ignorar la sugerencia).
        if self.pendiente is not None and (estado.grabando or ahora >= self.pendiente.vence):
            confirmada = self._cerrar_pendiente()

        prediccion = None
        if estado.terminada is not None:
            evaluacion = self.clasificador_palabras.evaluar(estado.terminada)
            prediccion = evaluacion.mejor
            repetida = (prediccion.letra == self._ultima_palabra and estado.inicio is not None
                        and estado.inicio - self._t_palabra < SEGUNDOS_REPETICION)
            segura = prediccion.confianza >= self.umbral_palabras and prediccion.confianza >= evaluacion.prob_otra
            dudosa = (prediccion.confianza >= self.umbral_sugerencia
                      and prediccion.confianza >= 0.5 * evaluacion.prob_otra)
            if not repetida and (segura or dudosa):
                if self.pendiente is not None:  # caso raro: dos señas sin cuadro intermedio
                    confirmada = self._cerrar_pendiente() or confirmada
                if segura:  # se escribe apenas se reconoce; queda unos segundos para corregirla
                    self._escribir(prediccion)
                    confirmada = prediccion.letra
                plazo = SEGUNDOS_CORRECCION if segura else SEGUNDOS_SUGERENCIA
                self.pendiente = PalabraPendiente(tuple(evaluacion.opciones[:3]), segura, ahora, ahora + plazo)
                self._ultima_palabra = prediccion.letra
                self._t_palabra = ahora

        return ResultadoCuadro(
            cuadro=cuadro,
            mano=None,
            prediccion=prediccion,
            letra_confirmada=confirmada,
            texto=self.buffer.texto,
            progreso=min(estado.segundos / SEGUNDOS_MAX, 1.0),
            fps=self._medir_fps(),
            cuerpo=cuerpo,
            grabando_sena=estado.grabando,
            pendiente=self.pendiente,
            ahora=ahora,
            brillo=_brillo(cuadro),
        )

    # ---------------------------------------------------- corrección (RF-13)
    def confirmar_pendiente(self, opcion: int = 0) -> str | None:
        """Elige una opción (0 = la más probable): en una sugerencia la escribe; en una palabra ya
        escrita, la cambia por esa opción. Devuelve la palabra que queda escrita."""
        if self.pendiente is None or opcion >= len(self.pendiente.opciones):
            return None
        pendiente, elegida = self.pendiente, self.pendiente.opciones[opcion]
        self.pendiente = None
        if pendiente.automatica:
            if opcion == 0:
                return elegida.letra  # era correcta
            self.buffer.borrar_ultima()  # se reemplaza la que se escribió
        self._escribir(elegida)
        return elegida.letra

    def descartar_pendiente(self) -> None:
        """Descarta la sugerencia, o borra la palabra que se acaba de escribir."""
        if self.pendiente is not None:
            if self.pendiente.automatica and self.buffer.ultima == self.pendiente.opciones[0].letra:
                self.buffer.borrar_ultima()
            self._ultima_palabra = None  # permite volver a hacer la misma seña de inmediato
        self.pendiente = None

    def _escribir(self, palabra: Prediccion) -> None:
        self._ultima_palabra = palabra.letra
        self.buffer.agregar_palabra(palabra.letra)
        self.ultima_confianza = palabra.confianza
        self.historial.registrar_letra(self.sesion_id, palabra.letra, palabra.confianza)

    def _cerrar_pendiente(self) -> str | None:
        """Termina el plazo de corrección: la palabra escrita se queda y la sugerencia se descarta."""
        self.pendiente = None
        return None

    def detener(self) -> None:
        """CU-05: primero se guarda el texto y después se libera la cámara (Figura 5)."""
        if not self.activo:
            return
        self._cerrar_pendiente()
        self.activo = False
        if self.sesion_id is not None:
            self.historial.guardar_sesion(self.sesion_id, self.buffer.texto)
        self.captura.liberar()

    def cerrar(self) -> None:
        """Cierre de la aplicación: detener, cerrar historial y liberar recursos."""
        if self.activo:
            self._cerrar_pendiente()
            if self.sesion_id is not None:
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
