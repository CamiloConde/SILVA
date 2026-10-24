"""RF-04: confirmar solo con confianza >= 0,80 y 5 cuadros estables."""

from silva.buffer_texto import BufferTexto
from silva.modelo import Prediccion


def alimentar(buffer, letra, confianza, veces):
    return [buffer.procesar(Prediccion(letra, confianza)) for _ in range(veces)]


def test_confirma_al_quinto_cuadro_estable():
    b = BufferTexto()
    resultados = alimentar(b, "A", 0.9, 5)
    assert resultados == [None, None, None, None, "A"]
    assert b.texto == "A"


def test_no_confirma_con_confianza_baja():
    b = BufferTexto()
    alimentar(b, "A", 0.79, 20)
    assert b.texto == ""


def test_confianza_exactamente_en_el_umbral_si_cuenta():
    b = BufferTexto()
    alimentar(b, "A", 0.80, 5)
    assert b.texto == "A"


def test_prediccion_inestable_reinicia_la_racha():
    b = BufferTexto()
    alimentar(b, "A", 0.9, 4)
    b.procesar(Prediccion("B", 0.9))
    alimentar(b, "A", 0.9, 4)
    assert b.texto == ""


def test_un_cuadro_de_baja_confianza_reinicia_la_racha():
    b = BufferTexto()
    alimentar(b, "A", 0.9, 4)
    b.procesar(Prediccion("A", 0.5))
    alimentar(b, "A", 0.9, 4)
    assert b.texto == ""


def test_mantener_la_sena_no_repite_la_letra():
    b = BufferTexto()
    alimentar(b, "L", 0.95, 30)
    assert b.texto == "L"


def test_retirar_la_mano_permite_repetir_letra():
    b = BufferTexto()
    alimentar(b, "L", 0.95, 5)
    b.procesar(None)
    alimentar(b, "L", 0.95, 5)
    assert b.texto == "LL"


def test_cambiar_de_letra_y_volver():
    b = BufferTexto()
    alimentar(b, "A", 0.9, 5)
    alimentar(b, "B", 0.9, 5)
    alimentar(b, "A", 0.9, 5)
    assert b.texto == "ABA"


def test_espacio_borrar_y_limpiar():
    b = BufferTexto()
    b.agregar_espacio()
    assert b.texto == ""  # no se empieza con espacio
    alimentar(b, "A", 0.9, 5)
    b.agregar_espacio()
    b.agregar_espacio()
    assert b.texto == "A "
    b.borrar_ultima()
    assert b.texto == "A"
    b.limpiar()
    assert b.texto == ""


def test_progreso():
    b = BufferTexto()
    alimentar(b, "A", 0.9, 2)
    assert b.progreso == 0.4
