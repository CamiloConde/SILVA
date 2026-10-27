"""«¿Quisiste decir?» del modo Deletreo: palabras frecuentes del español que empiezan como la que se deletrea.

Deletrear es lento; con las primeras letras (HOLA MUN…) se ofrecen las palabras más frecuentes que
empiezan así (MUNDO, MUNDIAL…) y un clic las completa. La lista (recursos/palabras_es.txt) son las
20 000 palabras más frecuentes de subtítulos en español, de FrequencyWords (CC BY-SA 4.0).
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from silva import config


def _base(texto: str) -> str:
    """Mayúsculas sin tildes (la Ñ se conserva): así se compara con lo deletreado."""
    salida = []
    for c in unicodedata.normalize("NFD", texto.upper()):
        if unicodedata.category(c) == "Mn":
            if c == "̃" and salida and salida[-1] == "N":
                salida[-1] = "Ñ"
            continue
        salida.append(c)
    return "".join(salida)


class Sugerencias:
    def __init__(self, ruta: Path = config.RUTA_PALABRAS_ES) -> None:
        self._palabras: list[tuple[str, str]] = []  # (base sin tildes, palabra en mayúsculas), por frecuencia
        if ruta.exists():
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                if linea and not linea.startswith("#"):
                    self._palabras.append((_base(linea), linea.upper()))

    def para(self, texto: str, n: int = 3) -> list[str]:
        """Hasta n palabras frecuentes que completan la última palabra del texto (desde 2 letras)."""
        partes = texto.rstrip("▏").split(" ")
        en_curso = _base(partes[-1]) if partes else ""
        if len(en_curso) < 2 or not en_curso.isalpha():
            return []
        salida = []
        for base, palabra in self._palabras:
            if len(base) > len(en_curso) and base.startswith(en_curso) and palabra not in salida:
                salida.append(palabra)
                if len(salida) == n:
                    break
        return salida
