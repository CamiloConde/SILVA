"""Reposo aprendido del segmentador de Palabras: personas sentadas (muestras propias) y de pie (LSC-54).

1. Muestras propias (data/propias, grabadas con la app): cada una se simula como un flujo en vivo, con la
   persona quieta en su posición de reposo 1,5 s antes y después de la seña (la imagen de la muestra con las
   muñecas más abajo). Se compara el segmentador sin y con reposo aprendido: si la seña termina
   antes del máximo de 4 s y qué escribe el modelo de palabras actual (que nunca vio estas muestras).
2. LSC-54 (personas de pie): con reposo aprendido, ¿corta los videos igual que antes?

    python scripts/evaluar_reposo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entrenar_palabras as ep  # noqa: E402
import evaluar_fps as ev  # noqa: E402

from silva import config, muestras_propias as mp  # noqa: E402
from silva.palabras import SEGUNDOS_MAX, SegmentadorSenas, vector_secuencia  # noqa: E402

REPOSO = 1.5  # segundos quieto antes y después de la seña


def segmentar(cuadros: np.ndarray, fps: float, aprender: bool) -> list[np.ndarray]:
    seg = SegmentadorSenas(aprender_reposo=aprender)
    salida = []
    for i, f in enumerate(cuadros):
        e = seg.agregar(f, i / fps)
        if e.terminada is not None:
            salida.append(e.terminada)
    return salida


def muestras_sentadas() -> None:
    muestras = [m for a in mp.archivos() for m in mp.leer(a) if m.get("tipo") == "palabra"]
    if not muestras:
        print("No hay muestras propias de palabras en", mp.DIR_PROPIAS)
        return
    paquete = joblib.load(config.RUTA_MODELO_PALABRAS)
    modelo, umbral = paquete["modelo"], paquete["metadatos"].get("umbral", 0.2)
    print(f"{len(muestras)} señas grabadas con la app ({', '.join(sorted({m['clave'] for m in muestras}))})\n")
    print("| Segmentador | Seña cortada antes de 4 s | Escrita bien | Escrita mal | «¿Quisiste decir?» | Nada |")
    print("|---|---|---|---|---|---|")
    for aprender in (False, True):
        r = {"a_tiempo": 0, "bien": 0, "mal": 0, "sugerida": 0, "nada": 0}
        for m in muestras:
            fps = float(m.get("fps") or 30)
            c = np.asarray(m["cuadros"], np.float32)
            n = int(REPOSO * fps)
            # el reposo: la imagen con las muñecas más abajo (en una seña cortada a los 4 s, la última no lo es)
            reposo = c[int(np.argmax(c[:, 11] + c[:, 13]))][None]
            flujo = np.concatenate([np.repeat(reposo, n, 0), c, np.repeat(reposo, n, 0)])
            segs = segmentar(flujo, fps, aprender)
            r["a_tiempo"] += bool(segs) and all(len(s) / fps < SEGUNDOS_MAX * 0.97 for s in segs)
            decisiones = []
            if segs:
                proba = modelo.predict_proba(np.array([vector_secuencia(s) for s in segs]))
                mejor, _, escribe, sugiere, top3 = ep.decidir(proba, modelo.classes_, umbral)
                decisiones = list(zip(mejor, escribe, sugiere, top3))
            escritas = [w for w, e, _, _ in decisiones if e]
            if m["clave"] in escritas and all(w == m["clave"] for w in escritas):
                r["bien"] += 1
            elif escritas:
                r["mal"] += 1
            elif any(su and m["clave"] in t for _, _, su, t in decisiones):
                r["sugerida"] += 1
            else:
                r["nada"] += 1
        n = len(muestras)
        print(f"| {'con reposo aprendido' if aprender else 'sin reposo aprendido (1.4.1)'} | {r['a_tiempo'] / n:.0%} | "
              f"{r['bien'] / n:.0%} | {r['mal'] / n:.0%} | {r['sugerida'] / n:.0%} | {r['nada'] / n:.0%} |")


def lsc54_de_pie() -> None:
    d = np.load(ep.ORIGEN, allow_pickle=True)
    cat = np.array([ep._norm_categoria(c) for c in d["categorias"]])
    sec = d["secuencias"][np.isin(cat, [ep.VOCABULARIO, "Colores", "Numeros"])]
    for fps in (30, 15):
        distintos = 0
        for s in sec:
            flujo = ev.con_reposo(s)[::ev.PASOS[fps]]
            a, b = segmentar(flujo, fps, False), segmentar(flujo, fps, True)
            distintos += len(a) != len(b) or any(x.shape != y.shape or not np.array_equal(x, y) for x, y in zip(a, b))
        print(f"LSC-54 (de pie) a {fps} cuadros/s: videos que se cortan distinto con reposo aprendido: "
              f"{distintos} de {len(sec)} ({distintos / len(sec):.1%})")


def lsc54_reconocimiento() -> None:
    """Con personas de LSC-54 que el modelo no vio (3 pliegues): ¿cambia lo que se escribe?"""
    from sklearn.model_selection import GroupKFold

    from silva.palabras import OTRA
    d = np.load(ep.ORIGEN, allow_pickle=True)
    sec, etq, fir = d["secuencias"], d["etiquetas"].astype(object), d["firmantes"].astype(str)
    cat = np.array([ep._norm_categoria(c) for c in d["categorias"]])
    es_vocab, es_neg = cat == ep.VOCABULARIO, np.isin(cat, ["Colores", "Numeros"])
    etiquetas = np.where(es_vocab, etq, OTRA)
    umbral = joblib.load(config.RUTA_MODELO_PALABRAS)["metadatos"].get("umbral", 0.2)
    personas = np.unique(fir[es_vocab])
    r = {(fps, a): {"bien": 0, "videos": 0, "falsas": 0, "ajenas": 0} for fps in (30, 15) for a in (False, True)}
    for tr, te in GroupKFold(n_splits=3).split(personas, groups=personas):
        prueba = set(personas[te])
        m_tr = ~np.isin(fir, list(prueba)) & (es_vocab | es_neg)
        X, y, _, _ = ep.construir(sec[m_tr], etiquetas[m_tr], fir[m_tr], True)
        modelo = ep.nuevo_modelo().fit(X, y)
        for s, real in zip(sec[np.isin(fir, list(prueba)) & (es_vocab | es_neg)],
                           etiquetas[np.isin(fir, list(prueba)) & (es_vocab | es_neg)]):
            for fps in (30, 15):
                flujo = ev.con_reposo(s)[::ev.PASOS[fps]]
                for a in (False, True):
                    segs = segmentar(flujo, fps, a)
                    escritas = []
                    if segs:
                        mejor, _, escribe, _, _ = ep.decidir(
                            modelo.predict_proba(np.array([vector_secuencia(g) for g in segs])), modelo.classes_, umbral)
                        escritas = list(mejor[escribe])
                    x = r[(fps, a)]
                    if real == OTRA:
                        x["ajenas"] += 1
                        x["falsas"] += bool(escritas)
                    else:
                        x["videos"] += 1
                        x["bien"] += real in escritas and all(w == real for w in escritas)
    print("\n| Cuadros/s | Segmentador | Escritas bien | Palabras falsas (ajenas) |\n|---|---|---|---|")
    for (fps, a), x in r.items():
        print(f"| {fps} | {'con reposo aprendido' if a else 'sin reposo aprendido (1.4.1)'} | "
              f"{x['bien'] / x['videos']:.1%} | {x['falsas'] / x['ajenas']:.1%} |")


def main() -> None:
    muestras_sentadas()
    print()
    lsc54_de_pie()
    if "--completo" in sys.argv:
        lsc54_reconocimiento()


if __name__ == "__main__":
    main()
