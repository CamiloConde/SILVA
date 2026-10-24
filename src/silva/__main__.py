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
from silva.interfaz import FONDO, SUAVE, VentanaPrincipal
from silva.palabras import ClasificadorPalabras
from silva.repositorio_historial import RepositorioHistorial


def _icono():
    from PySide6.QtGui import QIcon

    from silva import config

    return QIcon(str(config.RUTA_ICONO)) if config.RUTA_ICONO.exists() else None


def _cargar_palabras():
    """El modo Palabras es opcional: si falta su modelo, la app funciona solo con letras."""
    try:
        clasificador = ClasificadorPalabras()
        return DetectorCuerpo(), clasificador, clasificador.metadatos.get("umbral", 0.5)
    except FileNotFoundError:
        return None, None, 0.5


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
    paso("Detector de cuerpo (MediaPipe Pose)", lambda: f"pose en cuadro vacío: {DetectorCuerpo().detectar(cuadro, 0).pose is not None}")
    paso("Clasificador de palabras", lambda: f"{len(ClasificadorPalabras().palabras)} expresiones")
    paso("Historial (SQLite)", lambda: f"{len(RepositorioHistorial().listar_sesiones())} sesiones guardadas")
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


def main() -> None:
    if "--verificar" in sys.argv:
        from silva import config

        i = sys.argv.index("--verificar")
        hay_ruta = len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--")
        destino = Path(sys.argv[i + 1]) if hay_ruta else config.DIR_DATOS_USUARIO / "verificacion.txt"
        sys.exit(0 if verificar(destino, "--camara" in sys.argv) else 1)

    app = QApplication(sys.argv)  # Qt 6 ya maneja la escala de pantalla de Windows (texto nítido)
    app.setApplicationName("SILVA")
    if config_icono := _icono():
        app.setWindowIcon(config_icono)
    app.setFont(QFont("Segoe UI", 10))

    aviso = QLabel("SILVA\nCargando modelos…")
    aviso.setAlignment(Qt.AlignCenter)
    aviso.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
    aviso.setStyleSheet(f"background: {FONDO}; color: {SUAVE}; font-size: 14pt; padding: 40px 70px;")
    aviso.show()
    app.processEvents()

    try:
        # Orden de la Figura 3: primero se cargan los modelos, después (al presionar Iniciar) la cámara.
        detector_cuerpo, clasificador_palabras, umbral_palabras = _cargar_palabras()
        controlador = ControladorSILVA(
            captura=CapturaVideo(),
            detector=DetectorManos(),
            clasificador=ClasificadorPreentrenado(),
            historial=RepositorioHistorial(),
            buffer=BufferTexto(),
            detector_cuerpo=detector_cuerpo,
            clasificador_palabras=clasificador_palabras,
            umbral_palabras=umbral_palabras,
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
