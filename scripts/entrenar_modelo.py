"""Entrena el clasificador Random Forest y genera modelos/modelo_senas.pkl.

Usa todos los archivos .npz de data/landmarks (dataset externo + capturas propias).
La evaluación separa secuencias/ráfagas completas entre entrenamiento y prueba
(no cuadros sueltos), para no inflar la precisión con cuadros casi idénticos.
Si hay capturas propias, además mide cómo generaliza un modelo entrenado solo
con el dataset externo a las manos del equipo.

Uso:
    python scripts/entrenar_modelo.py [--sin-aumento] [--arboles 150]
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit

from silva import config

RUTA_REPORTE = config.RAIZ_PROYECTO / "docs" / "metricas_modelo.md"
SEMILLA = 42


def cargar() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    archivos = sorted(config.DIR_LANDMARKS.glob("*.npz"))
    if not archivos:
        raise SystemExit("No hay datos en data/landmarks. Ejecute primero scripts/preparar_dataset.py")
    X, y, g = [], [], []
    for a in archivos:
        d = np.load(a)
        X.append(d["X"]), y.append(d["y"]), g.append(d["grupos"])
        print(f"  {a.name}: {len(d['X'])} muestras")
    return np.concatenate(X), np.concatenate(y), np.concatenate(g)


def aumentar(X: np.ndarray, y: np.ndarray, copias: int, rng: np.random.Generator):
    """Rota ±15° y añade ruido leve: simula distintos ángulos de cámara y manos."""
    puntos = X.reshape(len(X), -1, 2)
    salida_X, salida_y = [X], [y]
    for _ in range(copias):
        ang = np.deg2rad(rng.uniform(-15, 15, size=len(X)))
        c, s = np.cos(ang)[:, None], np.sin(ang)[:, None]
        rot = np.stack([c * puntos[..., 0] - s * puntos[..., 1], s * puntos[..., 0] + c * puntos[..., 1]], axis=-1)
        rot += rng.normal(0, 0.02, size=rot.shape)
        salida_X.append(rot.reshape(len(X), -1).astype(np.float32))
        salida_y.append(y)
    return np.concatenate(salida_X), np.concatenate(salida_y)


def nuevo_modelo(arboles: int) -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=arboles, n_jobs=-1, random_state=SEMILLA, class_weight="balanced")


def evaluar(modelo, X, y) -> dict:
    proba = modelo.predict_proba(X)
    pred = modelo.classes_[proba.argmax(axis=1)]
    conf = proba.max(axis=1)
    aceptadas = conf >= config.UMBRAL_CONFIANZA
    return {
        "exactitud": accuracy_score(y, pred),
        "f1_macro": f1_score(y, pred, average="macro"),
        "cobertura": aceptadas.mean(),
        "exactitud_aceptadas": accuracy_score(y[aceptadas], pred[aceptadas]) if aceptadas.any() else float("nan"),
        "reporte": classification_report(y, pred, digits=3, zero_division=0),
        "matriz": confusion_matrix(y, pred, labels=modelo.classes_),
        "n": len(y),
    }


def bloque(titulo: str, r: dict, clases) -> str:
    cab = "     " + " ".join(f"{c:>4}" for c in clases)
    filas = "\n".join(f"{c:>4} " + " ".join(f"{v:>4}" for v in fila) for c, fila in zip(clases, r["matriz"]))
    return f"""## {titulo}

| Métrica | Valor |
|---|---|
| Muestras de prueba | {r['n']} |
| Exactitud (todas las predicciones) | {r['exactitud']:.1%} |
| F1 macro | {r['f1_macro']:.3f} |
| Cobertura con confianza ≥ {config.UMBRAL_CONFIANZA:.2f} | {r['cobertura']:.1%} |
| Exactitud de las predicciones con confianza ≥ {config.UMBRAL_CONFIANZA:.2f} | {r['exactitud_aceptadas']:.1%} |

<details><summary>Reporte por letra</summary>

```
{r['reporte']}
```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
{cab}
{filas}
```
</details>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sin-aumento", action="store_true")
    parser.add_argument("--copias-aumento", type=int, default=3)
    parser.add_argument("--arboles", type=int, default=150)
    args = parser.parse_args()
    rng = np.random.default_rng(SEMILLA)
    copias = 0 if args.sin_aumento else args.copias_aumento

    print("Cargando datos:")
    X, y, grupos = cargar()
    fuente = np.array([g.split("/")[0] for g in grupos])
    clases = sorted(set(y), key=config.LETRAS_ESTATICAS.index)
    secciones = []

    # 1) Evaluación por secuencias/ráfagas (80/20)
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEMILLA).split(X, y, grupos))
    Xa, ya = aumentar(X[tr], y[tr], copias, rng)
    modelo = nuevo_modelo(args.arboles).fit(Xa, ya)
    r = evaluar(modelo, X[te], y[te])
    print(f"\n[80/20 por secuencias] exactitud={r['exactitud']:.3f}  cobertura@0.80={r['cobertura']:.3f}  "
          f"exactitud@0.80={r['exactitud_aceptadas']:.3f}")
    secciones.append(bloque("Evaluación 80/20 separando secuencias completas", r, clases))

    # 2) Generalización a personas nuevas: entrenar sin una fuente y probar con ella
    propias = sorted(set(fuente) - {"externo"})
    for persona in propias:
        m = fuente == persona
        Xa, ya = aumentar(X[~m], y[~m], copias, rng)
        r = evaluar(nuevo_modelo(args.arboles).fit(Xa, ya), X[m], y[m])
        print(f"[sin datos de '{persona}', probado con '{persona}'] exactitud={r['exactitud']:.3f}")
        secciones.append(bloque(f"Generalización: modelo sin datos de «{persona}», probado con «{persona}»", r, clases))

    # 3) Tiempo de inferencia por cuadro (RNF-03). En la app se predice un cuadro a la vez:
    # ahí el paralelismo de joblib solo añade sobrecarga (~35 ms vs ~5 ms), por eso n_jobs=1.
    modelo.set_params(n_jobs=1)
    t = time.perf_counter()
    for i in range(200):
        modelo.predict_proba(X[i % len(X)].reshape(1, -1))
    ms = (time.perf_counter() - t) / 200 * 1000
    print(f"Inferencia: {ms:.2f} ms por cuadro")

    # Modelo final con todos los datos
    Xa, ya = aumentar(X, y, copias, rng)
    final = nuevo_modelo(args.arboles).fit(Xa, ya)
    final.set_params(n_jobs=1)
    metadatos = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "letras": clases,
        "muestras": int(len(X)),
        "fuentes": {f: int((fuente == f).sum()) for f in sorted(set(fuente))},
        "aumento_copias": copias,
        "sklearn": sklearn.__version__,
    }
    config.RUTA_MODELO_SENAS.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": final, "metadatos": metadatos}, config.RUTA_MODELO_SENAS, compress=3)
    print(f"\nModelo guardado en {config.RUTA_MODELO_SENAS}")

    fuentes = ", ".join(f"{k}: {v}" for k, v in metadatos["fuentes"].items())
    RUTA_REPORTE.parent.mkdir(parents=True, exist_ok=True)
    RUTA_REPORTE.write_text(
        f"""# Métricas del modelo de señas

Generado por `scripts/entrenar_modelo.py` el {metadatos['fecha']}.

- Clasificador: Random Forest ({args.arboles} árboles, scikit-learn {sklearn.__version__})
- Letras ({len(clases)}): {' '.join(clases)}
- Muestras originales: {len(X)} ({fuentes})
- Aumento de datos: {copias} copias rotadas ±15° con ruido gaussiano (solo en entrenamiento)
- Tiempo de inferencia: {ms:.2f} ms por cuadro

"""
        + "\n".join(secciones),
        encoding="utf-8",
    )
    print(f"Reporte en {RUTA_REPORTE}")


if __name__ == "__main__":
    main()
