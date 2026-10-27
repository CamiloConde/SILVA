"""Reentrena los modelos de SILVA con las muestras grabadas en la app del teléfono (sección «Entrenar»).

    python scripts/entrenar_con_muestras.py [silva_muestras_20261027_1530.jsonl.gz …]

1. Copia los archivos a data/propias/. Ahí se acumulan: cada vez se usan todas las muestras importadas.
   La app de PC graba directamente ahí (Entrenar), así que en ese caso no hace falta pasar archivos.
2. Las convierte al formato de cada modelo (silva.muestras_propias).
3. Mide si el modelo nuevo los reconoce mejor a ustedes: el modelo actual (antes) contra un modelo que
   aprendió con sus otras tomas pero no con la que se prueba (después).
4. Reentrena los modelos que tienen muestras propias. Sus informes en docs/ siguen midiendo la exactitud
   con personas que el modelo nunca vio, para comprobar que no empeora con los demás.
5. Crea dist/silva_modelo_<fecha>.zip (desde el ejecutable, en Descargas), para «Entrenar → Más… → Importar
   modelo» en el teléfono.

Opciones:
  --rapido      en el paso 4 entrena solo los modelos finales, sin las validaciones de los informes (unos minutos
                en vez de 20-30; el umbral de palabras es el del modelo actual). Es lo que usa la app (Entrenar).
  --solo-medir  pasos 1 a 3.
  --sin-medir   salta el paso 3, que tarda unos minutos.
Las muestras son datos de personas (puntos del cuerpo y las manos): data/propias/ no se sube a git.
"""
from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import GroupKFold

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from silva import config, muestras_propias as mp  # noqa: E402
from silva.letras_movimiento import caracteristicas_secuencia  # noqa: E402
from silva.palabras import OTRA, vector_secuencia  # noqa: E402

SEMILLA = 42


def _pliegues(tomas: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    unicas = np.unique(tomas)
    k = min(4, len(unicas))
    return list(GroupKFold(n_splits=k).split(tomas, groups=tomas)) if k >= 2 else []


def medir_palabras() -> tuple[int, float, float] | None:
    """Palabras escritas bien (regla de la app): antes y después, con tomas propias no vistas."""
    if not mp.RUTA_SECUENCIAS.exists():
        return None
    import entrenar_palabras as ep
    d = np.load(mp.RUTA_SECUENCIAS, allow_pickle=True)
    sec, etq, fir, tomas = d["secuencias"], d["etiquetas"].astype(object), d["firmantes"], d["tomas"]
    X_prop = np.array([vector_secuencia(s) for s in sec])  # como en vivo: la seña tal como la cortó la app

    def escritas_bien(modelo, X, real, umbral):
        mejor, _, escribe, _, _ = ep.decidir(modelo.predict_proba(X), modelo.classes_, umbral)
        return (escribe & (mejor == real)).mean()

    paquete = joblib.load(config.RUTA_MODELO_PALABRAS)
    umbral = paquete["metadatos"].get("umbral", 0.2)
    antes = escritas_bien(paquete["modelo"], X_prop, etq, umbral)
    pliegues = _pliegues(tomas)
    if not pliegues:
        return len(sec), antes, float("nan")
    b_sec, b_etq, b_fir, _, _ = ep.cargar_datos(sin_propias=True)
    Xb, yb, _, _ = ep.construir(b_sec, b_etq, b_fir, con_espejo=True)
    aciertos = np.zeros(len(sec))
    for k, (tr, te) in enumerate(pliegues, 1):
        Xp, yp, _, _ = ep.construir(sec[tr], etq[tr], fir[tr], con_espejo=True)
        modelo = ep.nuevo_modelo().fit(np.vstack([Xb, Xp]), np.concatenate([yb, yp]))
        mejor, _, escribe, _, _ = ep.decidir(modelo.predict_proba(X_prop[te]), modelo.classes_, umbral)
        aciertos[te] = escribe & (mejor == etq[te])
        print(f"  palabras: pliegue {k} de {len(pliegues)}")
    return len(sec), antes, aciertos.mean()


def medir_letras() -> tuple[int, float, float] | None:
    """Letras quietas: cuadros reconocidos con confianza ≥ umbral de la app, antes y después."""
    if not mp.RUTA_LETRAS.exists():
        return None
    import entrenar_modelo as em
    d = np.load(mp.RUTA_LETRAS)
    Xp, yp, tomas = d["X"], d["y"], d["tomas"]

    def bien(modelo, X, real):
        proba = modelo.predict_proba(X)
        return (proba.max(axis=1) >= config.UMBRAL_CONFIANZA) & (modelo.classes_[proba.argmax(axis=1)] == real)

    antes = bien(joblib.load(config.RUTA_MODELO_SENAS)["modelo"], Xp, yp).mean()
    pliegues = _pliegues(tomas)
    if not pliegues:
        return len(np.unique(tomas)), antes, float("nan")
    X, y, g = em.cargar()
    base = ~np.char.startswith(g.astype(str), "propias/")
    rng = np.random.default_rng(SEMILLA)
    resultado = np.zeros(len(Xp), dtype=bool)
    for k, (tr, te) in enumerate(pliegues, 1):
        Xa, ya = em.aumentar(np.vstack([X[base], Xp[tr]]), np.concatenate([y[base], yp[tr]]), 3, rng)
        resultado[te] = bien(em.nuevo_modelo(150).fit(Xa, ya), Xp[te], yp[te])
        print(f"  letras: pliegue {k} de {len(pliegues)}")
    return len(np.unique(tomas)), antes, resultado.mean()


def medir_trazos() -> tuple[int, float, float] | None:
    """Letras con trazo: trazos reconocidos como la letra correcta con confianza ≥ umbral, antes y después."""
    if not mp.RUTA_TRAZOS.exists():
        return None
    import entrenar_letras_movimiento as elm
    d = np.load(mp.RUTA_TRAZOS)
    es_trazo = ~np.isin(d["letras"], config.LETRAS_ESTATICAS)  # se miden solo las letras con movimiento
    if not es_trazo.any():
        return None
    puntos, izq, letras, tomas = d["puntos"], d["izquierda"], d["letras"], d["tomas"]
    X_prop = np.array([caracteristicas_secuencia(p, iz) for p, iz in zip(puntos, izq)])

    def bien(modelo, X, real):
        proba = modelo.predict_proba(X)
        return (proba.max(axis=1) >= config.UMBRAL_MOVIMIENTO) & (modelo.classes_[proba.argmax(axis=1)] == real)

    antes = bien(joblib.load(config.RUTA_MODELO_LETRAS_MOVIMIENTO)["modelo"], X_prop[es_trazo], letras[es_trazo]).mean()
    pliegues = _pliegues(tomas)
    if not pliegues:
        return int(es_trazo.sum()), antes, float("nan")
    secuencias, izquierdas, todas, personas = elm.cargar()
    base = [(p, iz, l) for p, iz, l, pe in zip(secuencias, izquierdas, todas, personas) if not str(pe).startswith("propias/")]
    rng = np.random.default_rng(SEMILLA)
    resultado = np.zeros(len(letras), dtype=bool)
    for k, (tr, te) in enumerate(pliegues, 1):
        propias = [(puntos[i], bool(izq[i]), str(letras[i])) for i in tr]
        Xa, ya = elm.matriz(base + propias, 4, rng)
        resultado[te] = bien(elm.nuevo_modelo(200).fit(Xa, ya), X_prop[te], letras[te])
        print(f"  trazos: pliegue {k} de {len(pliegues)}")
    return int(es_trazo.sum()), antes, resultado[es_trazo].mean()


def entrenar_rapido() -> None:
    """Solo los modelos finales, con la misma receta que los scripts de entrenamiento pero sin sus validaciones."""
    destino = config.DIR_MODELOS_PROPIOS
    destino.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().isoformat(timespec="seconds")
    rng = np.random.default_rng(SEMILLA)
    if mp.RUTA_LETRAS.exists():
        import entrenar_modelo as em
        print("\nLetras quietas…")
        X, y, g = em.cargar()
        Xa, ya = em.aumentar(X, y, 3, rng)
        final = em.nuevo_modelo(150).fit(Xa, ya)
        final.set_params(n_jobs=1)  # en la app se predice un cuadro a la vez
        fuente = np.array([s.split("/")[0] for s in g])
        metadatos = {"fecha": fecha, "letras": sorted(set(y), key=config.LETRAS_ESTATICAS.index), "muestras": int(len(X)),
                     "fuentes": {f: int((fuente == f).sum()) for f in sorted(set(fuente))}, "aumento_copias": 3,
                     "entrenamiento": "rápido (con muestras propias)"}
        joblib.dump({"modelo": final, "metadatos": metadatos}, destino / "modelo_senas.pkl", compress=3)
        config.RUTA_MODELO_SENAS = destino / "modelo_senas.pkl"
    if mp.RUTA_TRAZOS.exists():
        import entrenar_letras_movimiento as elm
        print("Letras con trazo…")
        secuencias, izquierdas, letras, _ = elm.cargar()
        Xa, ya = elm.matriz(list(zip(secuencias, izquierdas, letras)), 4, rng)
        final = elm.nuevo_modelo(200).fit(Xa, ya)
        final.set_params(n_jobs=1)
        metadatos = {"fecha": fecha, "letras_movimiento": elm.LETRAS_MOVIMIENTO, "senas": len(secuencias),
                     "umbral": config.UMBRAL_MOVIMIENTO, "recorrido_minimo": config.RECORRIDO_MINIMO,
                     "entrenamiento": "rápido (con muestras propias)"}
        joblib.dump({"modelo": final, "metadatos": metadatos}, destino / "modelo_letras_movimiento.pkl", compress=3)
        config.RUTA_MODELO_LETRAS_MOVIMIENTO = destino / "modelo_letras_movimiento.pkl"
    if mp.RUTA_SECUENCIAS.exists():
        import entrenar_palabras as ep
        print("Palabras…")
        anterior = joblib.load(config.RUTA_MODELO_PALABRAS).get("metadatos", {})
        secuencias, etiquetas, firmantes, _, _ = ep.cargar_datos()
        X, y, _, _ = ep.construir(secuencias, etiquetas, firmantes, con_espejo=True)
        final = ep.nuevo_modelo().fit(X, y)
        nombres = {c: ep.nombre_visible(c) for c in final.classes_ if c != OTRA}
        metadatos = {**anterior, "fecha": fecha, "firmantes": int(len(set(firmantes))),
                     "muestras_propias": int(np.char.startswith(firmantes.astype(str), "P-").sum()),
                     "entrenamiento": "rápido (con muestras propias; umbral del modelo anterior)"}
        joblib.dump({"modelo": final, "nombres": nombres, "metadatos": metadatos}, destino / "modelo_palabras.pkl",
                    compress=3)
        config.RUTA_MODELO_PALABRAS = destino / "modelo_palabras.pkl"
    print(f"Modelos guardados en {destino}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archivos", nargs="*", type=Path, help="archivos .jsonl.gz exportados por la app")
    parser.add_argument("--rapido", action="store_true", help="solo los modelos finales (sin las validaciones)")
    parser.add_argument("--solo-medir", action="store_true", help="medir sin reentrenar ni crear el paquete")
    parser.add_argument("--sin-medir", action="store_true", help="reentrenar sin la medición antes/después")
    args = parser.parse_args(argv)

    # 1) Copiar los archivos nuevos
    mp.DIR_PROPIAS.mkdir(parents=True, exist_ok=True)
    for a in args.archivos:
        if not a.exists():
            raise SystemExit(f"No existe {a}")
        mp.leer(a)  # comprueba el formato antes de copiarlo
        if not (mp.DIR_PROPIAS / a.name).exists():
            shutil.copy(a, mp.DIR_PROPIAS / a.name)
    archivos = mp.archivos()
    if not archivos:
        raise SystemExit("No hay muestras: grábelas en la app (Entrenar) o pase los archivos exportados por el teléfono.")

    # 2) Convertirlas
    muestras = [m for a in archivos for m in mp.leer(a)]
    clases = joblib.load(config.RUTA_MODELO_PALABRAS)["modelo"].classes_
    datos = mp.reunir(muestras, {str(c) for c in clases if c != OTRA})
    cuentas = mp.guardar(datos)
    personas = sorted({mp.persona_id(str(m.get("persona", ""))) for m in muestras})
    print(f"{len(archivos)} archivos, {len(muestras)} muestras de {len(personas)} personas ({', '.join(personas)}): "
          + ", ".join(f"{v} {k}" for k, v in cuentas.items()))
    for tipo, clave, motivo in datos["omitidas"]:
        print(f"  omitida: {tipo} «{clave}» ({motivo})")

    # 3) ¿Los reconoce mejor?
    if not args.sin_medir:
        print("\nMidiendo con sus tomas (el modelo «después» no vio la toma que se prueba)…")
        filas = [("Palabras: escritas bien", medir_palabras()), ("Letras quietas: cuadros reconocidos", medir_letras()),
                 ("Letras con trazo: reconocidas", medir_trazos())]
        print("\n| Modelo | Muestras | Antes (modelo actual) | Después (con sus muestras) |\n|---|---|---|---|")
        for nombre, r in filas:
            if r is not None:
                n, antes, despues = r
                txt = "hace falta más de una toma" if np.isnan(despues) else f"{despues:.0%}"
                print(f"| {nombre} | {n} | {antes:.0%} | {txt} |")
    if args.solo_medir:
        return

    # 4) Reentrenar los modelos que tienen muestras propias
    if args.rapido:
        entrenar_rapido()
    else:
        scripts = [("letras quietas", "entrenar_modelo", mp.RUTA_LETRAS),
                   ("letras con trazo", "entrenar_letras_movimiento", mp.RUTA_TRAZOS),
                   ("palabras", "entrenar_palabras", mp.RUTA_SECUENCIAS)]
        for nombre, script, ruta in scripts:
            if ruta.exists():
                print(f"\nReentrenando {nombre} ({script}.py)…")
                if config.EMPAQUETADO:  # dentro del ejecutable no hay un Python aparte: se entrena aquí mismo
                    importlib.import_module(script).main([])
                else:
                    subprocess.run([sys.executable, str(RAIZ / "scripts" / f"{script}.py")], check=True, cwd=RAIZ)

    # 5) Paquete para el teléfono
    import exportar_movil
    fecha = datetime.now()
    carpeta = Path.home() / "Downloads" if config.EMPAQUETADO else RAIZ / "dist"
    destino = carpeta / f"silva_modelo_{fecha:%Y%m%d_%H%M}.zip"
    origen = f"propio, del {fecha:%d/%m/%Y} ({len(muestras)} muestras de {len(personas)} personas)"
    exportar_movil.exportar_paquete(destino, origen)
    print(f"\nListo. Para el teléfono: pase {destino} e impórtelo en Entrenar → Más… → Importar modelo.")


if __name__ == "__main__":
    main()
