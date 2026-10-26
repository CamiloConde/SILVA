"""Extrae las letras estáticas de LSC70 (70 personas) como muestras para el modelo de letras.

Fuente: Muñoz Galindez, J. A., Villota Coral, L. V. y Vargas-Cañas, R. (2024). Speak in Colombian
Sign Language: A Dynamic LSC70 Database (V2) [Conjunto de datos]. Mendeley Data.
https://doi.org/10.17632/9ssyn8tff5.2 — Licencia CC BY 4.0.

Cada seña tiene 6 imágenes de 640×480 (LSC70AN). Se detecta la mano con el mismo modelo y la misma
normalización que usa la app (silva.detector_manos.normalizar_landmarks); si hay dos manos, se toma
la más alta (la que hace la seña). Cada persona es un grupo, para evaluar con personas no vistas.

Uso:
    python scripts/preparar_lsc70.py [--zip data/externo/lsc70/LSC70.zip]
"""

from __future__ import annotations

import argparse
import os
import zipfile
from multiprocessing import Pool
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from silva import config
from silva.detector_manos import normalizar_landmarks
from silva.modelo import Landmark

ZIP = config.RAIZ_PROYECTO / "data" / "externo" / "lsc70" / "LSC70.zip"
DESTINO = config.DIR_LANDMARKS / "lsc70_letras.npz"
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
    datos = np.frombuffer(_zip.read(nombre), np.uint8)
    img = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if img is None:
        return nombre, None
    r = _detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    if not r.hand_landmarks:
        return nombre, None
    i = min(range(len(r.hand_landmarks)), key=lambda k: r.hand_landmarks[k][0].y)  # la mano más alta
    landmarks = [Landmark(p.x, p.y) for p in r.hand_landmarks[i]]
    es_izquierda = r.handedness[i][0].index == 1
    return nombre, normalizar_landmarks(landmarks, es_izquierda)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", type=Path, default=ZIP)
    parser.add_argument("--procesos", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    args = parser.parse_args()

    with zipfile.ZipFile(args.zip) as z:
        imagenes = [n for n in z.namelist()
                    if n.startswith("LSC70/LSC70AN/") and n.lower().endswith(".jpg")
                    and n.split("/")[3] in config.LETRAS_ESTATICAS]
    print(f"{len(imagenes)} imágenes de letras estáticas")

    X, y, grupos, perdidas = [], [], [], 0
    with Pool(args.procesos, initializer=_iniciar, initargs=(str(args.zip),)) as pool:
        for nombre, vector in pool.imap_unordered(_procesar, imagenes, chunksize=16):
            if vector is None:
                perdidas += 1
                continue
            _, _, persona, letra, _ = nombre.split("/")
            X.append(vector)
            y.append(letra)
            grupos.append(f"lsc70/{persona}")
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(DESTINO, X=np.array(X, np.float32), y=np.array(y), grupos=np.array(grupos))
    print(f"{len(X)} muestras de {len(set(y))} letras y {len(set(grupos))} personas "
          f"(sin mano detectada: {perdidas}) -> {DESTINO}")


if __name__ == "__main__":
    main()
