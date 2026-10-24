"""Persistencia local del historial de sesiones en SQLite (RF-07)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from silva import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sesiones (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio  TEXT NOT NULL,
    fin     TEXT,
    texto   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS letras (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id  INTEGER NOT NULL REFERENCES sesiones(id),
    letra      TEXT NOT NULL,
    confianza  REAL NOT NULL,
    momento    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS respuestas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id  INTEGER REFERENCES sesiones(id),
    texto      TEXT NOT NULL,
    momento    TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Sesion:
    id: int
    inicio: str
    fin: str | None
    texto: str


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RepositorioHistorial:
    def __init__(self, ruta: Path | str = config.RUTA_HISTORIAL) -> None:
        if str(ruta) != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        # La interfaz escribe desde el hilo de video y lee desde el de la ventana; los accesos
        # se serializan con el candado de VentanaPrincipal, por eso se permite compartir la conexión.
        self._con = sqlite3.connect(str(ruta), check_same_thread=False)
        self._con.executescript(ESQUEMA)

    def iniciar_sesion(self) -> int:
        cur = self._con.execute("INSERT INTO sesiones (inicio) VALUES (?)", (_ahora(),))
        self._con.commit()
        return cur.lastrowid

    def registrar_letra(self, sesion_id: int, letra: str, confianza: float) -> None:
        self._con.execute(
            "INSERT INTO letras (sesion_id, letra, confianza, momento) VALUES (?, ?, ?, ?)",
            (sesion_id, letra, confianza, _ahora()),
        )
        self._con.commit()

    def guardar_sesion(self, sesion_id: int, texto: str) -> None:
        self._con.execute(
            "UPDATE sesiones SET texto = ?, fin = ? WHERE id = ?", (texto, _ahora(), sesion_id)
        )
        self._con.commit()

    def registrar_respuesta(self, sesion_id: int | None, texto: str) -> None:
        """RF-09: respuesta escrita por la persona oyente (sesion_id None si la cámara estaba apagada)."""
        self._con.execute(
            "INSERT INTO respuestas (sesion_id, texto, momento) VALUES (?, ?, ?)", (sesion_id, texto, _ahora())
        )
        self._con.commit()

    def listar_respuestas(self, limite: int = 50) -> list[tuple[str, str, int | None]]:
        """(momento, texto, sesion_id) de las respuestas más recientes."""
        return self._con.execute(
            "SELECT momento, texto, sesion_id FROM respuestas ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()

    def listar_sesiones(self, limite: int = 50) -> list[Sesion]:
        filas = self._con.execute(
            "SELECT id, inicio, fin, texto FROM sesiones ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
        return [Sesion(*f) for f in filas]

    def letras_de_sesion(self, sesion_id: int) -> list[tuple[str, float]]:
        return self._con.execute(
            "SELECT letra, confianza FROM letras WHERE sesion_id = ? ORDER BY id", (sesion_id,)
        ).fetchall()

    def cerrar(self) -> None:
        self._con.close()
