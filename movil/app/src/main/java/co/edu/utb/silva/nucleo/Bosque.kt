package co.edu.utb.silva.nucleo

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Bosque de árboles de decisión exportado de scikit-learn (scripts/exportar_movil.py).
 *
 * Recorre cada árbol igual que scikit-learn (x <= umbral → hijo izquierdo, que es el nodo siguiente)
 * y promedia las probabilidades de las hojas, así que da las mismas respuestas que la app de PC.
 */
class Bosque(datos: ByteArray) {
    val nCaracteristicas: Int
    val nClases: Int
    private val arboles: List<Arbol>

    private class Arbol(
        val caracteristica: ShortArray,
        val umbral: FloatArray,
        val derecho: IntArray,
        val tabla: FloatArray,
    )

    init {
        val b = ByteBuffer.wrap(datos).order(ByteOrder.LITTLE_ENDIAN)
        val firma = ByteArray(8).also { b.get(it) }
        require(String(firma, Charsets.US_ASCII) == "SILVAARB") { "No es un modelo de SILVA" }
        require(b.int == 1) { "Versión de modelo no soportada" }
        val nArboles = b.int
        nCaracteristicas = b.int
        nClases = b.int
        arboles = List(nArboles) {
            val n = b.int
            val caracteristica = ShortArray(n).also { b.asShortBuffer().get(it); b.position(b.position() + 2 * n) }
            val umbral = FloatArray(n).also { b.asFloatBuffer().get(it); b.position(b.position() + 4 * n) }
            val derecho = IntArray(n).also { b.asIntBuffer().get(it); b.position(b.position() + 4 * n) }
            val m = b.int
            val tabla = FloatArray(m).also { b.asFloatBuffer().get(it); b.position(b.position() + 4 * m) }
            Arbol(caracteristica, umbral, derecho, tabla)
        }
    }

    /** Probabilidad de cada clase (en el orden de `classes_` de scikit-learn). */
    fun probabilidades(x: FloatArray): DoubleArray {
        require(x.size == nCaracteristicas) { "Se esperaban $nCaracteristicas características, llegaron ${x.size}" }
        val proba = DoubleArray(nClases)
        for (a in arboles) {
            var nodo = 0
            while (true) {
                val f = a.caracteristica[nodo].toInt()
                if (f < 0) break
                nodo = if (x[f] <= a.umbral[nodo]) nodo + 1 else a.derecho[nodo]
            }
            val r = a.derecho[nodo]
            if (r >= 0) {
                proba[r] += 1.0
            } else {
                val inicio = -r - 1
                val k = a.tabla[inicio].toInt()
                for (j in 0 until k) {
                    proba[a.tabla[inicio + 1 + 2 * j].toInt()] += a.tabla[inicio + 2 + 2 * j].toDouble()
                }
            }
        }
        for (c in proba.indices) proba[c] /= arboles.size
        return proba
    }
}

data class Prediccion(val texto: String, val confianza: Double)
