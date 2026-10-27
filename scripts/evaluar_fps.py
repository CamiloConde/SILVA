"""Modo Palabras en vivo a distintos cuadros por segundo: segmentador por cuadros contra por segundos.

En un teléfono la app procesa 10-20 cuadros/s, no los 30 del video de LSC-54 con que se calibró el
segmentador. Este script simula la cámara en vivo con los videos de personas que el modelo no vio:

1. Comprueba que, a 30 cuadros/s, el segmentador por segundos corta exactamente igual que el anterior.
2. Pasa cada video (con reposo antes y después) a 30, 15, 10 y 7,5 cuadros/s por los dos segmentadores
   y aplica la regla de la app: cuenta palabras escritas bien, mal, sugeridas y señas perdidas, y
   palabras falsas con señas ajenas al vocabulario (colores y números).

Evaluación: 3 pliegues por persona de LSC-54 (el modelo de cada pliegue no vio a sus personas de prueba).

    python scripts/evaluar_fps.py
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entrenar_palabras as ep  # noqa: E402

from silva import config  # noqa: E402
from silva.palabras import (CUADROS_FIN, MARGEN, MAX_CUADROS, MIN_ACTIVOS, MOVIMIENTO_ACTIVO, OTRA,  # noqa: E402
                            SegmentadorSenas, _levantada, _munecas, vector_secuencia)

PASOS = {30: 1, 15: 2, 10: 3, 7.5: 4}  # cuadros/s simulados → tomar un cuadro de cada tantos
REPOSO_ANTES, REPOSO_DESPUES = 15, 45  # cuadros de reposo (a 30/s) agregados a cada video


class SegmentadorCuadros:
    """El segmentador de la versión 1.3.0, que cuenta cuadros (copia para comparar)."""

    def __init__(self) -> None:
        self._previo: deque[np.ndarray] = deque(maxlen=MARGEN)
        self._actual: list[np.ndarray] = []
        self._reposo = 0
        self._activos = 0
        self._munecas_previas: list[np.ndarray] = []

    def agregar(self, f: np.ndarray) -> np.ndarray | None:
        munecas = _munecas(f)
        activo = _levantada(f, munecas) or (bool(self._munecas_previas and munecas) and any(
            min(np.linalg.norm(m - p) for p in self._munecas_previas) > MOVIMIENTO_ACTIVO for m in munecas))
        self._munecas_previas = munecas
        terminada = None
        if not self._actual:
            if activo:
                self._actual = [*self._previo, f]
                self._reposo = 0
                self._activos = 1
            else:
                self._previo.append(f)
        else:
            self._actual.append(f)
            self._reposo = 0 if activo else self._reposo + 1
            self._activos += int(activo)
            if self._reposo >= CUADROS_FIN or len(self._actual) >= MAX_CUADROS:
                seq = np.array(self._actual)
                if self._reposo >= CUADROS_FIN:
                    seq = seq[: len(seq) - self._reposo + MARGEN]
                if self._activos >= MIN_ACTIVOS:
                    terminada = seq
                self._actual = []
                self._previo.clear()
                self._reposo = 0
        return terminada


def con_reposo(s: np.ndarray) -> np.ndarray:
    return np.concatenate([np.repeat(s[:1], REPOSO_ANTES, 0), s, np.repeat(s[-1:], REPOSO_DESPUES, 0)])


def segmentos(s: np.ndarray, fps: float, por_segundos: bool) -> list[np.ndarray]:
    paso = PASOS[fps]
    idx = range(0, len(s), paso)
    if por_segundos:
        seg = SegmentadorSenas()
        res = (seg.agregar(s[i], i / 30).terminada for i in idx)
    else:
        seg = SegmentadorCuadros()
        res = (seg.agregar(s[i]) for i in idx)
    return [r for r in res if r is not None]


def main() -> None:
    d = np.load(ep.ORIGEN, allow_pickle=True)
    sec, etq, fir = d["secuencias"], d["etiquetas"].astype(object), d["firmantes"].astype(str)
    cat = np.array([ep._norm_categoria(c) for c in d["categorias"]])
    es_vocab = cat == ep.VOCABULARIO
    es_neg = np.isin(cat, ["Colores", "Numeros"])
    etiquetas = np.where(es_vocab, etq, OTRA)
    umbral = joblib.load(config.RUTA_MODELO_PALABRAS)["metadatos"].get("umbral", 0.2)

    # 1) A 30 cuadros/s los dos segmentadores deben cortar igual
    distintos = 0
    for s in sec[es_vocab | es_neg]:
        a, b = segmentos(con_reposo(s), 30, False), segmentos(con_reposo(s), 30, True)
        distintos += len(a) != len(b) or any(x.shape != y.shape or not np.array_equal(x, y) for x, y in zip(a, b))
    print(f"A 30 cuadros/s, videos donde los dos segmentadores cortan distinto: {distintos} de {(es_vocab | es_neg).sum()}")

    # LSC50 siempre al entrenamiento (sus personas no se prueban aquí)
    extra = []
    if ep.ORIGEN_LSC50.exists():
        d50 = np.load(ep.ORIGEN_LSC50, allow_pickle=True)
        vocab = set(ep.NOMBRES)
        extra = [(s, str(e) if str(e) in vocab else OTRA, str(f)) for s, e, f in
                 zip(d50["secuencias"], d50["etiquetas"], d50["firmantes"])]

    personas = np.unique(fir[es_vocab])
    resultados = {(fps, ps): {"bien": 0, "mal": 0, "sugerida": 0, "nada": 0, "videos": 0, "falsas": 0, "ajenas": 0}
                  for fps in PASOS for ps in (False, True)}
    for k, (tr, te) in enumerate(GroupKFold(n_splits=3).split(personas, groups=personas), 1):
        prueba = set(personas[te])
        m_tr = ~np.isin(fir, list(prueba)) & (es_vocab | es_neg)
        s_tr = list(sec[m_tr]) + [x[0] for x in extra]
        e_tr = list(etiquetas[m_tr]) + [x[1] for x in extra]
        f_tr = list(fir[m_tr]) + [x[2] for x in extra]
        X, y, _, _ = ep.construir(np.array(s_tr, dtype=object), np.array(e_tr, dtype=object), np.array(f_tr), True)
        modelo = ep.nuevo_modelo().fit(X, y)
        clases = modelo.classes_
        print(f"Pliegue {k}: modelo sin {len(prueba)} personas, entrenado con {len(X)} ejemplos")
        m_te = np.isin(fir, list(prueba)) & (es_vocab | es_neg)
        for s, real in zip(sec[m_te], etiquetas[m_te]):
            s = con_reposo(s)
            for fps in PASOS:
                for ps in (False, True):
                    r = resultados[(fps, ps)]
                    segs = segmentos(s, fps, ps)
                    decisiones = []
                    if segs:
                        proba = modelo.predict_proba(np.array([vector_secuencia(g) for g in segs]))
                        mejor, _, escribe, sugiere, top3 = ep.decidir(proba, clases, umbral)
                        decisiones = list(zip(mejor, escribe, sugiere, top3))
                    escritas = [m for m, e, _, _ in decisiones if e]
                    if real == OTRA:
                        r["ajenas"] += 1
                        r["falsas"] += bool(escritas)
                        continue
                    r["videos"] += 1
                    if real in escritas and all(w == real for w in escritas):
                        r["bien"] += 1
                    elif escritas:
                        r["mal"] += 1
                    elif any(su and real in t for _, _, su, t in decisiones):
                        r["sugerida"] += 1
                    else:
                        r["nada"] += 1

    print("\n| Cuadros/s | Segmentador | Escrita bien | Escrita mal | «¿Quisiste decir?» | No detectada | Palabras falsas (ajenas) |")
    print("|---|---|---|---|---|---|---|")
    for fps in PASOS:
        for ps in (False, True):
            r = resultados[(fps, ps)]
            n = r["videos"]
            print(f"| {fps:g} | {'por segundos' if ps else 'por cuadros (1.3.0)'} | {r['bien'] / n:.1%} | "
                  f"{r['mal'] / n:.1%} | {r['sugerida'] / n:.1%} | {r['nada'] / n:.1%} | "
                  f"{r['falsas'] / max(r['ajenas'], 1):.1%} |")
    print(f"\n{n} videos del vocabulario y {r['ajenas']} ajenos, de {len(personas)} personas de LSC-54 no vistas.")


if __name__ == "__main__":
    main()
