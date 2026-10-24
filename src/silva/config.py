"""Constantes compartidas por la aplicación, los scripts y las pruebas."""

import os
import sys
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

# Dentro del ejecutable (PyInstaller) los recursos están en la carpeta del paquete y
# el historial va a la carpeta de datos del usuario, donde siempre se puede escribir
# (no en «Archivos de programa»). Desde el código fuente, todo queda en el proyecto.
EMPAQUETADO = getattr(sys, "frozen", False)
DIR_RECURSOS = Path(getattr(sys, "_MEIPASS", RAIZ_PROYECTO))
if EMPAQUETADO:
    DIR_DATOS_USUARIO = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SILVA"
else:
    DIR_DATOS_USUARIO = RAIZ_PROYECTO / "data"

# Rutas
DIR_MODELOS = DIR_RECURSOS / "modelos"
RUTA_ICONO = DIR_RECURSOS / "recursos" / "silva.ico"
RUTA_MODELO_MANOS = DIR_MODELOS / "hand_landmarker.task"  # MediaPipe Hand Landmarker
RUTA_MODELO_SENAS = DIR_MODELOS / "modelo_senas.pkl"  # clasificador de letras
RUTA_MODELO_POSE = DIR_MODELOS / "pose_landmarker_lite.task"  # MediaPipe Pose Landmarker
RUTA_MODELO_PALABRAS = DIR_MODELOS / "modelo_palabras.pkl"  # clasificador de palabras
DIR_LANDMARKS = RAIZ_PROYECTO / "data" / "landmarks"
RUTA_HISTORIAL = DIR_DATOS_USUARIO / "historial.db"

# Formato de los landmarks
NUM_LANDMARKS = 21
NUM_CARACTERISTICAS = NUM_LANDMARKS * 2  # (x, y) por landmark

# Detección de la mano
CONFIANZA_DETECCION = 0.6
CONFIANZA_SEGUIMIENTO = 0.6

# Regla de confirmación (RF-04, Figura 4 del modelado UML)
UMBRAL_CONFIANZA = 0.80
CUADROS_ESTABLES = 5

# Letras estáticas del alfabeto dactilológico de LSC que cubre el MVP.
# G, H, J, M, N, Ñ, P, Q, S y Z se hacen con movimiento y quedan fuera de
# alcance (ver docs/dataset.md, análisis de movimiento por letra).
LETRAS_ESTATICAS = list("ABCDEFIKLORTUVWXY")

# Cámara
INDICE_CAMARA = 0
