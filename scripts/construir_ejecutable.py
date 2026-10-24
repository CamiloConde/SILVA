"""Construye el ejecutable de Windows y el .zip listo para publicar como Release.

Pasos: PyInstaller (empaquetado/silva.spec) → copia LEEME.txt y TERCEROS.md →
autoverificación del ejecutable (--verificar) → dist/SILVA-v<versión>-windows.zip

Uso:
    python scripts/construir_ejecutable.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from silva import __version__

RAIZ = Path(__file__).resolve().parents[1]
DIST = RAIZ / "dist"
CARPETA = DIST / "SILVA"


def main() -> None:
    print(f"Construyendo SILVA {__version__}…")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST),
         "--workpath", str(RAIZ / "build"), str(RAIZ / "empaquetado" / "silva.spec")],
        check=True,
    )
    leeme = (RAIZ / "empaquetado" / "LEEME.txt").read_text(encoding="utf-8").replace("{version}", __version__)
    (CARPETA / "LEEME.txt").write_text(leeme, encoding="utf-8")
    shutil.copy(RAIZ / "TERCEROS.md", CARPETA / "TERCEROS.md")

    # El ejecutable debe poder cargar todos los modelos por sí solo
    informe = Path(tempfile.gettempdir()) / "silva_verificacion_build.txt"
    resultado = subprocess.run([str(CARPETA / "SILVA.exe"), "--verificar", str(informe)], timeout=180)
    print(informe.read_text(encoding="utf-8"))
    if resultado.returncode != 0:
        raise SystemExit("La autoverificación del ejecutable falló; no se genera el .zip")

    destino = DIST / f"SILVA-v{__version__}-windows.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for ruta in CARPETA.rglob("*"):
            z.write(ruta, Path("SILVA") / ruta.relative_to(CARPETA))
    tam_carpeta = sum(f.stat().st_size for f in CARPETA.rglob("*") if f.is_file())
    print(f"\nCarpeta: {tam_carpeta / 1e6:.0f} MB  ·  Zip: {destino.stat().st_size / 1e6:.0f} MB  ->  {destino}")


if __name__ == "__main__":
    os.chdir(RAIZ)
    main()
