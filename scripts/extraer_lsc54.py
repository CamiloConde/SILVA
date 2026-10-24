"""Extrae las secuencias de características (cuerpo + manos) de los videos de LSC-54.

Fuente: Mora-Zarate, J. E. (2025). A dataset representing the movements that a
person must perform to produce a sign (V4) [Conjunto de datos]. Science Data
Bank. https://doi.org/10.57760/sciencedb.25639 — Licencia CC BY-NC 4.0.

Se procesan los videos originales (no el datos.json de 51 GB, que repite cada
video 45 veces desplazado) con el mismo detector que usa la app en vivo, para
que entrenamiento e inferencia vean exactamente las mismas características.

Uso:
    python scripts/extraer_lsc54.py [--zips data/externo/lsc54] [--procesos 12]
"""

from __future__ import annotations

import argparse
import os
import tempfile
import time
import unicodedata
import zipfile
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np

from silva import config
from silva.cuerpo import N_CARACTERISTICAS_CUADRO, DetectorCuerpo, caracteristicas_cuadro

DIR_ZIPS = config.RAIZ_PROYECTO / "data" / "externo" / "lsc54"
DESTINO = config.DIR_LANDMARKS / "lsc54_secuencias.npz"

_detector: DetectorCuerpo | None = None


def _iniciar_trabajador() -> None:
    global _detector
    _detector = DetectorCuerpo()


def _procesar(tarea: tuple[str, str]) -> tuple[str, np.ndarray]:
    ruta_zip, nombre = tarea
    with zipfile.ZipFile(ruta_zip) as z, tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp:
        tmp.write(z.read(nombre))
    try:
        cap = cv2.VideoCapture(tmp.name)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        filas, i = [], 0
        while True:
            ok, cuadro = cap.read()
            if not ok:
                break
            # Marcas de tiempo propias por video: el detector en modo VIDEO solo exige que crezcan.
            c = _detector.detectar(cuadro, _detector._ultimo_ms + 1 + int(1000 / fps))
            v = caracteristicas_cuadro(c)
            filas.append(v if v is not None else np.full(N_CARACTERISTICAS_CUADRO, np.nan, np.float32))
            i += 1
        cap.release()
    finally:
        os.unlink(tmp.name)
    return nombre, np.array(filas, dtype=np.float32).reshape(-1, N_CARACTERISTICAS_CUADRO)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zips", type=Path, default=DIR_ZIPS)
    parser.add_argument("--procesos", type=int, default=max(1, (os.cpu_count() or 2) - 4))
    args = parser.parse_args()

    tareas = []
    for ruta_zip in sorted(args.zips.glob("*.zip")):
        with zipfile.ZipFile(ruta_zip) as z:
            tareas += [(str(ruta_zip), n) for n in z.namelist() if n.lower().endswith((".avi", ".mp4"))]
    print(f"{len(tareas)} videos, {args.procesos} procesos")

    secuencias, etiquetas, firmantes, categorias, nombres = [], [], [], [], []
    t0 = time.time()
    with Pool(args.procesos, initializer=_iniciar_trabajador) as pool:
        for k, (nombre, seq) in enumerate(pool.imap_unordered(_procesar, tareas, chunksize=4), 1):
            partes = unicodedata.normalize("NFC", nombre).split("/")  # Videos X/<firmante>/<categoría>/<seña>/<n>.avi
            secuencias.append(seq)
            firmantes.append(partes[1])
            categorias.append(partes[2])
            etiquetas.append(partes[3])
            nombres.append(nombre)
            if k % 100 == 0:
                print(f"  {k}/{len(tareas)}  ({time.time() - t0:.0f} s)", flush=True)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        DESTINO,
        secuencias=np.array(secuencias, dtype=object),
        etiquetas=np.array(etiquetas),
        firmantes=np.array(firmantes),
        categorias=np.array(categorias),
        nombres=np.array(nombres),
    )
    print(f"{len(secuencias)} secuencias de {len(set(etiquetas))} señas y {len(set(firmantes))} firmantes "
          f"-> {DESTINO} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
