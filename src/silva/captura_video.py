"""Captura de video desde la cámara web con OpenCV."""

from __future__ import annotations

import sys

import cv2
import numpy as np

from silva import config

ANCHO_PROCESO = 640  # los cuadros más anchos se reducen a este ancho (mismo campo de visión, menos cómputo)


class CamaraNoDisponibleError(RuntimeError):
    """La cámara no existe o la está usando otra aplicación (alt de la Figura 3)."""


class CapturaVideo:
    def __init__(self, indice: int = config.INDICE_CAMARA) -> None:
        self.indice = indice  # 0 = cámara integrada; 1, 2… = cámaras externas o el celular como cámara web
        self._resolucion = (640, 480)
        self._cap: cv2.VideoCapture | None = None

    def configurar(self, ancho: int, alto: int) -> None:
        """Resolución pedida a la cámara; si ya está abierta se aplica en caliente."""
        self._resolucion = (ancho, alto)
        if self.abierta:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)

    def abrir(self) -> None:
        # En Windows DirectShow abre la cámara mucho más rápido que el backend por defecto (RF-01: < 3 s).
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.indice, backend)
        if not cap.isOpened():
            cap.release()
            raise CamaraNoDisponibleError(f"No se pudo abrir la cámara {self.indice + 1}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolucion[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolucion[1])
        # con poca luz muchas cámaras bajan solas a 15 cuadros/s (exponen más): la mano rápida sale borrosa y
        # MediaPipe la pierde. Se piden 30; la cámara que no puede, lo ignora.
        cap.set(cv2.CAP_PROP_FPS, 30)
        self._cap = cap

    @property
    def abierta(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def leer_cuadro(self) -> np.ndarray | None:
        if not self.abierta:
            return None
        ok, cuadro = self._cap.read()
        if not ok:
            return None
        alto, ancho = cuadro.shape[:2]
        if ancho > ANCHO_PROCESO:
            cuadro = cv2.resize(cuadro, (ANCHO_PROCESO, round(alto * ANCHO_PROCESO / ancho)),
                                interpolation=cv2.INTER_AREA)
        return cuadro

    def liberar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


def camaras_disponibles() -> list[str]:
    """Nombres de las cámaras conectadas, en el orden de sus índices de OpenCV (DirectShow en Windows).

    Sirve para elegir por nombre («Cámara integrada HD», «Enlace Móvil», «DroidCam»…) en vez de «Cámara 2».
    Lista vacía si no se pudo consultar: la interfaz ofrece entonces cámaras numeradas.
    """
    if sys.platform != "win32":
        return []
    try:
        return _camaras_directshow()
    except OSError:
        return []


def _camaras_directshow() -> list[str]:
    # COM sin dependencias: ICreateDevEnum → IEnumMoniker → IMoniker → IPropertyBag("FriendlyName"). Es la misma
    # enumeración que usa OpenCV con CAP_DSHOW, así que la posición en la lista es el índice de la cámara.
    import ctypes
    from ctypes import POINTER, byref, c_void_p, c_wchar_p, wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

        def __init__(self, texto: str) -> None:
            import uuid
            u = uuid.UUID(texto)
            super().__init__(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))

    class VARIANT(ctypes.Structure):
        _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                    ("valor", c_void_p), ("extra", c_void_p)]

    ole32, oleaut32 = ctypes.OleDLL("ole32"), ctypes.WinDLL("oleaut32")

    def metodo(objeto: c_void_p, indice: int, *tipos):
        tabla = ctypes.cast(ctypes.cast(objeto, POINTER(c_void_p))[0], POINTER(c_void_p))
        return ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *tipos)(tabla[indice])

    def soltar(objeto: c_void_p) -> None:
        if objeto:
            ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(
                ctypes.cast(ctypes.cast(objeto, POINTER(c_void_p))[0], POINTER(c_void_p))[2])(objeto)

    # en el hilo de la ventana Qt ya inició COM (devuelve S_FALSE o RPC_E_CHANGED_MODE): no es un error
    try:
        iniciado = ole32.CoInitializeEx(None, 2) in (0, 1)  # COINIT_APARTMENTTHREADED
    except OSError:
        iniciado = False
    nombres: list[str] = []
    enumerador, monikers = c_void_p(), c_void_p()
    try:
        ole32.CoCreateInstance(byref(GUID("62BE5D10-60EB-11d0-BD3B-00A0C911CE86")), None, 1,  # CLSCTX_INPROC_SERVER
                               byref(GUID("29840822-5B84-11D0-BD3B-00A0C911CE86")), byref(enumerador))
        hr = metodo(enumerador, 3, c_void_p, POINTER(c_void_p), wintypes.DWORD)(
            enumerador, byref(GUID("860BB310-5D01-11d0-BD3B-00A0C911CE86")), byref(monikers), 0)
        if hr != 0 or not monikers:  # S_FALSE: no hay ninguna cámara
            return []
        siguiente = metodo(monikers, 3, wintypes.ULONG, POINTER(c_void_p), POINTER(wintypes.ULONG))
        while True:
            moniker, n = c_void_p(), wintypes.ULONG()
            if siguiente(monikers, 1, byref(moniker), byref(n)) != 0 or not moniker:
                break
            bolsa = c_void_p()
            try:
                metodo(moniker, 9, c_void_p, c_void_p, c_void_p, POINTER(c_void_p))(  # IMoniker::BindToStorage
                    moniker, None, None, byref(GUID("55272A00-42CB-11CE-8135-00AA004BB851")), byref(bolsa))
                v = VARIANT()
                metodo(bolsa, 3, c_wchar_p, POINTER(VARIANT), c_void_p)(bolsa, "FriendlyName", byref(v), None)
                nombres.append(ctypes.wstring_at(v.valor) if v.vt == 8 and v.valor else f"Cámara {len(nombres) + 1}")
                oleaut32.VariantClear(byref(v))
            except OSError:
                nombres.append(f"Cámara {len(nombres) + 1}")
            finally:
                soltar(bolsa)
                soltar(moniker)
    finally:
        soltar(monikers)
        soltar(enumerador)
        if iniciado:
            ole32.CoUninitialize()
    return nombres
