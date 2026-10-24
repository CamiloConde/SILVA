"""RF-07: persistencia del historial en SQLite."""

from silva.repositorio_historial import RepositorioHistorial


def test_guardar_y_listar_sesion(tmp_path):
    ruta = tmp_path / "historial.db"
    repo = RepositorioHistorial(ruta)
    sid = repo.iniciar_sesion()
    repo.registrar_letra(sid, "H", 0.91)
    repo.registrar_letra(sid, "I", 0.88)
    repo.guardar_sesion(sid, "HI")
    repo.cerrar()

    repo = RepositorioHistorial(ruta)  # persiste al reabrir
    sesiones = repo.listar_sesiones()
    assert len(sesiones) == 1
    assert sesiones[0].texto == "HI"
    assert sesiones[0].fin is not None
    assert repo.letras_de_sesion(sid) == [("H", 0.91), ("I", 0.88)]
    repo.cerrar()


def test_sesiones_mas_recientes_primero():
    repo = RepositorioHistorial(":memory:")
    a = repo.iniciar_sesion()
    b = repo.iniciar_sesion()
    assert [s.id for s in repo.listar_sesiones()] == [b, a]


def test_respuestas_del_oyente():
    repo = RepositorioHistorial(":memory:")
    sid = repo.iniciar_sesion()
    repo.registrar_respuesta(sid, "Gracias, ya le ayudo")
    repo.registrar_respuesta(None, "Buenos días")  # con la cámara apagada
    assert [(t, s) for _, t, s in repo.listar_respuestas()] == [("Buenos días", None), ("Gracias, ya le ayudo", sid)]
