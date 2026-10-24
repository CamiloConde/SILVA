# Especificación de PyInstaller para el ejecutable de Windows.
# No se ejecuta directamente: use  python scripts/construir_ejecutable.py
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

RAIZ = Path(SPECPATH).parent  # noqa: F821 - SPECPATH lo define PyInstaller

datos = [
    (str(RAIZ / "modelos" / "hand_landmarker.task"), "modelos"),
    (str(RAIZ / "modelos" / "pose_landmarker_lite.task"), "modelos"),
    (str(RAIZ / "modelos" / "modelo_senas.pkl"), "modelos"),
    (str(RAIZ / "modelos" / "modelo_palabras.pkl"), "modelos"),
    (str(RAIZ / "recursos" / "silva.ico"), "recursos"),
]
datos += collect_data_files("mediapipe", includes=["**/*.binarypb", "**/*.tflite", "**/*.txt"])

a = Analysis(  # noqa: F821
    [str(RAIZ / "empaquetado" / "lanzador.py")],
    pathex=[str(RAIZ / "src")],
    binaries=collect_dynamic_libs("mediapipe"),
    datas=datos,
    hiddenimports=["sklearn.ensemble._forest", "sklearn.tree._classes", "sklearn.utils._typedefs"],
    excludes=[
        # No los usa SILVA (mediapipe los trae como dependencia opcional); excluirlos reduce el tamaño
        "jax", "jaxlib", "sounddevice", "tkinter", "pytest", "IPython", "PIL.ImageTk",
        "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore",
    ],
    noarchive=False,
)


def _innecesario(destino: str) -> bool:
    """Archivos pesados que SILVA no usa: lectura de archivos de video (solo usa la cámara),
    OpenGL por software (la ventana no usa OpenGL) y traducciones de Qt a otros idiomas."""
    d = destino.replace("\\", "/").lower()
    nombre = d.rsplit("/", 1)[-1]
    if nombre.startswith("opencv_videoio_ffmpeg") or nombre == "opengl32sw.dll":
        return True
    return "pyside6/translations/" in d and not nombre.endswith("_es.qm")


a.binaries = [b for b in a.binaries if not _innecesario(b[0])]
a.datas = [d for d in a.datas if not _innecesario(d[0])]

pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SILVA",
    icon=str(RAIZ / "recursos" / "silva.ico"),
    console=False,
    upx=False,
)
coleccion = COLLECT(exe, a.binaries, a.datas, name="SILVA", upx=False)  # noqa: F821
