"""Genera modelos/animaciones_senas.npz: una animación de esqueleto por cada palabra del vocabulario.

Para cada seña se elige, entre las grabaciones de LSC-54 (Mora-Zarate, 2025; CC BY-NC 4.0), la que
el modelo de palabras reconoce con más confianza (suele ser la más clara), se recorta al tramo de la
seña, se rellenan los cuadros donde se perdió la mano y se remuestrea a una duración fija. Se guardan
solo los puntos (pose + manos, en anchos de hombro respecto al centro de los hombros), no video.

Uso:
    python scripts/generar_animaciones.py
"""

from __future__ import annotations

import sys

import numpy as np

from silva import config
from silva.palabras import ClasificadorPalabras, rellenar_manos, recortar_activo, remuestrear

sys.path.insert(0, str(config.RAIZ_PROYECTO / "scripts"))
from entrenar_palabras import NOMBRES, nombre_visible  # noqa: E402

DESTINO = config.DIR_MODELOS / "animaciones_senas.npz"
CUADROS = 45  # ~1,5 s a 30 cuadros/s


def main() -> None:
    clasificador = ClasificadorPalabras()
    d = np.load(config.DIR_LANDMARKS / "lsc54_secuencias.npz", allow_pickle=True)
    m = d["categorias"] == "Cordialidad"
    nombres, animaciones = [], []
    for clave in sorted(NOMBRES):
        visible = nombre_visible(clave)
        mejor, mejor_conf = None, -1.0
        for s in d["secuencias"][m][d["etiquetas"][m] == clave]:
            tramo = recortar_activo(s)
            if tramo is None:
                continue
            # la mano debe verse en buena parte de la seña para que la animación se entienda
            presencia = np.maximum(tramo[:, 14 + 42], tramo[:, 14 + 43 + 42]).mean()
            if presencia < 0.6:
                continue
            ev = clasificador.evaluar(tramo)
            conf = next((o.confianza for o in ev.opciones if o.letra == visible), 0.0)
            if conf > mejor_conf:
                mejor, mejor_conf = tramo, conf
        if mejor is None:
            print(f"  {visible}: sin una grabación clara, se omite")
            continue
        animaciones.append(remuestrear(rellenar_manos(mejor), CUADROS).astype(np.float32))
        nombres.append(visible)
        print(f"  {visible}: confianza del modelo {mejor_conf:.0%}")
    np.savez_compressed(DESTINO, nombres=np.array(nombres), animaciones=np.stack(animaciones))
    print(f"{len(nombres)} animaciones -> {DESTINO} ({DESTINO.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
