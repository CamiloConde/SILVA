# Créditos y licencias de terceros

SILVA usa y redistribuye los siguientes datos y componentes. Cada uno conserva su licencia original.

## Datos

| Recurso | Uso en SILVA | Licencia / condiciones | Fuente |
|---|---|---|---|
| Dataset de landmarks del alfabeto dactilológico de LSC (JuanPlazas, 2026) | Entrenamiento del modelo de letras (`modelos/modelo_senas.pkl`); muestras derivadas en `data/landmarks/externo_juanplazas.npz` | Uso educativo, académico, de investigación y desarrollo **citando la autoría** (`CERTIFICATE.md` del autor; sin archivo de licencia formal) | https://github.com/JuanPlazas/deteccion_letras_senas |
| LSC-54 (Mora-Zarate, 2025) | Entrenamiento del modelo de palabras (`modelos/modelo_palabras.pkl`); landmarks extraídos de los videos en `data/landmarks/lsc54_secuencias.npz` | **CC BY-NC 4.0**: con atribución y **sin fines comerciales**. Los videos originales no se redistribuyen | https://doi.org/10.57760/sciencedb.25639 |

Como el modelo de palabras se deriva de LSC-54, **SILVA no puede venderse ni usarse con fines comerciales** mientras incluya ese modelo.

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

**Sobre PySide6 (LGPL):** se distribuye como bibliotecas dinámicas separadas (carpeta `_internal` del ejecutable). Quien lo desee puede reemplazarlas por otra versión compatible. El código fuente de Qt está disponible en https://code.qt.io.

**Sobre MediaPipe:** la versión está fija en 0.10.21 porque las versiones que publica Google desde la 0.10.22 envían estadísticas de uso a `play.googleapis.com` sin forma de desactivarlo ([issue #6291](https://github.com/google-ai-edge/mediapipe/issues/6291)). Eso incumpliría el requisito de privacidad RNF-01.
