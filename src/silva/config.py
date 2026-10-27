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
RUTA_LOGO = DIR_RECURSOS / "recursos" / "silva_logo.png"  # ícono: S blanca sobre tinta
RUTA_MARCA = DIR_RECURSOS / "recursos" / "silva_marca.png"  # S sola (tinta y azul), para el encabezado
DIR_FUENTES = DIR_RECURSOS / "recursos" / "fuentes"  # IBM Plex Sans y Mono (OFL)
RUTA_PALABRAS_ES = DIR_RECURSOS / "recursos" / "palabras_es.txt"  # «¿Quisiste decir?» del deletreo
RUTA_MODELO_MANOS = DIR_MODELOS / "hand_landmarker.task"  # MediaPipe Hand Landmarker
RUTA_MODELO_SENAS = DIR_MODELOS / "modelo_senas.pkl"  # clasificador de letras
RUTA_MODELO_POSE = DIR_MODELOS / "pose_landmarker_lite.task"  # MediaPipe Pose Landmarker
RUTA_MODELO_PALABRAS = DIR_MODELOS / "modelo_palabras.pkl"  # clasificador de palabras
RUTA_MODELO_LETRAS_MOVIMIENTO = DIR_MODELOS / "modelo_letras_movimiento.pkl"  # G H J Ñ Q S Z
RUTA_ANIMACIONES =DIR_MODELOS / "animaciones_senas.npz"  # palabras a señas (scripts/generar_animaciones.py)
DIR_LANDMARKS = RAIZ_PROYECTO / "data" / "landmarks"
RUTA_HISTORIAL = DIR_DATOS_USUARIO / "historial.db"

# Formato de los landmarks
NUM_LANDMARKS = 21
NUM_CARACTERISTICAS = NUM_LANDMARKS * 2  # (x, y) por landmark

# Detección de la mano
CONFIANZA_DETECCION = 0.6
CONFIANZA_SEGUIMIENTO = 0.6
# Modo Palabras: con la mano en movimiento (desenfoque, cerca de la cara) MediaPipe la pierde a
# menudo. Medido en 4 512 cuadros de seña de LSC-54: con 0,6 se detecta en el 84,9 %, con 0,4 en
# el 87,2 % (la resolución no influye). Se usa 0,4 también al extraer LSC-54 para entrenar.
CONFIANZA_MANOS_PALABRAS = 0.4
# Recuperación de la mano perdida: si MediaPipe no encuentra una mano pero la pose dice dónde está la
# muñeca (y la mano no está en reposo), se busca en un recorte ampliado alrededor de ella. Medido en
# 40 videos de LSC-54: la mano en uso se detecta en el 70,3 % de los cuadros y con la recuperación
# en el 89,0 % (recorte de 1,8 anchos de hombro llevado a 256 px; ~20 ms por intento).
RECUPERAR_MANOS = True
RECORTE_RECUPERACION = 1.8  # lado del recorte, en anchos de hombro
TAM_RECORTE = 256  # px
CONFIANZA_RECUPERACION = 0.3

# Poca luz: la cámara alarga la exposición, los movimientos salen borrosos y se pierde la mano.
# Brillo medio de la imagen (0-255) por debajo del cual se avisa.
BRILLO_MINIMO = 55

# Encuadre ideal en modo Palabras (imagen 16:9), medido en 60 videos de LSC-54 con los que se entrenó:
# ancho de hombros = 21 % del ancho (p10-p90: 18-24 %), hombros centrados (x = 0,51) a media altura
# (y = 0,50) y la nariz a y = 0,31. La guía tolera un margen alrededor de esos valores.
ENCUADRE_HOMBROS = (0.15, 0.30)  # fracción del ancho: menos = muy lejos, más = muy cerca
ENCUADRE_CENTRO_X = (0.38, 0.62)
ENCUADRE_NARIZ_Y_MIN = 0.12  # la cabeza más arriba deja sin espacio a las señas cerca de la cabeza
ENCUADRE_HOMBROS_Y_MAX = 0.70  # hombros más abajo: la persona queda baja en la imagen

# Regla de confirmación (RF-04, Figura 4 del modelado UML). Con personas no vistas (LSC70, validación
# cruzada por persona): con 0,80 se escribían el 70 % de las señas (98,5 % de acierto) y con 0,60 el 85 %
# (96,1 % de acierto): con 0,80 muchas letras de manos nuevas no llegaban a escribirse. Además la letra
# debe sostenerse CUADROS_ESTABLES cuadros seguidos.
UMBRAL_CONFIANZA = 0.60
CUADROS_ESTABLES = 5

# Letras que se reconocen cuadro a cuadro (modelo de letras estáticas). M, N y P se agregaron en la
# versión 1.3: en LSC70 (70 personas) casi no se mueven. G, H, J, Ñ, Q, S y Z se hacen con un trazo
# y las reconoce el modelo de letras con movimiento (silva.letras_movimiento).
LETRAS_ESTATICAS = list("ABCDEFIKLMNOPRTUVWXY")
LETRAS = list("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")  # el alfabeto completo de LSC (27 letras)

# Letras con movimiento: segmentación del trazo. El movimiento de un cuadro es el desplazamiento
# medio de los 21 puntos de la mano respecto al cuadro anterior, en tamaños de mano (muñeca-nudillo).
MOVIMIENTO_INICIO = 0.08  # media de 3 cuadros por encima: empieza un trazo
MOVIMIENTO_FIN = 0.04  # por debajo durante CUADROS_QUIETO cuadros: el trazo terminó
CUADROS_QUIETO = 4
MIN_CUADROS_MOVIMIENTO = 6  # trazos más cortos (~0,2 s) se ignoran
MAX_CUADROS_MOVIMIENTO = 75  # ~2,5 s: un trazo más largo se corta y se clasifica
UMBRAL_MOVIMIENTO = 0.4  # probabilidad mínima para escribir una letra con movimiento
# Recorrido mínimo de la muñeca durante el trazo, en tamaños de mano. En LSC70 el 90 % de las letras con
# movimiento recorre más de 0,46 (la Q y la G, las que menos); las estáticas, 0,1-0,35 (mediana). Pasar de
# una letra estática a otra cambia la forma de la mano pero casi no la desplaza.
RECORRIDO_MINIMO = 0.4
# Si una letra estática se escribió justo antes de empezar el trazo (p. ej. la I con que empieza la J),
# era el comienzo de la letra con movimiento y se reemplaza.
SEGUNDOS_INICIO_TRAZO = 0.6

# Cámara
INDICE_CAMARA = 0
