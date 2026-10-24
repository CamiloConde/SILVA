"""Convierte el dataset externo de LSC (secuencias) en muestras estáticas por cuadro.

Fuente: JuanPlazas (2026), deteccion_letras_senas — https://github.com/JuanPlazas/deteccion_letras_senas
Cada secuencia (30 cuadros x 42 valores) aporta 30 muestras de la letra, ya
normalizadas igual que en silva.detector_manos.normalizar_landmarks.

Uso:
    python scripts/preparar_dataset.py [--origen RUTA]
"""

from __future__ import annotations

import argparse
import subprocess
import unicodedata
from pathlib import Path

import numpy as np

from silva import config

REPO_EXTERNO = "https://github.com/JuanPlazas/deteccion_letras_senas"
ORIGEN_POR_DEFECTO = config.RAIZ_PROYECTO / "data" / "externo" / "deteccion_letras_senas"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--origen", type=Path, default=ORIGEN_POR_DEFECTO)
    args = parser.parse_args()

    if not args.origen.exists():
        print(f"Descargando el dataset externo en {args.origen} ...")
        subprocess.run(["git", "clone", "--depth", "1", REPO_EXTERNO, str(args.origen)], check=True)

    dir_secuencias = args.origen / "data" / "sequences"
    X, y, grupos = [], [], []
    for carpeta in sorted(dir_secuencias.iterdir()):
        letra = unicodedata.normalize("NFC", carpeta.name)
        if letra not in config.LETRAS_ESTATICAS:
            continue
        for archivo in sorted(carpeta.glob("*.npy")):
            secuencia = np.load(archivo)
            if secuencia.shape[1] != config.NUM_CARACTERISTICAS:
                raise ValueError(f"{archivo}: forma inesperada {secuencia.shape}")
            cuadros = secuencia[np.abs(secuencia).sum(axis=1) > 0]  # descarta cuadros sin mano
            X.append(cuadros)
            y += [letra] * len(cuadros)
            grupos += [f"externo/{archivo.stem}"] * len(cuadros)

    X = np.concatenate(X).astype(np.float32)
    destino = config.DIR_LANDMARKS / "externo_juanplazas.npz"
    destino.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destino, X=X, y=np.array(y), grupos=np.array(grupos))
    print(f"{len(X)} muestras de {len(set(y))} letras ({len(set(grupos))} secuencias) -> {destino}")


if __name__ == "__main__":
    main()
