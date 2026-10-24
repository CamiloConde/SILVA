"""Captura muestras propias de landmarks con la cámara web.

Controles (en la ventana de video):
    Letra (A, B, C...)  elige la letra a grabar (solo letras estáticas)
    ESPACIO             inicia/detiene una ráfaga de grabación (máx. --por-rafaga muestras)
    ESC                 guarda y sale

Cada ráfaga se guarda como un grupo distinto, para que la evaluación separe
ráfagas completas entre entrenamiento y prueba. Las muestras quedan en
data/landmarks/propio_<persona>_<fecha>.npz y entrenar_modelo.py las usa automáticamente.

Uso:
    python scripts/capturar_dataset.py --persona camilo
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

import cv2
import numpy as np

from silva import config
from silva.captura_video import CapturaVideo
from silva.detector_manos import DetectorManos, dibujar_mano


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--persona", required=True, help="nombre corto de quien graba (sin espacios)")
    parser.add_argument("--por-rafaga", type=int, default=60)
    args = parser.parse_args()

    captura = CapturaVideo()
    captura.abrir()
    detector = DetectorManos()
    t0 = time.monotonic()

    X, y, grupos = [], [], []
    letra, grabando, en_rafaga, n_rafaga = config.LETRAS_ESTATICAS[0], False, 0, 0
    conteo = {l: 0 for l in config.LETRAS_ESTATICAS}
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        while True:
            cuadro = captura.leer_cuadro()
            if cuadro is None:
                break
            mano = detector.detectar(cuadro, int((time.monotonic() - t0) * 1000))
            if mano is not None:
                dibujar_mano(cuadro, mano)
                if grabando:
                    X.append(mano.caracteristicas)
                    y.append(letra)
                    grupos.append(f"{args.persona}/{sello}/{n_rafaga}")
                    conteo[letra] += 1
                    en_rafaga += 1
                    if en_rafaga >= args.por_rafaga:
                        grabando = False

            vista = cv2.flip(cuadro, 1)
            color = (0, 0, 255) if grabando else (255, 255, 255)
            estado = f"GRABANDO {en_rafaga}/{args.por_rafaga}" if grabando else "ESPACIO para grabar"
            cv2.putText(vista, f"Letra: {letra}  ({conteo[letra]} muestras)", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(vista, estado, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            if mano is None:
                cv2.putText(vista, "No se detecta la mano", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            cv2.imshow("SILVA - captura de dataset (ESC para guardar y salir)", vista)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == 27:
                break
            if tecla == 32:
                grabando = not grabando
                if grabando:
                    en_rafaga, n_rafaga = 0, n_rafaga + 1
            elif chr(tecla).upper() in config.LETRAS_ESTATICAS and not grabando:
                letra = chr(tecla).upper()
    finally:
        captura.liberar()
        detector.cerrar()
        cv2.destroyAllWindows()

    if not X:
        print("No se grabaron muestras.")
        return
    destino = config.DIR_LANDMARKS / f"propio_{args.persona}_{sello}.npz"
    destino.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destino, X=np.array(X, dtype=np.float32), y=np.array(y), grupos=np.array(grupos))
    print(f"{len(X)} muestras guardadas en {destino}")
    for l, n in conteo.items():
        if n:
            print(f"  {l}: {n}")


if __name__ == "__main__":
    main()
