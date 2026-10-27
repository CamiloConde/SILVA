package co.edu.utb.silva.nucleo

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.text.Normalizer

/** Formas alternativas que también activan una seña (silva.animacion.VARIANTES). */
private val VARIANTES = mapOf("como estas" to "¿Cómo está?", "buen dia" to "Buenos días", "de nada" to "De nada", "lo siento" to "Lo siento")

/** Minúsculas, sin tildes ni signos, como en la app de PC (allí la ñ también queda como n). */
fun normalizarTexto(texto: String): String {
    val sinTildes = Normalizer.normalize(texto.lowercase(), Normalizer.Form.NFD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }
    return sinTildes.replace(Regex("[^a-z0-9ñ ]"), " ").split(" ").filter { it.isNotEmpty() }.joinToString(" ")
}

/** Promedio móvil (¼, ½, ¼) en el tiempo: quita el temblor de los puntos de la grabación (no la presencia de las manos). */
private fun suavizar(cuadros: List<FloatArray>): List<FloatArray> = cuadros.indices.map { k ->
    if (k == 0 || k == cuadros.size - 1) cuadros[k]
    else FloatArray(cuadros[k].size) { j ->
        if (j == N_POSE + 42 || j == N_POSE + N_MANO + 42) cuadros[k][j]
        else 0.25f * cuadros[k - 1][j] + 0.5f * cuadros[k][j] + 0.25f * cuadros[k + 1][j]
    }
}

/** Animaciones de esqueleto de cada palabra (scripts/generar_animaciones.py): 45 cuadros de 100 valores. */
class Animaciones(datos: ByteArray, val nombres: List<String>) {
    private val cuadros: Map<String, List<FloatArray>>
    private val porForma: Map<String, String>
    private val largoMax: Int

    init {
        val b = ByteBuffer.wrap(datos).order(ByteOrder.LITTLE_ENDIAN)
        val n = b.int
        val t = b.int
        val d = b.int
        require(n == nombres.size)
        val todos = FloatArray(n * t * d).also { b.asFloatBuffer().get(it) }
        cuadros = nombres.withIndex().associate { (i, nombre) ->
            nombre to suavizar(List(t) { k -> todos.copyOfRange((i * t + k) * d, (i * t + k + 1) * d) })
        }
        porForma = nombres.associateBy { normalizarTexto(it) } + VARIANTES.filterValues { it in cuadros }
        largoMax = porForma.keys.maxOf { it.split(" ").size }
    }

    fun cuadros(nombre: String): List<FloatArray> = cuadros.getValue(nombre)

    /** Señas conocidas que aparecen en el texto, en orden (las frases largas primero: «muchas gracias»). */
    fun buscar(texto: String): List<String> {
        val palabras = normalizarTexto(texto).split(" ").filter { it.isNotEmpty() }
        val encontradas = mutableListOf<String>()
        var i = 0
        while (i < palabras.size) {
            var largo = minOf(largoMax, palabras.size - i)
            var avanzo = false
            while (largo > 0) {
                val nombre = porForma[palabras.subList(i, i + largo).joinToString(" ")]
                if (nombre != null) {
                    encontradas.add(nombre)
                    i += largo
                    avanzo = true
                    break
                }
                largo--
            }
            if (!avanzo) i++
        }
        return encontradas
    }
}
