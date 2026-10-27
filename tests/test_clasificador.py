"""RF-03: el clasificador preentrenado devuelve (letra, confianza)."""

import numpy as np
import pytest

from silva import config
from silva.clasificador import ClasificadorPreentrenado


@pytest.fixture(scope="module")
def clasificador():
    if not config.RUTA_MODELO_SENAS.exists():
        pytest.skip("Falta modelos/modelo_senas.pkl (scripts/entrenar_modelo.py)")
    return ClasificadorPreentrenado()


def test_cubre_las_letras_estaticas(clasificador):
    assert clasificador.letras == sorted(config.LETRAS_ESTATICAS)


def test_prediccion_valida(clasificador, datos_externos):
    X, _ = datos_externos
    p = clasificador.predecir(X[0].tolist())
    assert p.letra in config.LETRAS_ESTATICAS
    assert 0.0 <= p.confianza <= 1.0


def test_acierta_una_muestra_por_letra(clasificador, datos_externos):
    X, y = datos_externos
    for letra in sorted(set(y)):  # JuanPlazas no trae M, N ni P (salen de LSC70)
        i = int(np.flatnonzero(y == letra)[0])
        assert clasificador.predecir(X[i].tolist()).letra == letra


def test_modelo_faltante(tmp_path):
    with pytest.raises(FileNotFoundError):
        ClasificadorPreentrenado(tmp_path / "no_existe.pkl")
