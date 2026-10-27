# Créditos y licencias de terceros

SILVA usa y redistribuye los siguientes datos y componentes. Cada uno conserva su licencia original.

## Datos

| Recurso | Uso en SILVA | Licencia / condiciones | Fuente |
|---|---|---|---|
| Dataset de landmarks del alfabeto dactilológico de LSC (JuanPlazas, 2026) | Entrenamiento del modelo de letras (`modelos/modelo_senas.pkl`); muestras derivadas en `data/landmarks/externo_juanplazas.npz` | Uso educativo, académico, de investigación y desarrollo **citando la autoría** (`CERTIFICATE.md` del autor; sin archivo de licencia formal) | https://github.com/JuanPlazas/deteccion_letras_senas |
| LSC70 (Muñoz Galindez, Villota Coral y Vargas-Cañas, 2024) | Modelo de letras (`modelo_senas.pkl`): 70 personas; puntos derivados en `data/landmarks/lsc70_letras.npz`. Modelo de letras con trazo (`modelos/modelo_letras_movimiento.pkl`); secuencias derivadas en `data/landmarks/lsc70_secuencias.npz` | **CC BY 4.0** (con atribución) | https://doi.org/10.17632/9ssyn8tff5.2 |
| LSC50 (Flórez-Sierra et al., 2024) | Modelo de palabras: 5 personas más, de otro entorno de grabación; puntos convertidos en `data/landmarks/lsc50_secuencias.npz` | **CC BY 4.0** (con atribución) | https://figshare.com/articles/dataset/LSC50_Colombian_Sign_Language_Video_and_Inertial_Measurement_Dataset/27383016 |
| LSC-54 (Mora-Zarate, 2025) | Entrenamiento del modelo de palabras (`modelos/modelo_palabras.pkl`); landmarks extraídos de los videos en `data/landmarks/lsc54_secuencias.npz`. Las señas animadas (`modelos/animaciones_senas.npz`) son los puntos de una grabación por seña, sin imagen | **CC BY-NC 4.0**: con atribución y **sin fines comerciales**. Los videos originales no se redistribuyen | https://doi.org/10.57760/sciencedb.25639 |
| FrequencyWords (Hermit Dave) | Las 20 000 palabras más frecuentes del español, para «¿Quisiste decir?» al deletrear (`recursos/palabras_es.txt`, filtradas a solo letras) | **CC BY-SA 4.0** (con atribución; una versión modificada de la lista se comparte con la misma licencia) | https://github.com/hermitdave/FrequencyWords |

Como el modelo de palabras y las animaciones se derivan de LSC-54, **SILVA no puede venderse ni usarse con fines comerciales** mientras incluya ese modelo.

## Software incluido en el ejecutable

| Componente | Licencia | Sitio |
|---|---|---|
| MediaPipe 0.10.21 y los modelos Hand Landmarker y Pose Landmarker (Google) | Apache 2.0 | https://github.com/google-ai-edge/mediapipe |
| Qt for Python / PySide6 (The Qt Company) | LGPL v3 | https://doc.qt.io/qtforpython-6/ |
| OpenCV | Apache 2.0 | https://opencv.org |
| scikit-learn | BSD 3-Clause | https://scikit-learn.org |
| NumPy | BSD 3-Clause | https://numpy.org |
| joblib | BSD 3-Clause | https://joblib.readthedocs.io |
| protobuf | BSD 3-Clause | https://github.com/protocolbuffers/protobuf |
| matplotlib (dependencia de MediaPipe) | Licencia matplotlib (tipo PSF/BSD) | https://matplotlib.org |
| Python 3.12 | PSF License | https://www.python.org |
| PyInstaller (solo para empaquetar; su bootloader se distribuye con excepción GPL) | GPL v2 con excepción de bootloader | https://pyinstaller.org |
| IBM Plex Sans e IBM Plex Mono (fuentes de la interfaz, en `recursos/fuentes/`) | SIL Open Font License 1.1 (`recursos/fuentes/OFL.txt`) | https://github.com/IBM/plex |

**Sobre PySide6 (LGPL):** se distribuye como bibliotecas dinámicas separadas (carpeta `_internal` del ejecutable). Quien lo desee puede reemplazarlas por otra versión compatible. El código fuente de Qt está disponible en https://code.qt.io.

**Sobre MediaPipe:** la versión está fija en 0.10.21 porque las versiones que publica Google desde la 0.10.22 envían estadísticas de uso a `play.googleapis.com` sin forma de desactivarlo ([issue #6291](https://github.com/google-ai-edge/mediapipe/issues/6291)). Eso incumpliría el requisito de privacidad RNF-01.

## Software incluido en la app de Android

| Componente | Licencia | Sitio |
|---|---|---|
| MediaPipe Tasks Vision 0.10.29 y los modelos Hand Landmarker y Pose Landmarker (Google) | Apache 2.0 | https://github.com/google-ai-edge/mediapipe |
| AndroidX: CameraX, Jetpack Compose, Activity, Core | Apache 2.0 | https://developer.android.com/jetpack/androidx |
| Kotlin y su biblioteca estándar | Apache 2.0 | https://kotlinlang.org |
| IBM Plex Sans e IBM Plex Mono | SIL Open Font License 1.1 (`assets/licencias/OFL_IBM_Plex.txt` dentro del APK) | https://github.com/IBM/plex |

**Sobre MediaPipe en Android:** se usa la 0.10.29 porque la 0.10.21 no carga en teléfonos con páginas de memoria de 16 KB. Esas versiones intentan enviar estadísticas de uso, pero la app no declara el permiso de internet (el manifiesto lo quita de forma explícita), así que Android bloquea cualquier conexión.
