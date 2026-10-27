"""Entrena el clasificador Random Forest de letras y genera modelos/modelo_senas.pkl.

Usa los archivos .npz de letras de data/landmarks: el dataset de JuanPlazas (una persona),
LSC70 (70 personas, scripts/preparar_lsc70.py) y las capturas propias (scripts/capturar_dataset.py).
La evaluación separa grupos completos entre entrenamiento y prueba (secuencias de JuanPlazas,
PERSONAS de LSC70 y ráfagas propias), nunca cuadros sueltos: la cifra que importa es la exactitud
con personas de LSC70 que el modelo no vio. Además, por cada fuente se mide un modelo entrenado
sin ella (p. ej. sin LSC70 = cómo le iba al modelo de una sola persona con 70 personas nuevas).

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
from sklearn.model_selection import GroupKFold

from silva import config, muestras_propias

RUTA_REPORTE = config.DIR_INFORMES / "metricas_modelo.md"
SEMILLA = 42
NOMBRE_FUENTE = {"externo": "JuanPlazas (1 persona)", "lsc70": "LSC70 (70 personas)",
                 "propias": "muestras propias (app)"}


def cargar() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    archivos = sorted(config.DIR_LANDMARKS.glob("*.npz"))
    if muestras_propias.RUTA_LETRAS.exists() and muestras_propias.RUTA_LETRAS not in archivos:
        archivos.append(muestras_propias.RUTA_LETRAS)  # en el ejecutable, las muestras propias están en la carpeta del usuario
    X, y, g = [], [], []
    for a in archivos:
        d = np.load(a, allow_pickle=True)
        if "X" not in d:  # p. ej. lsc54_secuencias.npz, que es del modo Palabras
            continue
        X.append(d["X"]), y.append(d["y"]), g.append(d["grupos"])
        print(f"  {a.name}: {len(d['X'])} muestras")
    if not X:
        raise SystemExit("No hay datos de letras en data/landmarks. Ejecute scripts/preparar_dataset.py")
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


def evaluar_probas(proba, clases, y) -> dict:
    pred = clases[proba.argmax(axis=1)]
    conf = proba.max(axis=1)
    aceptadas = conf >= config.UMBRAL_CONFIANZA
    return {
        "exactitud": accuracy_score(y, pred),
        "f1_macro": f1_score(y, pred, average="macro"),
        "cobertura": aceptadas.mean(),
        "exactitud_aceptadas": accuracy_score(y[aceptadas], pred[aceptadas]) if aceptadas.any() else float("nan"),
        "reporte": classification_report(y, pred, digits=3, zero_division=0),
        "matriz": confusion_matrix(y, pred, labels=clases),
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
| Cobertura con confianza ≥ {config.UMBRAL_CONFIANZA:.2f} (lo que la app escribe) | {r['cobertura']:.1%} |
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sin-aumento", action="store_true")
    parser.add_argument("--copias-aumento", type=int, default=3)
    parser.add_argument("--arboles", type=int, default=150)
    args = parser.parse_args(argv)
    rng = np.random.default_rng(SEMILLA)
    copias = 0 if args.sin_aumento else args.copias_aumento

    print("Cargando datos:")
    X, y, grupos = cargar()
    fuente = np.array([g.split("/")[0] for g in grupos])
    clases = sorted(set(y), key=config.LETRAS_ESTATICAS.index)
    secciones = []

    # 1) Validación cruzada por grupos (5 pliegues): personas de LSC70 / secuencias / ráfagas completas
    probas = np.zeros((len(X), len(clases)))
    for tr, te in GroupKFold(n_splits=5).split(X, y, grupos):
        Xa, ya = aumentar(X[tr], y[tr], copias, rng)
        modelo = nuevo_modelo(args.arboles).fit(Xa, ya)
        p = modelo.predict_proba(X[te])
        for j, cl in enumerate(modelo.classes_):
            probas[te, clases.index(cl)] = p[:, j]
    for nombre in sorted(set(fuente)):
        m = fuente == nombre
        r = evaluar_probas(probas[m], np.array(clases), y[m])
        quien = "personas no vistas" if nombre == "lsc70" else "grupos no vistos"
        print(f"[validación cruzada, {nombre}: {quien}] exactitud={r['exactitud']:.3f}  "
              f"cobertura@{config.UMBRAL_CONFIANZA:.2f}={r['cobertura']:.3f}  exactitud@{config.UMBRAL_CONFIANZA:.2f}={r['exactitud_aceptadas']:.3f}")
        secciones.append(bloque(f"Validación cruzada (5 pliegues por grupo): muestras de "
                                f"{NOMBRE_FUENTE.get(nombre, nombre)}, {quien}", r, clases))

    # 2) Generalización a una fuente entera: entrenar sin ella y probar con ella
    for nombre in sorted(set(fuente) - {"externo"}) if len(set(fuente)) > 1 else []:
        m = fuente == nombre
        Xa, ya = aumentar(X[~m], y[~m], copias, rng)
        r = evaluar_probas(nuevo_modelo(args.arboles).fit(Xa, ya).predict_proba(X[m]), np.array(clases), y[m])
        print(f"[sin datos de '{nombre}', probado con '{nombre}'] exactitud={r['exactitud']:.3f}  "
              f"cobertura@{config.UMBRAL_CONFIANZA:.2f}={r['cobertura']:.3f}")
        secciones.append(bloque(f"Generalización: modelo SIN {NOMBRE_FUENTE.get(nombre, nombre)}, "
                                f"probado con {NOMBRE_FUENTE.get(nombre, nombre)}", r, clases))

    # Modelo final con todos los datos
    Xa, ya = aumentar(X, y, copias, rng)
    final = nuevo_modelo(args.arboles).fit(Xa, ya)
    # 3) Tiempo de inferencia por cuadro (RNF-03). En la app se predice un cuadro a la vez:
    # ahí el paralelismo de joblib solo añade sobrecarga (~35 ms vs ~5 ms), por eso n_jobs=1.
    final.set_params(n_jobs=1)
    t = time.perf_counter()
    for i in range(200):
        final.predict_proba(X[i % len(X)].reshape(1, -1))
    ms = (time.perf_counter() - t) / 200 * 1000
    print(f"Inferencia: {ms:.2f} ms por cuadro")

    metadatos = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "letras": clases,
        "muestras": int(len(X)),
        "fuentes": {f: int((fuente == f).sum()) for f in sorted(set(fuente))},
        "aumento_copias": copias,
        "sklearn": sklearn.__version__,
    }
    destino = config.DIR_MODELOS_PROPIOS / "modelo_senas.pkl"
    destino.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": final, "metadatos": metadatos}, destino, compress=3)
    config.RUTA_MODELO_SENAS = destino
    print(f"\nModelo guardado en {destino}")

    fuentes = ", ".join(f"{NOMBRE_FUENTE.get(k, k)}: {v}" for k, v in metadatos["fuentes"].items())
    RUTA_REPORTE.parent.mkdir(parents=True, exist_ok=True)
    RUTA_REPORTE.write_text(
        f"""# Métricas del modelo de letras

Generado por `scripts/entrenar_modelo.py` el {metadatos['fecha']}.

- Clasificador: Random Forest ({args.arboles} árboles, scikit-learn {sklearn.__version__})
- Letras ({len(clases)}): {' '.join(clases)}
- Muestras: {len(X)} ({fuentes})
- Aumento de datos: {copias} copias rotadas ±15° con ruido gaussiano (solo en entrenamiento)
- Tiempo de inferencia: {ms:.2f} ms por cuadro

La cifra que representa el uso real es la de **LSC70 con personas no vistas**: el dataset de
JuanPlazas es de una sola persona, así que su validación cruzada es optimista.

"""
        + "\n".join(secciones),
        encoding="utf-8",
    )
    print(f"Reporte en {RUTA_REPORTE}")


if __name__ == "__main__":
    main()
