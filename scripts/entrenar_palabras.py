"""Entrena el clasificador de palabras (modo Palabras) con LSC-54 y genera modelos/modelo_palabras.pkl.

Además de las 33 expresiones de cortesía, el modelo aprende una clase de rechazo,
«otra cosa» (`__otra__`), con señas que NO están en el vocabulario (colores y números
de LSC-54). Sin ella, el modelo siempre elige una de las 33 y escribe palabras ante
cualquier movimiento: en la versión 1.0.0, el 81 % de los movimientos ajenos
terminaban escritos como una palabra.

La evaluación deja por fuera a firmantes completos (GroupKFold por firmante): mide
qué tan bien reconoce a personas que el modelo nunca vio y cuántas palabras falsas
escribe ante movimientos ajenos.

Uso:
    python scripts/entrenar_palabras.py [--negativas Colores,Numeros]
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
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupKFold

from silva import config
from silva.cuerpo import espejar
from silva.palabras import OTRA, recortar_activo, vector_secuencia

ORIGEN = config.DIR_LANDMARKS / "lsc54_secuencias.npz"
ORIGEN_LSC50 = config.DIR_LANDMARKS / "lsc50_secuencias.npz"  # scripts/preparar_lsc50.py (opcional)
RUTA_REPORTE = config.RAIZ_PROYECTO / "docs" / "metricas_palabras.md"
SEMILLA = 42
VOCABULARIO = "Cordialidad"
EXACTITUD_OBJETIVO = 0.95  # lo que la app escribe sola debe acertar al menos esto (lo dudoso se sugiere)…
FALSAS_MAXIMO = 0.15  # …y escribir (de forma provisional) a lo sumo esta fracción de movimientos ajenos
UMBRAL_SUGERENCIA = 0.12  # por debajo del umbral pero por encima de esto: «¿Quiso decir…?»
MARGEN_SUGERENCIA = 0.5  # para sugerir, la seña debe tener al menos la mitad de la probabilidad de «otra cosa»

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


def _norm_categoria(c: str) -> str:
    return unicodedata.normalize("NFC", c).replace("Números", "Numeros")


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
    return np.array(X), np.array(y, dtype=object), np.array(g), descartadas


def decidir(proba: np.ndarray, clases: np.ndarray, umbral: float):
    """La misma regla que la app: escribe la mejor seña conocida si supera el umbral y a «otra cosa»."""
    conocidas = clases != OTRA
    p_otra = proba[:, ~conocidas].max(axis=1) if (~conocidas).any() else np.zeros(len(proba))
    pc = proba[:, conocidas]
    mejor = clases[conocidas][pc.argmax(axis=1)]
    conf = pc.max(axis=1)
    top3 = clases[conocidas][np.argsort(-pc, axis=1)[:, :3]]
    escribe = (conf >= umbral) & (conf >= p_otra)
    sugiere = ~escribe & (conf >= UMBRAL_SUGERENCIA) & (conf >= MARGEN_SUGERENCIA * p_otra)
    return mejor, conf, escribe, sugiere, top3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--negativas", default="Colores,Numeros",
                        help="categorías de LSC-54 que se usan como «otra cosa» (vacío = sin rechazo)")
    parser.add_argument("--pliegues", type=int, default=6)
    parser.add_argument("--vocabulario", choices=["cortesia", "ampliado"], default="cortesia",
                        help="cortesia: las 33 de LSC-54 (las demás de LSC50 son «otra cosa»); "
                             "ampliado: además las señas de LSC50 que no están en LSC-54")
    parser.add_argument("--sin-lsc50", action="store_true", help="no usar LSC50 aunque esté disponible")
    args = parser.parse_args()

    d = np.load(ORIGEN, allow_pickle=True)
    secuencias = list(d["secuencias"])
    etiquetas_orig = list(d["etiquetas"].astype(object))
    firmantes = list(d["firmantes"].astype(str))
    cat = [_norm_categoria(c) for c in d["categorias"]]
    vocabulario = set(NOMBRES)  # las 33 de LSC-54
    if ORIGEN_LSC50.exists() and not args.sin_lsc50:  # LSC50: 5 personas más, de otro entorno de grabación
        d50 = np.load(ORIGEN_LSC50, allow_pickle=True)
        for s50, e50, f50 in zip(d50["secuencias"], d50["etiquetas"], d50["firmantes"]):
            secuencias.append(s50)
            etiquetas_orig.append(str(e50))
            firmantes.append(str(f50))
            en_vocab = str(e50) in vocabulario or args.vocabulario == "ampliado"
            cat.append(VOCABULARIO if en_vocab else "LSC50-otras")
    secuencias = np.array(secuencias, dtype=object)
    etiquetas_orig, firmantes, cat = np.array(etiquetas_orig, dtype=object), np.array(firmantes), np.array(cat)
    negativas = {_norm_categoria(c.strip()) for c in args.negativas.split(",") if c.strip()}
    if (cat == "LSC50-otras").any():
        negativas.add("LSC50-otras")
    m = (cat == VOCABULARIO) | np.isin(cat, list(negativas))
    secuencias, firmantes, cat, etiquetas_orig = secuencias[m], firmantes[m], cat[m], etiquetas_orig[m]
    etiquetas = np.where(cat == VOCABULARIO, etiquetas_orig, OTRA)
    es_pos = cat == VOCABULARIO
    n_vocab = len(set(etiquetas[es_pos]))
    print(f"{es_pos.sum()} videos de {n_vocab} señas + {(~es_pos).sum()} de «otra cosa» ({', '.join(sorted(negativas))}), "
          f"{len(set(firmantes))} firmantes")

    # Evaluación honesta: personas no vistas (GroupKFold por firmante) Y movimientos ajenos de una
    # categoría que el modelo no vio como «otra cosa» (se entrena con una categoría negativa y se
    # prueba con la otra). El espejo solo se agrega al entrenamiento.
    probas, reales, firmantes_te, clases_ref = [], [], [], None
    t0 = time.time()
    lista_firmantes = np.unique(firmantes)
    rondas = [(n, sorted(negativas - {n})) for n in sorted(negativas)] if len(negativas) > 1 else [(None, sorted(negativas))]
    for prueba_neg, entreno_neg in rondas:
        for k, (tr, te) in enumerate(GroupKFold(n_splits=args.pliegues).split(lista_firmantes, groups=lista_firmantes), 1):
            en_tr = np.isin(firmantes, lista_firmantes[tr])
            m_tr = en_tr & (es_pos | np.isin(cat, entreno_neg))
            Xtr, ytr, _, _ = construir(secuencias[m_tr], etiquetas[m_tr], firmantes[m_tr], con_espejo=True)
            modelo = nuevo_modelo().fit(Xtr, ytr)
            clases_ref = modelo.classes_ if clases_ref is None else clases_ref
            # Las señas reales se cuentan una sola vez (en la primera ronda)
            m_te = ~en_tr & ((es_pos if prueba_neg == rondas[0][0] else False) | (cat == prueba_neg))
            Xte, yte, gte, _ = construir(secuencias[m_te], etiquetas[m_te], firmantes[m_te], con_espejo=False)
            if len(Xte) == 0:  # p. ej. un pliegue sin ninguna de las 5 personas de LSC50
                continue
            p = modelo.predict_proba(Xte)
            alineada = np.zeros((len(p), len(clases_ref)))
            for j, c in enumerate(modelo.classes_):
                alineada[:, list(clases_ref).index(c)] = p[:, j]
            probas.append(alineada)
            reales += list(yte)
            firmantes_te += list(gte)
        print(f"  ronda: «otra cosa» de prueba = {prueba_neg} (entrenada con {', '.join(entreno_neg)})")
    proba, real = np.vstack(probas), np.array(reales, dtype=object)
    firmantes_te = np.array(firmantes_te)
    pos = real != OTRA

    # Curva de umbrales y elección
    curva = []
    for u in (round(0.10 + 0.05 * i, 2) for i in range(15)):
        mejor, conf, escribe, sugiere, top3 = decidir(proba, clases_ref, u)
        ep = escribe & pos
        curva.append({
            "u": u,
            "cobertura": ep.sum() / pos.sum(),
            "exactitud": (mejor[ep] == real[ep]).mean() if ep.any() else 1.0,
            "falsas": (escribe & ~pos).sum() / max((~pos).sum(), 1),
        })
    elegido = next((c for c in curva if c["exactitud"] >= EXACTITUD_OBJETIVO and c["falsas"] <= FALSAS_MAXIMO),
                   curva[-1])
    umbral = elegido["u"]
    mejor, conf, escribe, sugiere, top3 = decidir(proba, clases_ref, umbral)
    top1 = (mejor[pos] == real[pos]).mean()
    top3_ok = np.array([r in t for r, t in zip(real[pos], top3[pos])]).mean()
    sug_pos = sugiere & pos
    sug_util = np.array([r in t for r, t in zip(real[sug_pos], top3[sug_pos])]).mean() if sug_pos.any() else 0.0
    print(f"Exactitud (mejor de las {n_vocab}) con firmantes no vistos: {top1:.3f} · entre las 3 primeras: {top3_ok:.3f}"
          f"  ({time.time() - t0:.0f} s)")
    de50 = pos & np.char.startswith(firmantes_te.astype(str), "L50")
    top1_50 = (mejor[de50] == real[de50]).mean() if de50.any() else float("nan")
    top3_50 = np.array([r in t for r, t in zip(real[de50], top3[de50])]).mean() if de50.any() else float("nan")
    if de50.any():
        print(f"  …solo personas de LSC50 (otro entorno de grabación): mejor {top1_50:.3f} · entre 3: {top3_50:.3f}")
    sug_ruido = (sugiere & ~pos).sum() / max((~pos).sum(), 1)
    print(f"Sugerencias: {sugiere[pos].mean():.0%} de las señas reales (correcta entre las 3: {sug_util:.0%}); "
          f"por ruido: {sug_ruido:.0%}")
    print(f"Umbral {umbral:.2f}: escribe {elegido['cobertura']:.0%} de las señas con exactitud {elegido['exactitud']:.1%}; "
          f"palabras falsas en movimientos ajenos: {elegido['falsas']:.1%}")

    # Modelo final con todos los firmantes
    Xf, yf, _, descartadas = construir(secuencias, etiquetas, firmantes, con_espejo=True)
    final = nuevo_modelo().fit(Xf, yf)
    final.set_params(n_jobs=1)  # en vivo se clasifica una seña a la vez
    t = time.perf_counter()
    for i in range(20):
        final.predict_proba(Xf[i:i + 1])
    ms = (time.perf_counter() - t) / 20 * 1000

    nombres = {c: nombre_visible(c) for c in final.classes_ if c != OTRA}
    metadatos = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "vocabulario": args.vocabulario,
        "exactitud_lsc50": float(top1_50),
        "negativas": sorted(negativas),
        "firmantes": int(len(set(firmantes))),
        "exactitud_firmantes_no_vistos": float(top1),
        "umbral": umbral,
        "umbral_sugerencia": UMBRAL_SUGERENCIA,
        "sklearn": sklearn.__version__,
    }
    config.RUTA_MODELO_PALABRAS.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": final, "nombres": nombres, "metadatos": metadatos}, config.RUTA_MODELO_PALABRAS,
                compress=3)
    print(f"Modelo guardado en {config.RUTA_MODELO_PALABRAS} (inferencia {ms:.1f} ms por seña)")

    tabla = "\n".join(f"| {c['u']:.2f} | {c['cobertura']:.1%} | {c['exactitud']:.1%} | {c['falsas']:.1%} |"
                      for c in curva)
    reporte = classification_report([nombres[c] for c in real[pos]], [nombres[c] for c in mejor[pos]],
                                    digits=3, zero_division=0)
    RUTA_REPORTE.write_text(f"""# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el {metadatos['fecha']}.

- Datasets: LSC-54 (Mora-Zarate, 2025) y, si está, LSC50 (Flórez-Sierra et al., 2024).
  Vocabulario ({len(nombres)} señas): {', '.join(sorted(nombres.values()))}.
- Clase de rechazo «otra cosa»: señas de LSC-54 fuera del vocabulario ({', '.join(sorted(negativas))}),
  para que la app no escriba palabras ante cualquier movimiento.
- {len(secuencias)} videos de {len(set(firmantes))} firmantes; sin tramo activo detectado (descartados): {descartadas}
- Clasificador: Extra Trees (400 árboles, scikit-learn {sklearn.__version__}) sobre {Xf.shape[1]} características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: {ms:.1f} ms por seña

## Evaluación con firmantes no vistos ({args.pliegues} pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor de las {n_vocab} opciones) | {top1:.1%} |
| …solo con las personas de LSC50 (otro entorno de grabación) | {top1_50:.1%} (entre las 3 primeras: {top3_50:.1%}) |
| La seña correcta está entre las 3 primeras opciones | {top3_ok:.1%} |
| Umbral de confianza elegido | {umbral:.2f} |
| Señas reales que la app escribe sola | {elegido['cobertura']:.1%} |
| Exactitud de lo que escribe | {elegido['exactitud']:.1%} |
| Palabras falsas ante movimientos ajenos (categoría no vista) | {elegido['falsas']:.1%} |
| Señas reales que quedan como «¿Quiso decir…?» | {sug_pos.sum() / pos.sum():.1%} (la correcta está entre las 3 opciones en el {sug_util:.0%}) |

Regla de la app:
- Si la mejor seña conocida supera el umbral **y** a «otra cosa», se escribe de forma
  provisional, y quien esté en el computador puede corregirla o descartarla.
- Si solo supera {UMBRAL_SUGERENCIA} (y al menos la mitad de «otra cosa»), se muestra «¿Quiso decir…?»
  con 3 opciones, sin escribir nada.
- En otro caso, no se muestra nada.

El umbral es el menor que logra al menos {EXACTITUD_OBJETIVO:.0%} de exactitud en lo escrito y a lo sumo
{FALSAS_MAXIMO:.0%} de palabras falsas.

Las palabras falsas se miden de forma honesta: con movimientos de una categoría que el modelo
**no** usó como «otra cosa» (entrenando con números se prueba con colores, y al revés), hechos por
personas no vistas. Como el modelo final aprende con ambas categorías, en uso real debería ser algo
mejor ante esos movimientos; ante gestos cotidianos (rascarse, acomodarse) no está medido.
Las falsas quedan provisionales: se pueden descartar con X antes de que se escriban.

| Umbral | Señas escritas | Exactitud de lo escrito | Palabras falsas |
|---|---|---|---|
{tabla}

<details><summary>Reporte por seña (mejor opción)</summary>

```
{reporte}
```
</details>
""", encoding="utf-8")
    print(f"Reporte en {RUTA_REPORTE}")


if __name__ == "__main__":
    main()
