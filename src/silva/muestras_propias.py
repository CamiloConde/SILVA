"""Muestras propias grabadas con la app del teléfono (sección «Entrenar»).

La app exporta un .jsonl.gz: una primera línea que describe el archivo y luego una muestra por línea, con
solo los puntos que detectó MediaPipe (nunca la imagen):

- palabra: la seña completa como la cortó el segmentador en vivo, 100 valores por cuadro (cuerpo.py).
- letra: una letra quieta sostenida, los 42 valores por cuadro que recibe el modelo de letras, y la mano
  en coordenadas isotrópicas (letras_movimiento.a_isotropicas).
- trazo: una letra con movimiento, la mano en coordenadas isotrópicas en cada cuadro del trazo.

`reunir` las convierte al formato de cada entrenamiento:

- data/landmarks/propias_letras.npz (X, y, grupos): entrenar_modelo.py lo carga junto a los demás
  (grupo "propias/<persona>").
- data/landmarks/propias_secuencias.npz (secuencias, etiquetas, firmantes "P-<persona>"): entrenar_palabras.py.
- data/landmarks/propias_trazos.npz (puntos, izquierda, letras, personas): entrenar_letras_movimiento.py.
  Las letras quietas también entran aquí (6 cuadros de la toma): el modelo de trazos aprende a no
  confundirlas con una letra con movimiento.

Cada archivo guarda además `tomas`: un identificador por muestra, para medir con tomas no vistas.
"""
from __future__ import annotations

import gzip
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

from silva import config
from silva.letras_movimiento import CUADROS, remuestrear
from silva.palabras import SEGUNDOS_MAX

FORMATO = "silva-muestras"
# Desde el código, todo queda en el proyecto (data/propias y data/landmarks); en el ejecutable, en la carpeta del
# usuario (%LOCALAPPDATA%/SILVA), donde siempre se puede escribir.
if config.EMPAQUETADO:
    DIR_PROPIAS = config.DIR_DATOS_USUARIO / "muestras"
    _DIR_NPZ = config.DIR_DATOS_USUARIO / "propias"
else:
    DIR_PROPIAS = config.RAIZ_PROYECTO / "data" / "propias"
    _DIR_NPZ = config.DIR_LANDMARKS
RUTA_LETRAS = _DIR_NPZ / "propias_letras.npz"
RUTA_SECUENCIAS = _DIR_NPZ / "propias_secuencias.npz"
RUTA_TRAZOS = _DIR_NPZ / "propias_trazos.npz"
DIR_GRABACIONES = DIR_PROPIAS  # donde graba la app de PC (Entrenar)
# Una seña que llegó al máximo del segmentador (4 s) no tiene un final claro: trae movimiento de más
FRACCION_LIMITE = 0.97


def archivos(carpeta: Path = DIR_PROPIAS) -> list[Path]:
    """Archivos de muestras: los exportados por el teléfono (.jsonl.gz) y los grabados en el PC (.jsonl)."""
    return sorted([*carpeta.glob("*.jsonl.gz"), *carpeta.glob("*.jsonl")])


def persona_id(nombre: str) -> str:
    """«Camilo Andrés» → «camilo_andres»: sin tildes ni espacios, para usarlo como grupo."""
    s = unicodedata.normalize("NFKD", nombre.strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "sin_nombre"


def leer(ruta: Path) -> list[dict]:
    """Las muestras de un archivo exportado por la app."""
    abrir = gzip.open if ruta.suffix == ".gz" else open
    with abrir(ruta, "rt", encoding="utf-8") as f:
        lineas = [l for l in f if l.strip()]
    if not lineas:
        raise ValueError(f"{ruta.name}: el archivo está vacío")
    cabecera = json.loads(lineas[0])
    if cabecera.get("formato") != FORMATO:
        raise ValueError(f"{ruta.name}: no es un archivo de muestras de SILVA")
    return [json.loads(l) for l in lineas[1:]]


def reunir(muestras: list[dict], vocabulario: set[str]) -> dict:
    """Separa las muestras por modelo, quita repetidas (el mismo archivo importado dos veces) y las que no
    corresponden a ninguna clase. `vocabulario` = claves de las palabras (entrenar_palabras.NOMBRES)."""
    letras = {"X": [], "y": [], "grupos": [], "tomas": []}
    secuencias = {"secuencias": [], "etiquetas": [], "firmantes": [], "tomas": []}
    trazos = {"puntos": [], "izquierda": [], "letras": [], "personas": [], "tomas": []}
    vistas, omitidas = set(), []
    for m in muestras:
        tipo, clave, persona = m.get("tipo"), str(m.get("clave", "")), persona_id(str(m.get("persona", "")))
        firma = (tipo, clave, persona, m.get("fecha"), len(m.get("cuadros") or m.get("puntos") or []))
        if firma in vistas:
            continue
        vistas.add(firma)
        toma = f"{persona}/{len(vistas)}"
        if tipo == "palabra" and clave in vocabulario:
            cuadros = np.asarray(m["cuadros"], np.float32)
            if cuadros.ndim != 2 or cuadros.shape[1] != 100:
                omitidas.append((tipo, clave, "forma inválida"))
                continue
            fps = m.get("fps")
            if fps and len(cuadros) >= FRACCION_LIMITE * SEGUNDOS_MAX * float(fps):
                omitidas.append((tipo, clave, "llegó al límite de 4 s: no se vio el final de la seña"))
                continue
            secuencias["secuencias"].append(cuadros)
            secuencias["etiquetas"].append(clave)
            secuencias["firmantes"].append(f"P-{persona}")
            secuencias["tomas"].append(toma)
        elif tipo == "letra" and clave in config.LETRAS_ESTATICAS:
            cuadros = np.asarray(m["cuadros"], np.float32)
            puntos = np.asarray(m["puntos"], np.float32)
            letras["X"].extend(cuadros)
            letras["y"].extend([clave] * len(cuadros))
            letras["grupos"].extend([f"propias/{persona}"] * len(cuadros))
            letras["tomas"].extend([toma] * len(cuadros))
            seis = puntos[np.linspace(0, len(puntos) - 1, CUADROS).round().astype(int)]
            trazos["puntos"].append(seis)
            trazos["izquierda"].append(bool(m.get("izquierda", False)))
            trazos["letras"].append(clave)
            trazos["personas"].append(f"propias/{persona}")
            trazos["tomas"].append(toma)
        elif tipo == "trazo" and clave in config.LETRAS:
            puntos = np.asarray(m["puntos"], np.float32)
            if len(puntos) < 2:
                omitidas.append((tipo, clave, "trazo demasiado corto"))
                continue
            trazos["puntos"].append(remuestrear(puntos, CUADROS))
            trazos["izquierda"].append(bool(m.get("izquierda", False)))
            trazos["letras"].append(clave)
            trazos["personas"].append(f"propias/{persona}")
            trazos["tomas"].append(toma)
        else:
            omitidas.append((tipo, clave, "no es una clase del modelo"))
    return {"letras": letras, "secuencias": secuencias, "trazos": trazos, "omitidas": omitidas}


def guardar(datos: dict) -> dict[str, int]:
    """Escribe los tres .npz (o borra el de un modelo sin muestras). Devuelve cuántas muestras tiene cada uno."""
    cuentas = {}
    _DIR_NPZ.mkdir(parents=True, exist_ok=True)  # en el ejecutable es la carpeta del usuario, que puede no existir
    l, s, t = datos["letras"], datos["secuencias"], datos["trazos"]
    if l["X"]:
        np.savez_compressed(RUTA_LETRAS, X=np.array(l["X"], np.float32), y=np.array(l["y"]),
                            grupos=np.array(l["grupos"]), tomas=np.array(l["tomas"]))
    else:
        RUTA_LETRAS.unlink(missing_ok=True)
    if s["secuencias"]:
        sec = np.empty(len(s["secuencias"]), dtype=object)
        sec[:] = s["secuencias"]
        np.savez_compressed(RUTA_SECUENCIAS, secuencias=sec, etiquetas=np.array(s["etiquetas"]),
                            firmantes=np.array(s["firmantes"]), tomas=np.array(s["tomas"]))
    else:
        RUTA_SECUENCIAS.unlink(missing_ok=True)
    if t["puntos"]:
        np.savez_compressed(RUTA_TRAZOS, puntos=np.array(t["puntos"], np.float32), izquierda=np.array(t["izquierda"]),
                            letras=np.array(t["letras"]), personas=np.array(t["personas"]), tomas=np.array(t["tomas"]))
    else:
        RUTA_TRAZOS.unlink(missing_ok=True)
    cuentas["letras (tomas)"] = len(set(l["tomas"]))
    cuentas["palabras"] = len(s["secuencias"])
    cuentas["trazos"] = sum(letra in config.LETRAS and letra not in config.LETRAS_ESTATICAS for letra in t["letras"])
    return cuentas


def _redondear(valores) -> list:
    return np.round(np.nan_to_num(np.asarray(valores, np.float32)), 4).tolist()


class GrabadorMuestras:
    """Guarda muestras desde la app de PC (VentanaEntrenar) con el mismo formato que la app del teléfono:
    un .jsonl por sesión de grabación, en DIR_GRABACIONES."""

    def __init__(self, carpeta: Path | None = None) -> None:
        self.carpeta = carpeta or DIR_GRABACIONES
        self.archivo: Path | None = None  # se crea con la primera muestra
        self._conteo: Counter = Counter()
        self._lineas_propias: list[tuple[str, str]] = []  # (tipo, clave) de lo grabado en esta sesión
        if self.carpeta.exists():
            for a in archivos(self.carpeta):
                try:
                    self._conteo.update((m.get("tipo"), str(m.get("clave"))) for m in leer(a))
                except (ValueError, OSError, json.JSONDecodeError):
                    continue

    def cuantas(self, tipo: str, clave: str) -> int:
        return self._conteo[(tipo, clave)]

    @property
    def total(self) -> int:
        return sum(self._conteo.values())

    def _escribir(self, muestra: dict) -> None:
        if self.archivo is None:
            self.carpeta.mkdir(parents=True, exist_ok=True)
            self.archivo = self.carpeta / f"silva_muestras_pc_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
            cabecera = {"formato": FORMATO, "version": 1, "app": "pc", "exportado": f"{datetime.now():%Y-%m-%d %H:%M:%S}"}
            self.archivo.write_text(json.dumps(cabecera) + "\n", encoding="utf-8")
        with self.archivo.open("a", encoding="utf-8") as f:
            f.write(json.dumps(muestra, ensure_ascii=False) + "\n")
        self._conteo[(muestra["tipo"], muestra["clave"])] += 1
        self._lineas_propias.append((muestra["tipo"], muestra["clave"]))

    def _inicio(self, tipo: str, clave: str, persona: str) -> dict:
        return {"tipo": tipo, "clave": clave, "persona": persona, "fecha": f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}"}

    def palabra(self, clave: str, persona: str, cuadros: np.ndarray, fps: float) -> bool:
        """Guarda la seña; devuelve False (y no la guarda) si llegó al límite de 4 s: no se vio su final."""
        if len(cuadros) >= FRACCION_LIMITE * SEGUNDOS_MAX * fps:
            return False
        self._escribir({**self._inicio("palabra", clave, persona), "cuadros": _redondear(cuadros), "fps": round(fps, 1)})
        return True

    def letra(self, clave: str, persona: str, cuadros: list, puntos: list, izquierda: bool) -> None:
        self._escribir({**self._inicio("letra", clave, persona), "cuadros": _redondear(cuadros),
                        "puntos": _redondear(puntos), "izquierda": bool(izquierda)})

    def trazo(self, clave: str, persona: str, puntos: np.ndarray, izquierda: bool) -> None:
        self._escribir({**self._inicio("trazo", clave, persona), "puntos": _redondear(puntos), "izquierda": bool(izquierda)})

    def borrar_ultima(self) -> tuple[str, str] | None:
        """Borra la última muestra grabada en esta sesión (las de antes no se tocan)."""
        if not self._lineas_propias or self.archivo is None:
            return None
        lineas = [l for l in self.archivo.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.archivo.write_text("\n".join(lineas[:-1]) + "\n", encoding="utf-8")
        tipo, clave = self._lineas_propias.pop()
        self._conteo[(tipo, clave)] -= 1
        return tipo, clave

