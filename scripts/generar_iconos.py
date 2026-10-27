"""Genera los íconos de SILVA (PC y Android) a partir de los SVG de recursos/ (identidad v2).

- recursos/silva_logo.svg (S blanca y cursor azul sobre tinta) → silva_logo.png y silva.ico
- recursos/silva_marca.svg (S tinta y cursor azul, sin fondo) → silva_marca.png (encabezado de la app)
- íconos de la app Android (movil/app/src/main/res): mipmap de cada densidad y la capa del ícono adaptativo

Uso:
    python scripts/generar_iconos.py
"""

from __future__ import annotations

import io
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from silva import config

RECURSOS = config.RAIZ_PROYECTO / "recursos"
RES_ANDROID = config.RAIZ_PROYECTO / "movil" / "app" / "src" / "main" / "res"


def renderizar(svg: str, ancho: int, alto: int) -> Image.Image:
    img = QImage(ancho, alto, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    pintor = QPainter(img)
    pintor.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(pintor)
    pintor.end()
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    img.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA")


def main() -> None:
    QApplication.instance() or QApplication([])
    logo = (RECURSOS / "silva_logo.svg").read_text(encoding="utf-8")
    marca = (RECURSOS / "silva_marca.svg").read_text(encoding="utf-8")

    renderizar(logo, 512, 512).save(RECURSOS / "silva_logo.png")
    renderizar(logo, 256, 256).save(RECURSOS / "silva.ico",
                                    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    renderizar(marca, 220, 260).save(RECURSOS / "silva_marca.png")  # proporción del viewBox (233 × 275)

    if RES_ANDROID.exists():
        for carpeta, tam in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)):
            (RES_ANDROID / f"mipmap-{carpeta}").mkdir(exist_ok=True)
            renderizar(logo, tam, tam).save(RES_ANDROID / f"mipmap-{carpeta}" / "ic_launcher.png")
        # Ícono adaptativo: la S blanca en la zona segura (66 de 108 dp); el fondo tinta lo pone Android
        blanca = re.sub(r'stroke="#16181D"', 'stroke="#FFFFFF"', marca)
        capa = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
        s = renderizar(blanca, 190, 224)
        capa.paste(s, ((432 - 190) // 2, (432 - 224) // 2), s)
        (RES_ANDROID / "drawable-nodpi").mkdir(exist_ok=True)
        capa.save(RES_ANDROID / "drawable-nodpi" / "ic_launcher_foreground.png")
        renderizar(marca, 220, 260).save(RES_ANDROID / "drawable-nodpi" / "silva_marca.png")
    print("Listo: silva_logo.png, silva.ico, silva_marca.png" + (" e íconos de Android" if RES_ANDROID.exists() else ""))


if __name__ == "__main__":
    main()
