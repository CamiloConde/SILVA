"""Exporta los modelos y las animaciones a la app Android (movil/) y genera sus casos de prueba.

Los tres clasificadores son bosques de árboles de scikit-learn. Se guardan en un binario compacto
que la app recorre igual que scikit-learn, así que el teléfono reconoce exactamente como el PC:

    cabecera: b"SILVAARB", versión, árboles, características, clases (int32, little-endian)
    por árbol: nodos (int32); característica (int16, -1 = hoja); umbral (float32); hijo derecho
               (int32; el izquierdo es siempre el nodo siguiente). En una hoja, el campo del hijo
               derecho guarda la clase si la hoja es pura, o -(posición + 1) de su distribución en la
               tabla del árbol: [k, clase, prob, clase, prob, ...] (float32).

El umbral se redondea hacia abajo a float32: como las características son float32, x <= umbral32
equivale a x <= umbral64 (la comparación de scikit-learn).

Además escribe movil/app/src/test/resources/casos.json con entradas reales y lo que responde Python
(características y probabilidades), que las pruebas de la app comparan con su propio cálculo.

Uso:
    python scripts/exportar_movil.py
    python scripts/exportar_movil.py --paquete dist/silva_modelo.zip   (solo el paquete para «Importar modelo»)
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

import joblib
import numpy as np

from silva import config, palabras
from silva.cuerpo import CuadroCuerpo, asignar_manos, caracteristicas_cuadro, evaluar_encuadre
from silva.detector_manos import normalizar_landmarks
from silva.letras_movimiento import a_isotropicas, caracteristicas_secuencia
from silva.modelo import Landmark

sys.path.insert(0, str(config.RAIZ_PROYECTO / "scripts"))

MOVIL = config.RAIZ_PROYECTO / "movil" / "app" / "src"
ASSETS = MOVIL / "main" / "assets"
CASOS = MOVIL / "test" / "resources" / "casos.json"


def escribir_bosque(modelo, destino) -> None:
    partes = [b"SILVAARB", struct.pack("<4i", 1, len(modelo.estimators_), modelo.n_features_in_, len(modelo.classes_))]
    for estimador in modelo.estimators_:
        t = estimador.tree_
        hoja = t.children_left == -1
        assert (t.children_left[~hoja] == np.flatnonzero(~hoja) + 1).all()
        umbral = t.threshold.astype(np.float32)
        arriba = umbral.astype(np.float64) > t.threshold
        umbral[arriba] = np.nextafter(umbral[arriba], np.float32(-np.inf))
        caracteristica = np.where(hoja, -1, t.feature).astype(np.int16)
        derecho = t.children_right.astype(np.int32)
        tabla: list[float] = []
        valores = t.value[:, 0, :]
        for i in np.flatnonzero(hoja):
            v = valores[i] / valores[i].sum()
            clases = np.flatnonzero(v > 0)
            if len(clases) == 1:
                derecho[i] = clases[0]
            else:
                derecho[i] = -(len(tabla) + 1)
                tabla.append(len(clases))
                for c in clases:
                    tabla += [c, v[c]]
            umbral[i] = 0
        partes += [struct.pack("<i", t.node_count), caracteristica.tobytes(), umbral.tobytes(), derecho.tobytes(),
                   struct.pack("<i", len(tabla)), np.array(tabla, np.float32).tobytes()]
    destino.write_bytes(b"".join(partes))
    print(f"  {destino.name}: {destino.stat().st_size / 1e6:.1f} MB")


def lista(a, decimales=7):
    return np.round(np.asarray(a, np.float64), decimales).tolist()


def exportar_paquete(destino: Path, origen: str) -> None:
    """Los tres clasificadores y su índice en un .zip, para «Entrenar → Importar modelo» en el teléfono."""
    letras = joblib.load(config.RUTA_MODELO_SENAS)["modelo"]
    movimiento = joblib.load(config.RUTA_MODELO_LETRAS_MOVIMIENTO)["modelo"]
    paquete_palabras = joblib.load(config.RUTA_MODELO_PALABRAS)
    metadatos_palabras = paquete_palabras.get("metadatos", {})
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        escribir_bosque(letras, carpeta / "letras.bin")
        escribir_bosque(movimiento, carpeta / "letras_movimiento.bin")
        escribir_bosque(paquete_palabras["modelo"], carpeta / "palabras.bin")
        indice = {
            "origen": origen,
            "letras": {"clases": [str(c) for c in letras.classes_]},
            "letras_movimiento": {"clases": [str(c) for c in movimiento.classes_]},
            "palabras": {
                "clases": [str(c) for c in paquete_palabras["modelo"].classes_],
                "nombres": paquete_palabras.get("nombres", {}),
                "umbral": float(metadatos_palabras.get("umbral", 0.5)),
                "umbral_sugerencia": float(metadatos_palabras.get("umbral_sugerencia", 0.12)),
            },
        }
        (carpeta / "modelos.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
        destino.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            for nombre in ("letras.bin", "letras_movimiento.bin", "palabras.bin", "modelos.json"):
                z.write(carpeta / nombre, nombre)
    print(f"Paquete para el teléfono: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--paquete", type=Path, help="solo crear este .zip para importarlo en el teléfono")
    parser.add_argument("--origen", default="modelo propio", help="descripción que muestra el teléfono")
    args = parser.parse_args()
    if args.paquete:
        exportar_paquete(args.paquete, args.origen)
        return
    (ASSETS / "modelos").mkdir(parents=True, exist_ok=True)
    CASOS.parent.mkdir(parents=True, exist_ok=True)

    letras = joblib.load(config.RUTA_MODELO_SENAS)["modelo"]
    movimiento = joblib.load(config.RUTA_MODELO_LETRAS_MOVIMIENTO)
    paquete_palabras = joblib.load(config.RUTA_MODELO_PALABRAS)
    print("Modelos:")
    escribir_bosque(letras, ASSETS / "modelos" / "letras.bin")
    escribir_bosque(movimiento["modelo"], ASSETS / "modelos" / "letras_movimiento.bin")
    escribir_bosque(paquete_palabras["modelo"], ASSETS / "modelos" / "palabras.bin")
    for ruta in (config.RUTA_MODELO_MANOS, config.RUTA_MODELO_POSE):
        shutil.copy(ruta, ASSETS / "modelos" / ruta.name)

    animaciones = np.load(config.RUTA_ANIMACIONES)
    nombres_anim = [str(n) for n in animaciones["nombres"]]
    cuadros_anim = animaciones["animaciones"].astype(np.float32)
    (ASSETS / "modelos" / "animaciones.bin").write_bytes(struct.pack("<3i", *cuadros_anim.shape) + cuadros_anim.tobytes())

    metadatos_palabras = paquete_palabras.get("metadatos", {})
    indice = {
        "letras": {"clases": [str(c) for c in letras.classes_]},
        "letras_movimiento": {"clases": [str(c) for c in movimiento["modelo"].classes_]},
        "palabras": {
            "clases": [str(c) for c in paquete_palabras["modelo"].classes_],
            "nombres": paquete_palabras.get("nombres", {}),
            "umbral": float(metadatos_palabras.get("umbral", 0.5)),
            "umbral_sugerencia": float(metadatos_palabras.get("umbral_sugerencia", 0.12)),
        },
        "animaciones": nombres_anim,
    }
    (ASSETS / "modelos" / "modelos.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------------------------------------------------------------- casos de prueba
    rng = np.random.default_rng(7)
    casos: dict = {"config": {
        "UMBRAL_CONFIANZA": config.UMBRAL_CONFIANZA, "CUADROS_ESTABLES": config.CUADROS_ESTABLES,
        "MOVIMIENTO_INICIO": config.MOVIMIENTO_INICIO, "MOVIMIENTO_FIN": config.MOVIMIENTO_FIN,
        "CUADROS_QUIETO": config.CUADROS_QUIETO, "MIN_CUADROS_MOVIMIENTO": config.MIN_CUADROS_MOVIMIENTO,
        "MAX_CUADROS_MOVIMIENTO": config.MAX_CUADROS_MOVIMIENTO, "UMBRAL_MOVIMIENTO": config.UMBRAL_MOVIMIENTO,
        "RECORRIDO_MINIMO": config.RECORRIDO_MINIMO, "SEGUNDOS_INICIO_TRAZO": config.SEGUNDOS_INICIO_TRAZO,
        "LONGITUD_FIJA": palabras.LONGITUD_FIJA, "MIN_ACTIVOS": palabras.MIN_ACTIVOS,
        "MAX_CUADROS": palabras.MAX_CUADROS, "CUADROS_FIN": palabras.CUADROS_FIN, "MARGEN": palabras.MARGEN,
        "ALTURA_ACTIVA": palabras.ALTURA_ACTIVA, "MOVIMIENTO_ACTIVO": palabras.MOVIMIENTO_ACTIVO,
        "BRILLO_MINIMO": config.BRILLO_MINIMO, "ENCUADRE_HOMBROS": list(config.ENCUADRE_HOMBROS),
        "ENCUADRE_CENTRO_X": list(config.ENCUADRE_CENTRO_X), "ENCUADRE_NARIZ_Y_MIN": config.ENCUADRE_NARIZ_Y_MIN,
        "ENCUADRE_HOMBROS_Y_MAX": config.ENCUADRE_HOMBROS_Y_MAX,
        "RECORTE_RECUPERACION": config.RECORTE_RECUPERACION, "TAM_RECORTE": config.TAM_RECORTE,
        "CONFIANZA_RECUPERACION": config.CONFIANZA_RECUPERACION,
        "CONFIANZA_MANOS_PALABRAS": config.CONFIANZA_MANOS_PALABRAS, "CONFIANZA_DETECCION": config.CONFIANZA_DETECCION,
    }}

    # Letras: landmarks crudos de LSC70 → normalización → probabilidades
    d70 = np.load(config.DIR_LANDMARKS / "lsc70_secuencias.npz")
    casos_letras = []
    for i in rng.choice(np.flatnonzero(~np.isnan(d70["puntos"][:, 2, 0, 0])), 12, replace=False):
        puntos, izquierda = d70["puntos"][i, 2], bool(d70["izquierda"][i, 2])
        vector = normalizar_landmarks([Landmark(float(x), float(y)) for x, y in puntos], izquierda)
        casos_letras.append({"puntos": lista(puntos), "izquierda": izquierda, "vector": lista(vector),
                             "proba": lista(letras.predict_proba(np.array([vector], np.float32))[0], 6)})
    casos["letras"] = casos_letras

    # Letras con movimiento: secuencias de LSC70 → 264 características → probabilidades
    completas = np.flatnonzero(~np.isnan(d70["puntos"][:, :, 0, 0]).any(axis=1))
    casos_mov = []
    for i in rng.choice(completas, 10, replace=False):
        puntos = a_isotropicas(d70["puntos"][i], 640, 480)
        izquierda = bool(d70["izquierda"][i].mean() >= 0.5)
        x = caracteristicas_secuencia(puntos, izquierda)
        casos_mov.append({"puntos": lista(puntos), "izquierda": izquierda, "vector": lista(x),
                          "proba": lista(movimiento["modelo"].predict_proba(x.reshape(1, -1))[0], 6)})
    casos["letras_movimiento"] = casos_mov

    # Cuerpo: asignación de manos, vector de cuadro y encuadre, con poses inventadas
    casos_cuerpo = []
    for _ in range(6):
        pose = [Landmark(float(x), float(y)) for x, y in rng.uniform(0.2, 0.8, (33, 2))]
        manos = [[Landmark(float(x), float(y)) for x, y in rng.uniform(0.1, 0.9, (21, 2))] for _ in range(rng.integers(0, 3))]
        izq, der = asignar_manos(pose, manos)
        c = CuadroCuerpo(pose, izq, der, 16 / 9)
        casos_cuerpo.append({
            "pose": [[p.x, p.y] for p in pose], "manos": [[[p.x, p.y] for p in m] for m in manos],
            "izquierda": None if izq is None else manos.index(izq), "derecha": None if der is None else manos.index(der),
            "vector": lista(caracteristicas_cuadro(c)), "encuadre": evaluar_encuadre(c),
        })
    casos["cuerpo"] = casos_cuerpo

    # Palabras: secuencias reales de LSC-54 → segmentación en vivo, vector de 5 580 y probabilidades
    d54 = np.load(config.DIR_LANDMARKS / "lsc54_secuencias.npz", allow_pickle=True)
    clasificador = palabras.ClasificadorPalabras()
    casos_palabras = []
    for i in rng.choice(np.flatnonzero(d54["categorias"] == "Cordialidad"), 6, replace=False):
        s = d54["secuencias"][i].astype(np.float32)
        seg = palabras.SegmentadorSenas()
        terminadas = []
        for f in np.concatenate([s, np.repeat(s[-1:], 15, axis=0)]):  # reposo final para cerrar la seña
            e = seg.agregar(None if np.isnan(f[0]) else f)
            if e.terminada is not None:
                terminadas.append(e.terminada)
        tramo = palabras.recortar_activo(s)
        if tramo is None or not terminadas:
            continue
        ev = clasificador.evaluar(terminadas[0])
        casos_palabras.append({
            "cuadros": [None if np.isnan(f[0]) else lista(f) for f in s],
            "terminada": len(terminadas[0]),
            "vector": lista(palabras.vector_secuencia(terminadas[0])),
            "opciones": [[o.letra, round(o.confianza, 6)] for o in ev.opciones[:3]],
            "prob_otra": round(ev.prob_otra, 6),
        })
    casos["palabras"] = casos_palabras

    # Animaciones: búsqueda de señas en un texto
    from silva.animacion import AnimacionesSenas
    a = AnimacionesSenas()
    casos["animaciones"] = [{"texto": t, "senas": a.buscar(t)} for t in
                            ("Hola, ¿cómo estás?", "Muchas gracias, con gusto le ayudo", "buen día, por favor espere", "nada")]

    # «¿Quisiste decir?»: la lista de palabras va a la app y se comparan las sugerencias
    shutil.copy(config.RUTA_PALABRAS_ES, ASSETS / "modelos" / "palabras_es.txt")
    from silva.sugerencias import Sugerencias
    s = Sugerencias()
    casos["sugerencias"] = [{"texto": t, "opciones": s.para(t)} for t in
                            ("HOLA MUN", "GRA", "BUENOS DI", "MUS", "PEQUEÑ", "A", "HOLA ")]

    CASOS.write_text(json.dumps(casos, ensure_ascii=False), encoding="utf-8")
    print(f"Casos de prueba: {CASOS} ({CASOS.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
