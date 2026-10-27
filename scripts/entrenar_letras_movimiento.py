"""Entrena el clasificador de letras con movimiento y genera modelos/modelo_letras_movimiento.pkl.

Datos: data/landmarks/lsc70_secuencias.npz (scripts/preparar_lsc70_secuencias.py): las 27 letras
de LSC70, 70 personas, 6 cuadros por seña. El modelo aprende las 27 letras (para distinguir, p. ej.,
la Ñ de la N), pero en la app solo se escriben las letras con movimiento, y solo si la muñeca
recorrió al menos `config.RECORRIDO_MINIMO` tamaños de mano: pasar de una letra estática a otra
cambia la forma de la mano pero casi no la desplaza.

Para medir ese rechazo se arman transiciones (el final de una seña y el comienzo de otra, o el paso
directo de una forma a otra, de la misma persona). No se usan para entrenar: probado, enseñarle al
modelo una clase «transición» hecha así le hacía rechazar las letras con movimiento de verdad.

La evaluación separa personas completas (GroupKFold): la cifra que importa es cómo le va con
personas que el modelo nunca vio.

Uso:
    python scripts/entrenar_letras_movimiento.py [--arboles 200]
"""

from __future__ import annotations

import argparse
from datetime import datetime

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupKFold

from silva import config
from silva.letras_movimiento import (CUADROS, LETRAS_MOVIMIENTO, a_isotropicas, caracteristicas_secuencia,
                                     remuestrear)

ORIGEN = config.DIR_LANDMARKS / "lsc70_secuencias.npz"
RUTA_REPORTE = config.RAIZ_PROYECTO / "docs" / "metricas_letras_movimiento.md"
SEMILLA = 42
UMBRALES = (0.3, 0.4, 0.5, 0.6, 0.7)
RECORRIDO = -2  # índice del recorrido de la muñeca en el vector de caracteristicas_secuencia


def cargar():
    d = np.load(ORIGEN)
    puntos = a_isotropicas(d["puntos"], 640, 480)  # LSC70 y el modo Deletreo usan 640×480
    secuencias, izquierdas, letras, personas = [], [], [], []
    for p, iz, letra, persona in zip(puntos, d["izquierda"], d["letras"], d["personas"]):
        vistos = ~np.isnan(p[:, 0, 0])
        if vistos.sum() < 4:
            continue
        # cuadros sin mano: se interpolan entre los vecinos con mano
        t = np.arange(CUADROS)
        p = p.copy()
        for k in range(21):
            for c in range(2):
                p[:, k, c] = np.interp(t, t[vistos], p[vistos, k, c])
        secuencias.append(p.astype(np.float32))
        izquierdas.append(bool(iz[vistos].mean() >= 0.5))
        letras.append(str(letra))
        personas.append(str(persona))
    return secuencias, np.array(izquierdas), np.array(letras), np.array(personas)


def transiciones(secuencias, izquierdas, letras, personas, por_persona: int, rng):
    """Pasos de una letra estática a otra (solo para medir): el final de una seña y el comienzo de otra,
    de la misma persona. Después de una letra con movimiento la mano queda quieta y el trazo ya se cerró,
    así que lo que hay que rechazar en vivo son estos cambios entre letras estáticas."""
    salida = []
    estaticas = np.isin(letras, config.LETRAS_ESTATICAS)
    for persona in np.unique(personas):
        idx = np.flatnonzero((personas == persona) & estaticas)
        for _ in range(por_persona):
            a, b = rng.choice(idx, 2, replace=False)
            if letras[a] == letras[b]:
                continue
            corte = rng.integers(2, 5)
            if rng.random() < 0.5:  # media seña de cada una
                p = np.concatenate([secuencias[a][corte:], secuencias[b][:corte]])
            else:  # paso directo de la forma final de A a la inicial de B
                f = np.linspace(0, 1, CUADROS)[:, None, None]
                p = (1 - f) * secuencias[a][-1] + f * secuencias[b][0]
            salida.append((p.astype(np.float32), bool(izquierdas[a]), persona))
    return salida


def aumentar(p: np.ndarray, rng) -> np.ndarray:
    """Rota ±12°, cambia la escala, recorta un poco el principio o el final y añade ruido."""
    fino = remuestrear(p, 30)
    a, b = rng.integers(0, 5), 30 - rng.integers(0, 5)
    q = remuestrear(fino[a:b], CUADROS)
    ang = np.deg2rad(rng.uniform(-12, 12))
    rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]], np.float32)
    centro = q[0, 0]
    q = (q - centro) @ rot.T * rng.uniform(0.85, 1.15) + centro
    escala = float(np.linalg.norm(q[0, 9] - q[0, 0]))
    return (q + rng.normal(0, 0.03 * escala, q.shape)).astype(np.float32)


def matriz(muestras, copias: int, rng):
    X, y = [], []
    for p, iz, clase in muestras:
        X.append(caracteristicas_secuencia(p, iz))
        y.append(clase)
        for _ in range(copias):
            X.append(caracteristicas_secuencia(aumentar(p, rng), iz))
            y.append(clase)
    return np.array(X), np.array(y)


def nuevo_modelo(arboles: int) -> ExtraTreesClassifier:
    return ExtraTreesClassifier(n_estimators=arboles, n_jobs=-1, random_state=SEMILLA,
                                class_weight="balanced", min_samples_leaf=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arboles", type=int, default=200)
    parser.add_argument("--copias-aumento", type=int, default=4)
    parser.add_argument("--transiciones", type=int, default=40, help="transiciones de prueba por persona")
    args = parser.parse_args()
    rng = np.random.default_rng(SEMILLA)

    secuencias, izquierdas, letras, personas = cargar()
    muestras = [(p, iz, l) for p, iz, l in zip(secuencias, izquierdas, letras)]
    pruebas = transiciones(secuencias, izquierdas, letras, personas, args.transiciones, rng)
    X = np.array([caracteristicas_secuencia(p, iz) for p, iz, _ in muestras])
    X_trans = np.array([caracteristicas_secuencia(p, iz) for p, iz, _ in pruebas])
    personas_trans = np.array([g for *_, g in pruebas])
    print(f"{len(secuencias)} señas de {len(set(personas))} personas; {len(pruebas)} transiciones de prueba")

    # Validación cruzada por persona (las transiciones de prueba, con el modelo que no vio a esa persona)
    proba = proba_trans = clases = None
    for k, (tr, te) in enumerate(GroupKFold(n_splits=5).split(X, letras, personas)):
        Xa, ya = matriz([muestras[i] for i in tr], args.copias_aumento, rng)
        modelo = nuevo_modelo(args.arboles).fit(Xa, ya)
        if proba is None:
            clases = np.array(modelo.classes_)
            proba, proba_trans = np.zeros((len(X), len(clases))), np.zeros((len(X_trans), len(clases)))
        proba[te] = modelo.predict_proba(X[te])
        en_prueba = np.isin(personas_trans, np.unique(personas[te]))
        proba_trans[en_prueba] = modelo.predict_proba(X_trans[en_prueba])
        print(f"  pliegue {k + 1}/5")
    pred, conf = clases[proba.argmax(1)], proba.max(1)
    pred_trans, conf_trans = clases[proba_trans.argmax(1)], proba_trans.max(1)

    es_mov = np.isin(letras, LETRAS_MOVIMIENTO)
    exactitud_letras = accuracy_score(letras, pred)
    exactitud_mov = accuracy_score(letras[es_mov], pred[es_mov])
    print(f"Exactitud en las 27 letras (personas no vistas): {exactitud_letras:.1%}")
    print(f"Exactitud en las letras con movimiento: {exactitud_mov:.1%}")

    def acepta(p, c, x, u):
        return np.isin(p, LETRAS_MOVIMIENTO) & (c >= u) & (x[:, RECORRIDO] >= config.RECORRIDO_MINIMO)

    filas = []
    for u in UMBRALES:
        a = acepta(pred, conf, X, u)
        escritas = a[es_mov].mean()
        acierto = (pred[a & es_mov] == letras[a & es_mov]).mean() if (a & es_mov).any() else np.nan
        falsas_trans = acepta(pred_trans, conf_trans, X_trans, u).mean()
        falsas_est = a[~es_mov].mean()
        filas.append((u, escritas, acierto, falsas_trans, falsas_est))
        print(f"  umbral {u:.1f}: escribe {escritas:.1%} de las letras con movimiento, acierta {acierto:.1%}; "
              f"letra falsa en transiciones {falsas_trans:.1%}, en letras estáticas {falsas_est:.1%}")

    reporte = classification_report(letras[es_mov], pred[es_mov], labels=LETRAS_MOVIMIENTO,
                                     digits=3, zero_division=0)
    print(reporte)

    # Modelo final con todos los datos
    Xa, ya = matriz(muestras, args.copias_aumento, rng)
    final = nuevo_modelo(args.arboles).fit(Xa, ya)
    final.set_params(n_jobs=1)  # en la app se clasifica un movimiento a la vez
    metadatos = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "letras_movimiento": LETRAS_MOVIMIENTO,
        "senas": len(secuencias),
        "umbral": config.UMBRAL_MOVIMIENTO,
        "recorrido_minimo": config.RECORRIDO_MINIMO,
        "exactitud_movimiento": float(exactitud_mov),
        "sklearn": sklearn.__version__,
    }
    joblib.dump({"modelo": final, "metadatos": metadatos}, config.RUTA_MODELO_LETRAS_MOVIMIENTO, compress=3)
    print(f"Modelo guardado en {config.RUTA_MODELO_LETRAS_MOVIMIENTO}")

    tabla = "\n".join(f"| {u:.1f} | {e:.1%} | {a:.1%} | {t:.1%} | {s:.1%} |" for u, e, a, t, s in filas)
    RUTA_REPORTE.write_text(f"""# Métricas del modelo de letras con movimiento

Generado por `scripts/entrenar_letras_movimiento.py` el {metadatos['fecha']}.

- Clasificador: Extra Trees ({args.arboles} árboles, scikit-learn {sklearn.__version__})
- Datos: LSC70 (Muñoz Galindez et al., 2024), {len(secuencias)} señas de {len(set(personas))} personas, 6 cuadros por seña
- Clases: las 27 letras. Escribe solo {' '.join(LETRAS_MOVIMIENTO)}; M, N y P casi no se mueven en LSC70 y las reconoce el modelo de letras estáticas
- Regla de recorrido: la muñeca debe recorrer al menos {config.RECORRIDO_MINIMO} tamaños de mano (en LSC70 lo supera el 90 % de las letras con movimiento; la mediana de las estáticas es 0,1-0,35)
- Aumento: {args.copias_aumento} copias con rotación ±12°, escala, recorte temporal y ruido (solo en entrenamiento)
- Evaluación: validación cruzada de 5 pliegues por **persona** (personas no vistas)

| Métrica | Valor |
|---|---|
| Exactitud en las 27 letras | {exactitud_letras:.1%} |
| Exactitud en las letras con movimiento | {exactitud_mov:.1%} |

## Umbral de confianza

Una letra con movimiento se escribe si es la más probable, su probabilidad alcanza el umbral y la muñeca
recorrió lo suficiente. La app usa {config.UMBRAL_MOVIMIENTO}. Las transiciones son {len(pruebas)} pasos de una letra estática
a otra armados con señas de LSC70 (no se usaron para entrenar); cada una se clasifica con el modelo que no vio a esa persona.

| Umbral | Letras con movimiento escritas | Acierto de lo escrito | Letra falsa en transiciones | Letra falsa con letras estáticas |
|---|---|---|---|---|
{tabla}

<details><summary>Reporte por letra (letras con movimiento, sin umbral)</summary>

```
{reporte}
```
</details>

**Límite:** LSC70 trae 6 imágenes por seña, no el video, así que no se pudo medir aquí la segmentación
en vivo (cuándo empieza y termina el movimiento). Eso se prueba con la cámara.
""", encoding="utf-8")
    print(f"Reporte en {RUTA_REPORTE}")


if __name__ == "__main__":
    main()
