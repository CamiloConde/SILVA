"""Convierte los puntos de LSC50 (MediaPipe Holistic, CSV) al formato del modo Palabras.

Fuente: Flórez-Sierra, Solórzano, Segura-Quijano et al. (2024). LSC50: Colombian Sign Language
Video and Inertial Measurement dataset. Scientific Data, 11, 1347. Datos en figshare:
https://figshare.com/articles/dataset/LSC50_Colombian_Sign_Language_Video_and_Inertial_Measurement_Dataset/27383016
— Licencia CC BY 4.0. 50 señas × 5 personas × 4 repeticiones, video de cuerpo entero 1920×1080.

Se usan los puntos ya extraídos (LANDMARKS.zip): pose (33) y ambas manos (21). Cada cuadro pasa por
silva.cuerpo.caracteristicas_cuadro, igual que en vivo; las manos se asignan a izquierda/derecha por
cercanía a las muñecas de la pose. Las señas que también están en el vocabulario de SILVA (LSC-54)
quedan con la misma etiqueta; las demás conservan su nombre de LSC50.

Uso:
    python scripts/preparar_lsc50.py
"""

from __future__ import annotations

import csv
import io
import zipfile

import numpy as np

from silva import config
from silva.cuerpo import CuadroCuerpo, asignar_manos, caracteristicas_cuadro, N_CARACTERISTICAS_CUADRO
from silva.modelo import Landmark

ZIP = config.RAIZ_PROYECTO / "data" / "externo" / "lsc50" / "LANDMARKS.zip"
DESTINO = config.DIR_LANDMARKS / "lsc50_secuencias.npz"
ASPECTO = 1920 / 1080

# Tabla 1 del artículo (id de clase → seña). Las que coinciden con el vocabulario de SILVA usan la
# etiqueta de LSC-54 (ver NOMBRES en scripts/entrenar_palabras.py).
SENAS = [
    "Gracias", "Buenos dias", "Buenas tardes", "Buenas Noches", "Seña", "Nombre", "Trabajar", "Comer",
    "Vivir", "Poco", "Familia", "Personas", "Mujer", "Hombre", "Niño", "Niña", "Abuelo", "Tío", "Hermano",
    "Hambre", "Feliz", "Contento", "Triste", "Aburrido", "Bien", "Mal", "Como esta", "Maso Menos", "Sentir",
    "Juicioso", "Hola", "Adiós", "Por favor", "Con gusto", "Bienvenido", "Perdon", "Permiso", "Nunca", "Yo",
    "Tú", "Ustedes", "¿Qué?", "¿Cuándo?", "¿Dónde?", "¿Cómo?", "¿Por qué?", "¿Quién?", "Diferente", "Todos",
    "Mucho",
]


def _leer(z: zipfile.ZipFile, ruta: str, puntos: int) -> np.ndarray:
    """Matriz cuadros × puntos × 2 (x, y); NaN donde no hubo detección (fila vacía o en ceros)."""
    filas = list(csv.reader(io.StringIO(z.read(ruta).decode())))[1:]
    datos = np.full((len(filas), puntos, 2), np.nan)
    for i, fila in enumerate(filas):
        valores = [float(v) if v not in ("", "nan") else np.nan for v in fila[1:1 + 3 * puntos]]
        if len(valores) < 3 * puntos:
            continue
        xyz = np.array(valores).reshape(puntos, 3)
        if np.all(np.nan_to_num(xyz) == 0):
            continue
        datos[i] = xyz[:, :2]
    return datos


def main() -> None:
    z = zipfile.ZipFile(ZIP)
    nombres = sorted(n for n in z.namelist() if "/BODY_LANDMARKS/" in n and n.endswith(".csv"))
    secuencias, etiquetas, firmantes, sin_manos = [], [], [], 0
    for ruta in nombres:
        clave = ruta.rsplit("/", 1)[1]
        sena, persona, _ = (int(v) for v in clave[:-4].split("_"))
        cuerpo = _leer(z, ruta, 33)
        izq = _leer(z, ruta.replace("BODY_LANDMARKS", "HANDS_LANDMARKS/LEFT_HAND_LANDMARKS"), 21)
        der = _leer(z, ruta.replace("BODY_LANDMARKS", "HANDS_LANDMARKS/RIGHT_HAND_LANDMARKS"), 21)
        n = min(len(cuerpo), len(izq), len(der))
        cuadros = []
        for t in range(n):
            if np.isnan(cuerpo[t]).any():
                cuadros.append(np.full(N_CARACTERISTICAS_CUADRO, np.nan, np.float32))
                continue
            pose = [Landmark(*p) for p in cuerpo[t]]
            manos = [[Landmark(*p) for p in m[t]] for m in (izq, der) if not np.isnan(m[t]).any()]
            mano_izq, mano_der = asignar_manos(pose, manos)
            cuadros.append(caracteristicas_cuadro(CuadroCuerpo(pose, mano_izq, mano_der, ASPECTO)))
        s = np.array(cuadros, np.float32).reshape(-1, N_CARACTERISTICAS_CUADRO)
        sin_manos += int(np.nanmax(s[:, [14 + 42, 14 + 43 + 42]]) <= 0) if len(s) else 1
        secuencias.append(s)
        etiquetas.append(SENAS[sena])
        firmantes.append(f"L50-{persona}")
    np.savez_compressed(DESTINO, secuencias=np.array(secuencias, dtype=object), etiquetas=np.array(etiquetas),
                        firmantes=np.array(firmantes), categorias=np.array(["LSC50"] * len(etiquetas)),
                        nombres=np.array(nombres))
    print(f"{len(secuencias)} secuencias de {len(set(etiquetas))} señas y {len(set(firmantes))} personas "
          f"(sin ninguna mano detectada: {sin_manos}) -> {DESTINO}")


if __name__ == "__main__":
    main()
