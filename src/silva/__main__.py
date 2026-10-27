"""Punto de entrada: python -m silva"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from silva.buffer_texto import BufferTexto
from silva.captura_video import CapturaVideo
from silva.clasificador import ClasificadorPreentrenado
from silva.controlador import ControladorSILVA
from silva.cuerpo import DetectorCuerpo
from silva.detector_manos import DetectorManos
from silva.interfaz import GRAFITO, PAPEL, TINTA, VentanaPrincipal, cargar_fuentes
from silva.letras_movimiento import ClasificadorMovimiento
from silva.palabras import ClasificadorPalabras
from silva.repositorio_historial import RepositorioHistorial


def _icono():
    from PySide6.QtGui import QIcon

    from silva import config

    return QIcon(str(config.RUTA_ICONO)) if config.RUTA_ICONO.exists() else None


def _pantalla_de_carga():
    """Ventana sin bordes con el logo mientras se cargan los modelos (unos segundos)."""
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

    from silva import __version__, config

    ventana = QWidget()
    ventana.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
    ventana.setStyleSheet(f"background: {PAPEL}; color: {GRAFITO}; font-family: 'IBM Plex Sans'; font-size: 10pt;")
    v = QVBoxLayout(ventana)
    v.setContentsMargins(80, 40, 80, 34)
    v.setSpacing(6)
    fila = QHBoxLayout()
    fila.addStretch()
    if config.RUTA_MARCA.exists():
        marca = QLabel()
        marca.setPixmap(QPixmap(str(config.RUTA_MARCA)).scaledToHeight(64, Qt.SmoothTransformation))
        fila.addWidget(marca)
        fila.addSpacing(18)
    nombre = QLabel("SILVA")
    nombre.setStyleSheet(f"color: {TINTA}; font-size: 30pt; font-weight: 700; letter-spacing: 3px;")
    fila.addWidget(nombre)
    fila.addStretch()
    v.addLayout(fila)
    v.addSpacing(10)
    for texto in (f"Traductor de Lengua de Señas Colombiana · v{__version__}", "Cargando modelos…"):
        etiqueta = QLabel(texto)
        etiqueta.setAlignment(Qt.AlignCenter)
        v.addWidget(etiqueta)
    return ventana


def _cargar_palabras():
    """El modo Palabras es opcional: si falta su modelo, la app funciona solo con letras."""
    try:
        clasificador = ClasificadorPalabras()
        umbrales = (clasificador.metadatos.get("umbral", 0.5), clasificador.metadatos.get("umbral_sugerencia", 0.12))
        return DetectorCuerpo(), clasificador, umbrales
    except FileNotFoundError:
        return None, None, (0.5, 0.12)


def _cargar_movimiento():
    """Las letras con movimiento son opcionales: sin su modelo, el Deletreo sigue con las estáticas."""
    try:
        return ClasificadorMovimiento()
    except FileNotFoundError:
        return None


def _datos_para_entrenar() -> str:
    """Los datasets y el módulo de entrenamiento que usa «Entrenar los modelos ahora»."""
    from silva import config

    carpeta = str((config.DIR_RECURSOS if config.EMPAQUETADO else config.RAIZ_PROYECTO) / "scripts")
    if carpeta not in sys.path:
        sys.path.insert(0, carpeta)
    import entrenar_con_muestras  # noqa: F401 (comprueba que esté y que importe lo que necesita)

    nombres = ("lsc54_secuencias.npz", "lsc50_secuencias.npz", "lsc70_letras.npz", "lsc70_secuencias.npz",
               "externo_juanplazas.npz")
    faltan = [n for n in nombres if not (config.DIR_LANDMARKS / n).exists()]
    if faltan:
        raise FileNotFoundError("faltan " + ", ".join(faltan))
    return f"{len(nombres)} datasets en {config.DIR_LANDMARKS}"


def verificar(destino: Path, con_camara: bool) -> bool:
    """Autoverificación sin ventana (sirve para probar el ejecutable): modelos, detección y, opcionalmente, cámara."""
    import platform
    import time

    import numpy as np

    from silva import __version__, config

    lineas, ok = [f"SILVA {__version__} — verificación {time.strftime('%Y-%m-%d %H:%M:%S')}",
                  f"Python {platform.python_version()} · empaquetado={config.EMPAQUETADO}",
                  f"Recursos: {config.DIR_RECURSOS}", f"Historial: {config.RUTA_HISTORIAL}"], True

    def paso(nombre, funcion):
        nonlocal ok
        try:
            t = time.perf_counter()
            detalle = funcion()
            lineas.append(f"[OK]    {nombre} ({(time.perf_counter() - t) * 1000:.0f} ms){': ' + detalle if detalle else ''}")
        except Exception as error:  # noqa: BLE001 - el informe debe registrar cualquier falla
            ok = False
            lineas.append(f"[FALLA] {nombre}: {type(error).__name__}: {error}")

    cuadro = np.zeros((480, 640, 3), dtype=np.uint8)
    paso("Detector de manos (MediaPipe)", lambda: f"sin mano en cuadro vacío: {DetectorManos().detectar(cuadro, 0) is None}")
    paso("Clasificador de letras", lambda: f"{len(ClasificadorPreentrenado().letras)} letras")
    paso("Clasificador de letras con movimiento", lambda: " ".join(ClasificadorMovimiento().letras))
    paso("Detector de cuerpo (MediaPipe Pose)", lambda: f"pose en cuadro vacío: {DetectorCuerpo().detectar(cuadro, 0).pose is not None}")
    paso("Clasificador de palabras", lambda: f"{len(ClasificadorPalabras().palabras)} expresiones")
    paso("Historial (SQLite)", lambda: f"{len(RepositorioHistorial().listar_sesiones())} sesiones guardadas")
    paso("Datos para entrenar (Entrenar)", _datos_para_entrenar)
    if con_camara:
        def camara():
            c = CapturaVideo()
            c.abrir()
            leidos = sum(c.leer_cuadro() is not None for _ in range(15))
            c.liberar()
            if leidos == 0:
                raise RuntimeError("la cámara abrió pero no entregó cuadros")
            return f"{leidos}/15 cuadros leídos"
        paso("Cámara web", camara)
    lineas.append("RESULTADO: " + ("TODO CORRECTO" if ok else "HAY FALLAS"))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ok


def entrenar_sin_ventana() -> bool:
    """Lo mismo que «Entrenar los modelos ahora», sin ventana: el ejecutable no tiene consola, así que el registro
    va a %LOCALAPPDATA%/SILVA/entrenamiento.txt (desde el código, a data/entrenamiento.txt)."""
    import contextlib
    import importlib
    import traceback

    from silva import config

    registro = config.DIR_DATOS_USUARIO / "entrenamiento.txt"
    registro.parent.mkdir(parents=True, exist_ok=True)
    carpeta = str((config.DIR_RECURSOS if config.EMPAQUETADO else config.RAIZ_PROYECTO) / "scripts")
    sys.path.insert(0, carpeta)
    with registro.open("w", encoding="utf-8") as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
        try:
            importlib.import_module("entrenar_con_muestras").main(["--rapido"])
            return True
        except SystemExit as e:
            print(e)
            return e.code in (0, None)
        except Exception:  # noqa: BLE001 (queda en el registro)
            traceback.print_exc()
            return False


def main() -> None:
    if "--verificar" in sys.argv:
        from silva import config

        i = sys.argv.index("--verificar")
        hay_ruta = len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--")
        destino = Path(sys.argv[i + 1]) if hay_ruta else config.DIR_DATOS_USUARIO / "verificacion.txt"
        sys.exit(0 if verificar(destino, "--camara" in sys.argv) else 1)
    if "--entrenar" in sys.argv:  # reentrenar con las muestras grabadas, sin ventana (registro en entrenamiento.txt)
        sys.exit(0 if entrenar_sin_ventana() else 1)

    app = QApplication(sys.argv)  # Qt 6 ya maneja la escala de pantalla de Windows (texto nítido)
    app.setApplicationName("SILVA")
    if config_icono := _icono():
        app.setWindowIcon(config_icono)
    cargar_fuentes()  # IBM Plex Sans (recursos/fuentes), la tipografía de la identidad v2
    app.setFont(QFont("IBM Plex Sans", 10))

    aviso = _pantalla_de_carga()
    aviso.show()
    app.processEvents()

    try:
        # Orden de la Figura 3: primero se cargan los modelos, después (al presionar Iniciar) la cámara.
        detector_cuerpo, clasificador_palabras, (umbral_palabras, umbral_sugerencia) = _cargar_palabras()
        controlador = ControladorSILVA(
            captura=CapturaVideo(),
            detector=DetectorManos(),
            clasificador=ClasificadorPreentrenado(),
            historial=RepositorioHistorial(),
            buffer=BufferTexto(),
            detector_cuerpo=detector_cuerpo,
            clasificador_palabras=clasificador_palabras,
            umbral_palabras=umbral_palabras,
            umbral_sugerencia=umbral_sugerencia,
            clasificador_movimiento=_cargar_movimiento(),
        )
    except FileNotFoundError as error:
        aviso.close()
        QMessageBox.critical(None, "SILVA — falta un modelo", str(error))
        return

    ventana = VentanaPrincipal(controlador)
    aviso.close()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
