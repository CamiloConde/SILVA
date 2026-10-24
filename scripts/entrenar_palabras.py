"""Entrena el clasificador de palabras (modo Palabras) con LSC-54 y genera modelos/modelo_palabras.pkl.

La evaluación deja por fuera a firmantes completos (GroupKFold por firmante):
mide qué tan bien reconoce a personas que el modelo nunca vio, que es la
situación real de la app.

Uso:
    python scripts/entrenar_palabras.py [--categorias Cordialidad,Colores,Números]
"""

from __future__ import annotations

import argparse
import time
import unicodedata
from datetime import datetime

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupKFold

from silva import config
from silva.cuerpo import espejar
from silva.palabras import recortar_activo, vector_secuencia

ORIGEN = config.DIR_LANDMARKS / "lsc54_secuencias.npz"
RUTA_REPORTE = config.RAIZ_PROYECTO / "docs" / "metricas_palabras.md"
SEMILLA = 42
EXACTITUD_OBJETIVO = 0.90  # el umbral se elige para que lo que la app escribe acierte al menos esto

# Nombre para mostrar de cada carpeta del dataset
NOMBRES = {
    "Apoyar": "Apoyar", "Ayudar": "Ayudar", "Baño": "Baño", "Bien": "Bien", "Bienvenido": "Bienvenido",
    "Buenas Noches": "Buenas noches", "Buenas tardes": "Buenas tardes", "Buenos dias": "Buenos días",
    "Chao": "Chao", "Como esta": "¿Cómo está?", "Con gusto": "Con gusto", "Denada": "De nada",
    "Esperar": "Esperar", "Excelente": "Excelente", "Gracias": "Gracias", "Hola": "Hola",
    "Invitar": "Invitar", "Lo siento": "Lo siento", "Mal": "Mal", "Maso Menos": "Más o menos",
    "Muchas Gracias": "Muchas gracias", "Muy Bien": "Muy bien", "Muy mal": "Muy mal",
    "Necesitar": "Necesitar", "No": "No", "Perdon": "Perdón", "Perfecto": "Perfecto",
    "Permiso": "Permiso", "Por favor": "Por favor", "Presentar": "Presentar", "Sentarse": "Sentarse",
    "Si": "Sí", "Tranquilo": "Tranquilo",
}


def nombre_visible(clave: str) -> str:
    return NOMBRES.get(clave, clave[:1].upper() + clave[1:])


def elegir_umbral(confianza: np.ndarray, aciertos: np.ndarray) -> tuple[float, list[tuple[float, float, float]]]:
    """Menor umbral cuya exactitud (sobre las señas aceptadas) alcanza EXACTITUD_OBJETIVO."""
    curva = []
    for u in (round(0.10 + 0.05 * i, 2) for i in range(15)):  # 0.10 … 0.80, sin errores de redondeo
        m = confianza >= u
        curva.append((u, float(m.mean()), float(aciertos[m].mean()) if m.any() else 1.0))
    for u, _, exactitud in curva:
        if exactitud >= EXACTITUD_OBJETIVO:
            return u, curva
    return curva[-1][0], curva


def nuevo_modelo() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(n_estimators=400, max_features="sqrt", n_jobs=-1,
                                random_state=SEMILLA, class_weight="balanced")


def construir(secuencias, etiquetas, firmantes, con_espejo: bool):
    X, y, g, descartadas = [], [], [], 0
    for s, e, f in zip(secuencias, etiquetas, firmantes):
        tramo = recortar_activo(s)
        if tramo is None:
            descartadas += 1
            continue
        variantes = [tramo, espejar(tramo)] if con_espejo else [tramo]
        for v in variantes:
            X.append(vector_secuencia(v))
            y.append(e)
            g.append(f)
    return np.array(X), np.array(y), np.array(g), descartadas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--categorias", default="Cordialidad",
                        help="categorías a incluir, separadas por coma (Cordialidad, Colores, Números)")
    parser.add_argument("--pliegues", type=int, default=6)
    args = parser.parse_args()

    d = np.load(ORIGEN, allow_pickle=True)
    categorias = {unicodedata.normalize("NFC", c.strip()) for c in args.categorias.split(",")}
    cat = np.array([unicodedata.normalize("NFC", c) for c in d["categorias"]])
    m = np.isin(cat, list(categorias))
    secuencias, etiquetas, firmantes = d["secuencias"][m], d["etiquetas"][m], d["firmantes"][m]
    print(f"{m.sum()} videos, {len(set(etiquetas))} señas, {len(set(firmantes))} firmantes")

    X, y, g, descartadas = construir(secuencias, etiquetas, firmantes, con_espejo=False)
    print(f"Sin tramo activo (descartados): {descartadas}")

    # Evaluación: firmantes no vistos (el espejo solo se agrega al entrenamiento)
    pred_total, real_total, conf_total = [], [], []
    t0 = time.time()
    for k, (tr, te) in enumerate(GroupKFold(n_splits=args.pliegues).split(X, y, g), 1):
        Xtr, ytr, _, _ = construir(secuencias[np.isin(firmantes, g[tr])], etiquetas[np.isin(firmantes, g[tr])],
                                   firmantes[np.isin(firmantes, g[tr])], con_espejo=True)
        modelo = nuevo_modelo().fit(Xtr, ytr)
        proba = modelo.predict_proba(X[te])
        pred = modelo.classes_[proba.argmax(1)]
        pred_total += list(pred)
        real_total += list(y[te])
        conf_total += list(proba.max(1))
        print(f"  pliegue {k}: firmantes {sorted(set(g[te]), key=int)} exactitud={accuracy_score(y[te], pred):.3f}")
    pred_total, real_total, conf_total = map(np.array, (pred_total, real_total, conf_total))
    exactitud = accuracy_score(real_total, pred_total)
    umbral, curva = elegir_umbral(conf_total, pred_total == real_total)
    aceptadas = conf_total >= umbral
    exactitud_mostradas = accuracy_score(real_total[aceptadas], pred_total[aceptadas])
    print(f"Exactitud con firmantes no vistos: {exactitud:.3f}  ({time.time() - t0:.0f} s)")
    print(f"Umbral elegido {umbral:.2f}: se muestran {aceptadas.mean():.0%} de las señas, "
          f"con exactitud {exactitud_mostradas:.3f}")

    # Modelo final con todos los firmantes
    Xf, yf, _, _ = construir(secuencias, etiquetas, firmantes, con_espejo=True)
    final = nuevo_modelo().fit(Xf, yf)
    final.set_params(n_jobs=1)  # en vivo se clasifica una seña a la vez
    t = time.perf_counter()
    for i in range(20):
        final.predict_proba(X[i:i + 1])
    ms = (time.perf_counter() - t) / 20 * 1000

    nombres = {c: nombre_visible(c) for c in final.classes_}
    metadatos = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "categorias": sorted(categorias),
        "videos": int(m.sum()),
        "firmantes": int(len(set(firmantes))),
        "exactitud_firmantes_no_vistos": float(exactitud),
        "umbral": umbral,
        "sklearn": sklearn.__version__,
    }
    config.RUTA_MODELO_PALABRAS.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": final, "nombres": nombres, "metadatos": metadatos}, config.RUTA_MODELO_PALABRAS,
                compress=3)
    print(f"Modelo guardado en {config.RUTA_MODELO_PALABRAS} (inferencia {ms:.1f} ms por seña)")

    tabla_curva = "\n".join(f"| {u:.2f} | {c:.1%} | {e:.1%} |" for u, c, e in curva)
    reporte = classification_report(
        [nombres[c] for c in real_total], [nombres[c] for c in pred_total], digits=3, zero_division=0)
    RUTA_REPORTE.write_text(f"""# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el {metadatos['fecha']}.

- Dataset: LSC-54 (Mora-Zarate, 2025), categorías: {', '.join(sorted(categorias))}
- {m.sum()} videos de {len(set(firmantes))} firmantes, {len(final.classes_)} señas: {', '.join(nombres.values())}
- Videos sin tramo activo detectado (descartados): {descartadas}
- Clasificador: Extra Trees (400 árboles, scikit-learn {sklearn.__version__}) sobre {len(X[0])} características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: {ms:.1f} ms por seña

## Evaluación con firmantes no vistos ({args.pliegues} pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor opción del modelo) | {exactitud:.1%} |
| F1 macro | {f1_score(real_total, pred_total, average='macro'):.3f} |
| Umbral de confianza elegido | {umbral:.2f} |
| Señas que la app escribe (confianza ≥ umbral) | {aceptadas.mean():.1%} |
| Exactitud de las señas que escribe | {exactitud_mostradas:.1%} |

Las señas por debajo del umbral no se escriben: la app pide repetirlas. El umbral es el menor
que logra al menos {EXACTITUD_OBJETIVO:.0%} de exactitud en lo que se escribe.

| Umbral | Señas escritas | Exactitud de lo escrito |
|---|---|---|
{tabla_curva}

<details><summary>Reporte por seña</summary>

```
{reporte}
```
</details>
""", encoding="utf-8")
    print(f"Reporte en {RUTA_REPORTE}")


if __name__ == "__main__":
    main()
