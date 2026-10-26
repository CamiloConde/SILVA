"""Genera material de referencia para probar SILVA: cómo se hace cada seña que reconoce.

- Letras: el dataset de JuanPlazas (2026) no tiene imágenes, solo landmarks. Se dibuja
  el esqueleto de la mano de una muestra representativa de cada letra.
- Palabras: GIF animado de un video real de LSC-54 (Mora-Zarate, 2025) por expresión,
  recortado al tramo de la seña. Las caras vienen difuminadas en el dataset original.

La salida queda en data/externo/referencias/ (excluida de Git: LSC-54 es CC BY-NC y
sus videos no se redistribuyen). Abra referencias.html en el navegador.

También genera referencias_autocontenido.html: UN solo archivo con todas las imágenes
adentro (las animaciones en WebP), para enviarlo a otro equipo sin las carpetas.

Uso:
    python scripts/generar_referencias.py
"""

from __future__ import annotations

import base64
import html
import io
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from silva import config
from silva.detector_manos import CONEXIONES_MANO
from silva.palabras import actividad

DESTINO = config.RAIZ_PROYECTO / "data" / "externo" / "referencias"
ZIP_CORTESIA = config.RAIZ_PROYECTO / "data" / "externo" / "lsc54" / "courtesy.zip"
FONDO = (42, 30, 15)  # BGR del tema oscuro de la app


def dibujar_letra(puntos: np.ndarray, letra: str, tam: int = 360) -> np.ndarray:
    """Dibuja 21 puntos normalizados (muñeca en el origen) como esqueleto, en vista espejo."""
    p = puntos.reshape(21, 2).copy()
    p[:, 0] *= -1  # espejo: como se ve en la pantalla de SILVA
    minimo, maximo = p.min(axis=0), p.max(axis=0)
    escala = (tam * 0.72) / max(maximo - minimo)
    centro = (minimo + maximo) / 2
    px = [(int(tam / 2 + (x - centro[0]) * escala), int(tam / 2 + 20 + (y - centro[1]) * escala)) for x, y in p]
    lienzo = np.full((tam, tam, 3), FONDO, np.uint8)
    for a, b in CONEXIONES_MANO:
        cv2.line(lienzo, px[a], px[b], (120, 210, 140), 4, cv2.LINE_AA)
    for i, q in enumerate(px):
        color = (60, 160, 250) if i in (4, 8, 12, 16, 20) else (250, 150, 60)  # yemas en naranja
        cv2.circle(lienzo, q, 7, color, cv2.FILLED, cv2.LINE_AA)
    cv2.putText(lienzo, letra, (18, 58), cv2.FONT_HERSHEY_DUPLEX, 1.9, (245, 241, 241), 3, cv2.LINE_AA)
    return lienzo


def letras() -> list[str]:
    d = np.load(config.DIR_LANDMARKS / "externo_juanplazas.npz")
    X, y = d["X"], d["y"]
    carpeta = DESTINO / "letras"
    carpeta.mkdir(parents=True, exist_ok=True)
    imagenes = []
    for letra in config.LETRAS_ESTATICAS:
        muestras = X[y == letra]
        # Muestra representativa: la más cercana a la mediana de todas las de esa letra
        representativa = muestras[np.argmin(np.linalg.norm(muestras - np.median(muestras, axis=0), axis=1))]
        img = dibujar_letra(representativa, letra)
        cv2.imwrite(str(carpeta / f"{letra}.png"), img)
        imagenes.append(img)
    # Lámina con todas las letras
    filas = [np.hstack(imagenes[i:i + 6] + [np.full_like(imagenes[0], FONDO)] * (6 - len(imagenes[i:i + 6])))
             for i in range(0, len(imagenes), 6)]
    cv2.imwrite(str(DESTINO / "lamina_letras.png"), np.vstack(filas))
    return config.LETRAS_ESTATICAS


def palabras() -> list[tuple[str, str, str]]:
    import sys
    sys.path.insert(0, str(config.RAIZ_PROYECTO / "scripts"))
    from entrenar_palabras import nombre_visible

    d = np.load(config.DIR_LANDMARKS / "lsc54_secuencias.npz", allow_pickle=True)
    m = d["categorias"] == "Cordialidad"
    secuencias, etiquetas, firmantes, nombres = d["secuencias"][m], d["etiquetas"][m], d["firmantes"][m], d["nombres"][m]
    carpeta = DESTINO / "palabras"
    carpeta.mkdir(parents=True, exist_ok=True)
    resultado = []
    with zipfile.ZipFile(ZIP_CORTESIA) as z:
        for etiqueta in sorted(set(etiquetas), key=lambda e: nombre_visible(e).lower()):
            idx = np.flatnonzero(etiquetas == etiqueta)
            # Video con mejor detección de manos (menos cuadros perdidos) para que se vea claro
            def calidad(i):
                s = secuencias[i]
                return np.nanmean(np.maximum(s[:, 14 + 42], s[:, 14 + 43 + 42]))
            mejor = max(idx, key=calidad)
            act = actividad(secuencias[mejor])
            activos = np.flatnonzero(act)
            ini = max(int(activos[0]) - 6, 0) if len(activos) else 0
            fin = min(int(activos[-1]) + 6, len(act) - 1) if len(activos) else len(act) - 1

            with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp:
                tmp.write(z.read(nombres[mejor]))
            cap = cv2.VideoCapture(tmp.name)
            cuadros, i = [], 0
            while True:
                ok, f = cap.read()
                if not ok:
                    break
                if ini <= i <= fin:
                    cuadros.append(Image.fromarray(cv2.cvtColor(cv2.resize(f, (384, 216)), cv2.COLOR_BGR2RGB)))
                i += 1
            cap.release()
            Path(tmp.name).unlink()

            nombre = nombre_visible(etiqueta)
            archivo = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
            archivo = "".join(c if c.isalnum() else "_" for c in archivo).strip("_").lower() + ".gif"
            cuadros[0].save(carpeta / archivo, save_all=True, append_images=cuadros[1:], duration=40, loop=0,
                            optimize=True)
            resultado.append((nombre, archivo, f"firmante {firmantes[mejor]}"))
            print(f"  {nombre}: {len(cuadros)} cuadros (firmante {firmantes[mejor]})")
    return resultado


def _incrustar_letra(letra: str) -> str:
    datos = (DESTINO / "letras" / f"{letra}.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(datos).decode()


def _incrustar_palabra(archivo: str) -> str:
    """GIF → WebP animado (la mitad de los cuadros, 320×180): ~25 veces más liviano."""
    gif = Image.open(DESTINO / "palabras" / archivo)
    cuadros = []
    for i in range(0, gif.n_frames, 2):
        gif.seek(i)
        cuadros.append(gif.convert("RGB").resize((320, 180)))
    salida = io.BytesIO()
    cuadros[0].save(salida, "WEBP", save_all=True, append_images=cuadros[1:], duration=80, loop=0,
                    quality=55, method=4)
    return "data:image/webp;base64," + base64.b64encode(salida.getvalue()).decode()


def pagina(lista_letras: list[str], lista_palabras: list[tuple[str, str, str]], autocontenida: bool = False) -> Path:
    """referencias.html enlaza las carpetas; la versión autocontenida lleva las imágenes adentro."""
    src_letra = _incrustar_letra if autocontenida else (lambda l: f"letras/{l}.png")
    src_palabra = _incrustar_palabra if autocontenida else (lambda a: f"palabras/{a}")
    tarjetas_l = "\n".join(
        f'<figure><img src="{src_letra(l)}" alt="Letra {l}"><figcaption>{l}</figcaption></figure>'
        for l in lista_letras)
    tarjetas_p = "\n".join(
        f'<figure><img src="{src_palabra(a)}" alt="{html.escape(n)}"><figcaption>{html.escape(n)}'
        f'<small>{html.escape(f)}</small></figcaption></figure>' for n, a, f in lista_palabras)
    destino = DESTINO / ("referencias_autocontenido.html" if autocontenida else "referencias.html")
    destino.write_text(f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>SILVA · Señas de referencia</title>
<style>
body {{ background:#0b1120; color:#f1f5f9; font-family:"Segoe UI",sans-serif; margin:32px; }}
h1 {{ margin:0 0 4px; }} h2 {{ margin-top:36px; }} p, small {{ color:#94a3b8; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px; }}
.grid.p {{ grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); }}
figure {{ margin:0; background:#151e32; border:1px solid #26334a; border-radius:12px; padding:8px; }}
img {{ width:100%; border-radius:8px; display:block; }}
figcaption {{ padding:8px 4px 2px; font-weight:600; display:flex; justify-content:space-between; }}
</style></head><body>
<h1>Señas de referencia para probar SILVA</h1>
<p>Imite la seña frente a la cámara con la app en el modo correspondiente.</p>
<h2>Modo Deletreo · 17 letras</h2>
<p>Esqueleto de la mano dibujado a partir de los puntos del dataset (no contiene fotos), en vista espejo como en la
pantalla de SILVA; las yemas de los dedos están en naranja. Sostenga la seña hasta que se llene la barra de estabilidad.
Fuente: JuanPlazas (2026), deteccion_letras_senas.</p>
<div class="grid">{tarjetas_l}</div>
<h2>Modo Palabras · 33 expresiones</h2>
<p>Videos reales del dataset LSC-54 (caras difuminadas por sus autores). Deben verse hombros y manos; empiece con
las manos abajo, haga la seña y vuelva a bajarlas. Fuente: Mora-Zarate, J. E. (2025), Science Data Bank,
https://doi.org/10.57760/sciencedb.25639 — licencia CC BY-NC 4.0 (uso no comercial, con atribución).</p>
<div class="grid p">{tarjetas_p}</div>
</body></html>""", encoding="utf-8")
    return destino


def main() -> None:
    print("Letras…")
    l = letras()
    print("Palabras…")
    p = palabras()
    pagina(l, p)
    unico = pagina(l, p, autocontenida=True)
    print(f"Listo: {DESTINO / 'referencias.html'}")
    print(f"Archivo único para enviar: {unico} ({unico.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
