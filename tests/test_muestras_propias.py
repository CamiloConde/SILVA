"""Muestras grabadas con la app del teléfono (Entrenar) → datos de entrenamiento."""
import gzip
import json

import numpy as np

from silva import muestras_propias as mp


def _archivo(tmp_path, muestras, nombre="silva_muestras.jsonl.gz"):
    ruta = tmp_path / nombre
    with gzip.open(ruta, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"formato": "silva-muestras", "version": 1}) + "\n")
        for m in muestras:
            f.write(json.dumps(m) + "\n")
    return ruta


def _mano(dx=0.0):
    return [[0.5 + dx + 0.01 * k, 0.5 + 0.02 * k] for k in range(21)]


MUESTRAS = [
    {"tipo": "palabra", "clave": "Hola", "persona": "Camilo Andrés", "fecha": "2026-10-27 10:00:00",
     "cuadros": [[0.1] * 100] * 12, "fps": 15.0},
    {"tipo": "letra", "clave": "A", "persona": "Camilo Andrés", "fecha": "2026-10-27 10:01:00",
     "cuadros": [[0.2] * 42] * 30, "puntos": [_mano()] * 30, "izquierda": False},
    {"tipo": "trazo", "clave": "J", "persona": "Miguel", "fecha": "2026-10-27 10:02:00",
     "puntos": [_mano(0.02 * t) for t in range(9)], "izquierda": True},
    {"tipo": "palabra", "clave": "NoExiste", "persona": "Miguel", "fecha": "2026-10-27 10:03:00",
     "cuadros": [[0.1] * 100] * 12},
]


def test_lee_y_separa_por_modelo(tmp_path):
    muestras = mp.leer(_archivo(tmp_path, MUESTRAS))
    datos = mp.reunir(muestras, {"Hola"})
    assert datos["secuencias"]["etiquetas"] == ["Hola"]
    assert datos["secuencias"]["firmantes"] == ["P-camilo_andres"]
    assert np.array(datos["letras"]["X"]).shape == (30, 42)
    assert set(datos["letras"]["grupos"]) == {"propias/camilo_andres"}
    # la letra quieta también entra a los trazos (6 cuadros), y el trazo se remuestrea a 6
    assert datos["trazos"]["letras"] == ["A", "J"]
    assert all(np.asarray(p).shape == (6, 21, 2) for p in datos["trazos"]["puntos"])
    assert [o[1] for o in datos["omitidas"]] == ["NoExiste"]


def test_el_mismo_archivo_dos_veces_no_duplica(tmp_path):
    a = mp.leer(_archivo(tmp_path, MUESTRAS, "a.jsonl.gz"))
    b = mp.leer(_archivo(tmp_path, MUESTRAS, "b.jsonl.gz"))
    datos = mp.reunir(a + b, {"Hola"})
    assert len(datos["secuencias"]["secuencias"]) == 1
    assert len(datos["trazos"]["letras"]) == 2


def test_rechaza_archivos_que_no_son_de_silva(tmp_path):
    ruta = tmp_path / "otro.jsonl.gz"
    with gzip.open(ruta, "wt", encoding="utf-8") as f:
        f.write('{"formato": "otra-cosa"}\n')
    try:
        mp.leer(ruta)
    except ValueError:
        return
    raise AssertionError("debió rechazar el archivo")


def test_grabador_del_pc_escribe_lo_que_lee_el_entrenamiento(tmp_path):
    g = mp.GrabadorMuestras(tmp_path)
    g.palabra("Hola", "Juan Diego", np.full((12, 100), 0.1, np.float32), 29.7)
    g.letra("B", "Juan Diego", [np.full(42, 0.3)] * 30, [np.array(_mano())] * 30, False)
    g.trazo("Z", "Juan Diego", np.array([_mano(0.02 * t) for t in range(8)], np.float32), False)
    assert g.total == 3 and g.cuantas("palabra", "Hola") == 1
    assert g.borrar_ultima() == ("trazo", "Z")
    assert g.total == 2
    # otro grabador ve lo que quedó en la carpeta
    assert mp.GrabadorMuestras(tmp_path).total == 2
    datos = mp.reunir([m for a in mp.archivos(tmp_path) for m in mp.leer(a)], {"Hola"})
    assert datos["secuencias"]["firmantes"] == ["P-juan_diego"]
    assert np.array(datos["letras"]["X"]).shape == (30, 42)
    assert datos["trazos"]["letras"] == ["B"]
