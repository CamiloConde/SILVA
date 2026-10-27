"""Extrae de LSC70 las 27 letras (también las que se hacen con movimiento) como secuencias de 6 cuadros.

Fuente: Muñoz Galindez, J. A., Villota Coral, L. V. y Vargas-Cañas, R. (2024). Speak in Colombian
Sign Language: A Dynamic LSC70 Database (V2) [Conjunto de datos]. Mendeley Data.
https://doi.org/10.17632/9ssyn8tff5.2 — Licencia CC BY 4.0.

Cada seña de LSC70AN son 6 imágenes tomadas a lo largo del movimiento. Por cada imagen se guardan
los 21 puntos de la mano en coordenadas de imagen (sin normalizar, para conservar la trayectoria) y
si es la mano izquierda; si hay dos manos, la más alta. Lo usa scripts/entrenar_letras_movimiento.py.

Uso:
    python scripts/preparar_lsc70_secuencias.py [--zip data/externo/lsc70/LSC70.zip]
"""

from __future__ import annotations

import argparse
import os
import zipfile
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from silva import config

ZIP = config.RAIZ_PROYECTO / "data" / "externo" / "lsc70" / "LSC70.zip"
DESTINO = config.DIR_LANDMARKS / "lsc70_secuencias.npz"
CARPETA_LETRA = {"NN": "Ñ"}  # en LSC70 la Ñ se llama NN
_detector = None
_zip = None


def _iniciar(ruta_zip: str) -> None:
    global _detector, _zip
    _detector = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(config.RUTA_MODELO_MANOS)),
        running_mode=vision.RunningMode.IMAGE, num_hands=2,
        min_hand_detection_confidence=config.CONFIANZA_DETECCION,
        min_hand_presence_confidence=config.CONFIANZA_DETECCION))
    _zip = zipfile.ZipFile(ruta_zip)


def _procesar(nombre: str):
    img = cv2.imdecode(np.frombuffer(_zip.read(nombre), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return nombre, None, False, (0, 0)
    r = _detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    if not r.hand_landmarks:
        return nombre, None, False, img.shape[:2]
    i = min(range(len(r.hand_landmarks)), key=lambda k: r.hand_landmarks[k][0].y)  # la mano más alta
    puntos = np.array([(p.x, p.y) for p in r.hand_landmarks[i]], np.float32)
    return nombre, puntos, r.handedness[i][0].index == 1, img.shape[:2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", type=Path, default=ZIP)
    parser.add_argument("--procesos", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    args = parser.parse_args()

    letras = set(config.LETRAS)
    with zipfile.ZipFile(args.zip) as z:
        imagenes = [n for n in z.namelist()
                    if n.startswith("LSC70/LSC70AN/") and n.lower().endswith(".jpg")
                    and CARPETA_LETRA.get(n.split("/")[3], n.split("/")[3]) in letras]
    print(f"{len(imagenes)} imágenes de {len(letras)} letras")

    senas: dict[tuple[str, str], dict[int, tuple]] = defaultdict(dict)
    tamanos = set()
    with Pool(args.procesos, initializer=_iniciar, initargs=(str(args.zip),)) as pool:
        for k, (nombre, puntos, izquierda, tam) in enumerate(pool.imap_unordered(_procesar, imagenes, chunksize=16)):
            _, _, persona, carpeta, archivo = nombre.split("/")
            cuadro = int(Path(archivo).stem.rsplit("_", 1)[1])
            senas[(persona, CARPETA_LETRA.get(carpeta, carpeta))][cuadro] = (puntos, izquierda)
            tamanos.add(tam)
            if k % 2000 == 0:
                print(f"  {k}/{len(imagenes)}")

    claves = sorted(senas)
    puntos = np.full((len(claves), 6, 21, 2), np.nan, np.float32)
    izquierda = np.zeros((len(claves), 6), bool)
    for s, clave in enumerate(claves):
        for c, (p, iz) in senas[clave].items():
            if p is not None and c < 6:
                puntos[s, c], izquierda[s, c] = p, iz
    detectadas = ~np.isnan(puntos[:, :, 0, 0])
    print(f"Tamaños de imagen: {tamanos}")
    print(f"Mano detectada en el {detectadas.mean():.1%} de los cuadros; "
          f"señas con los 6 cuadros: {detectadas.all(axis=1).mean():.1%}")
    np.savez_compressed(DESTINO, puntos=puntos, izquierda=izquierda,
                        letras=np.array([l for _, l in claves]),
                        personas=np.array([f"lsc70/{p}" for p, _ in claves]))
    print(f"{len(claves)} señas -> {DESTINO}")


if __name__ == "__main__":
    main()
