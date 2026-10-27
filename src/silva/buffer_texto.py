"""Texto acumulado de la sesión y regla de confirmación de letras (RF-04)."""

from __future__ import annotations

from silva import config
from silva.modelo import Prediccion


class BufferTexto:
    """Acumula letras confirmadas.

    Una predicción solo se confirma si su confianza es >= `umbral` y la misma
    letra se repite en `cuadros_estables` cuadros consecutivos. Después de
    confirmar, la misma letra no se vuelve a agregar mientras se mantenga la
    seña: hay que cambiar de letra o retirar la mano (p. ej. para escribir "LL").
    """

    def __init__(
        self,
        umbral: float = config.UMBRAL_CONFIANZA,
        cuadros_estables: int = config.CUADROS_ESTABLES,
    ) -> None:
        self.umbral = umbral
        self.cuadros_estables = cuadros_estables
        self._texto: list[str] = []
        self._candidata: str | None = None
        self._racha = 0
        self._bloqueada: str | None = None

    @property
    def texto(self) -> str:
        return "".join(self._texto)

    @property
    def progreso(self) -> float:
        """Avance (0-1) de la letra candidata hacia su confirmación."""
        return min(self._racha / self.cuadros_estables, 1.0)

    def procesar(self, prediccion: Prediccion | None) -> str | None:
        """Registra la predicción de un cuadro. Devuelve la letra si quedó confirmada."""
        if prediccion is None:  # sin mano: se reinicia todo
            self._reiniciar_racha()
            self._bloqueada = None
            return None

        if prediccion.confianza < self.umbral:
            self._reiniciar_racha()
            return None

        if prediccion.letra == self._candidata:
            self._racha += 1
        else:
            self._candidata = prediccion.letra
            self._racha = 1
            if prediccion.letra != self._bloqueada:
                self._bloqueada = None

        if self._racha >= self.cuadros_estables and prediccion.letra != self._bloqueada:
            self._texto.append(prediccion.letra)
            self._bloqueada = prediccion.letra
            return prediccion.letra
        return None

    @property
    def ultima(self) -> str | None:
        return self._texto[-1] if self._texto else None

    def pausar(self) -> None:
        """Interrumpe la letra en curso sin olvidar la bloqueada (p. ej. mientras la mano traza una letra)."""
        self._reiniciar_racha()

    def agregar_letra(self, letra: str, bloquear: str | None = None) -> None:
        """Letra con movimiento, ya reconocida. `bloquear`: letra estática que no debe escribirse
        mientras se sostenga la mano tal como terminó el trazo."""
        self._texto.append(letra)
        self._reiniciar_racha()
        self._bloqueada = bloquear

    @property
    def palabra_en_curso(self) -> str:
        """Lo escrito después del último espacio (en Deletreo, las letras de la palabra que se deletrea)."""
        partes = []
        for p in reversed(self._texto):
            if p == " ":
                break
            partes.append(p)
        return "".join(reversed(partes))

    def completar(self, palabra: str) -> None:
        """«¿Quisiste decir?»: cambia la palabra en curso por `palabra` (letra por letra) y agrega un espacio."""
        while self._texto and self._texto[-1] != " ":
            self._texto.pop()
        self._texto.extend(palabra)
        self._texto.append(" ")
        self._reiniciar_racha()
        self._bloqueada = None

    def agregar_palabra(self, palabra: str) -> None:
        """Modo Palabras: agrega la palabra completa como una unidad (Borrar la quita entera)."""
        if self._texto and self._texto[-1] != " ":
            self._texto.append(" ")
        self._texto.append(palabra)

    def reiniciar_deteccion(self) -> None:
        """Olvida la letra en curso sin tocar el texto (p. ej. al cambiar de modo)."""
        self._reiniciar_racha()
        self._bloqueada = None

    def agregar_espacio(self) -> None:
        if self._texto and self._texto[-1] != " ":
            self._texto.append(" ")

    def borrar_ultima(self) -> None:
        if self._texto:
            self._texto.pop()

    def limpiar(self) -> None:
        self._texto.clear()
        self._reiniciar_racha()
        self._bloqueada = None

    def _reiniciar_racha(self) -> None:
        self._candidata = None
        self._racha = 0
