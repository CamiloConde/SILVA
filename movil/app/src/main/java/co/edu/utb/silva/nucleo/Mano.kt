package co.edu.utb.silva.nucleo

import kotlin.math.hypot

/** Punto en coordenadas normalizadas de imagen (0-1). */
data class Punto(val x: Float, val y: Float)

val CONEXIONES_MANO = listOf(
    0 to 1, 1 to 2, 2 to 3, 3 to 4,
    0 to 5, 5 to 6, 6 to 7, 7 to 8,
    0 to 9, 9 to 10, 10 to 11, 11 to 12,
    0 to 13, 13 to 14, 14 to 15, 15 to 16,
    0 to 17, 17 to 18, 18 to 19, 19 to 20,
    5 to 9, 9 to 13, 13 to 17,
)

/**
 * 21 puntos de la mano → 42 valores invariantes a posición y escala (silva.detector_manos).
 * Muñeca como origen, x espejada para la mano izquierda, escala = muñeca-nudillo del dedo medio.
 */
fun normalizarLandmarks(puntos: List<Punto>, izquierda: Boolean): FloatArray {
    require(puntos.size == 21) { "Se esperaban 21 puntos, llegaron ${puntos.size}" }
    val m = puntos[0]
    val dx = DoubleArray(21) { val d = puntos[it].x.toDouble() - m.x; if (izquierda) -d else d }
    val dy = DoubleArray(21) { puntos[it].y.toDouble() - m.y }
    val escala = hypot(dx[9], dy[9])
    return FloatArray(42) { i ->
        val v = if (i % 2 == 0) dx[i / 2] else dy[i / 2]
        (if (escala > 0) v / escala else v).toFloat()
    }
}

/** Letra a partir de una sola imagen de la mano (modo Deletreo, letras estáticas). */
class ClasificadorLetras(private val bosque: Bosque, val letras: List<String>) {
    fun predecir(caracteristicas: FloatArray): Prediccion {
        val p = bosque.probabilidades(caracteristicas)
        val i = p.indices.maxBy { p[it] }
        return Prediccion(letras[i], p[i])
    }
}
