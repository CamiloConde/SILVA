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

/** Lo que ocupa la figura durante toda la seña (x0, y0, x1, y1), con la cabeza y parte del torso (silva.animacion). */
private fun cajaFigura(cuadros: List<FloatArray>): FloatArray {
    var x0 = Float.MAX_VALUE
    var y0 = Float.MAX_VALUE
    var x1 = -Float.MAX_VALUE
    var y1 = -Float.MAX_VALUE
    fun ver(x: Float, y: Float) {
        x0 = minOf(x0, x); x1 = maxOf(x1, x); y0 = minOf(y0, y); y1 = maxOf(y1, y)
    }
    for (f in cuadros) {
        for (i in 0 until N_POSE / 2) ver(f[2 * i], f[2 * i + 1])
        for (inicio in intArrayOf(N_POSE, N_POSE + N_MANO)) {
            if (f[inicio + 42] > 0f) for (k in 0 until 21) ver(f[inicio + 2 * k], f[inicio + 2 * k + 1])
        }
        ver(f[0] - 0.32f, f[1] - 0.42f)  // la cabeza
        ver(f[0] + 0.32f, f[1])
    }
    return floatArrayOf(x0 - 0.12f, y0 - 0.12f, x1 + 0.12f, maxOf(y1, 1.3f) + 0.12f)  // al menos hasta la mitad del torso
}

/** Escala y origen para que la caja quepa entera y centrada en un área de ancho × alto (silva.animacion.encuadre). */
fun encuadre(caja: FloatArray, ancho: Float, alto: Float): Triple<Float, Float, Float> {
    val escala = minOf(ancho / (caja[2] - caja[0]), alto / (caja[3] - caja[1]))
    return Triple(escala, ancho / 2 - (caja[0] + caja[2]) / 2 * escala, alto / 2 - (caja[1] + caja[3]) / 2 * escala)
}

/** Animaciones de cada palabra (scripts/generar_animaciones.py): 45 cuadros de 100 valores. */
class Animaciones(datos: ByteArray, val nombres: List<String>) {
    private val cuadros: Map<String, List<FloatArray>>
    private val cajas: Map<String, FloatArray>
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
        cajas = cuadros.mapValues { cajaFigura(it.value) }
        porForma = nombres.associateBy { normalizarTexto(it) } + VARIANTES.filterValues { it in cuadros }
        largoMax = porForma.keys.maxOf { it.split(" ").size }
    }

    fun cuadros(nombre: String): List<FloatArray> = cuadros.getValue(nombre)

    fun caja(nombre: String): FloatArray = cajas.getValue(nombre)

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

/**
 * Guía de cada letra del Deletreo (scripts/generar_animaciones.py, de LSC70): la mano derecha en 6 cuadros, en
 * tamaños de palma y centrada; en las letras con trazo, los cuadros muestran el movimiento.
 */
class GuiasLetras(datos: ByteArray, val letras: List<String>, private val trazo: List<Boolean>) {
    private val cuadros: Map<String, List<FloatArray>>

    init {
        val b = ByteBuffer.wrap(datos).order(ByteOrder.LITTLE_ENDIAN)
        val n = b.int
        val t = b.int
        val k = b.int
        require(n == letras.size && n == trazo.size)
        val todos = FloatArray(n * t * k * 2).also { b.asFloatBuffer().get(it) }
        cuadros = letras.withIndex().associate { (i, l) ->
            l to List(t) { j -> todos.copyOfRange((i * t + j) * k * 2, (i * t + j + 1) * k * 2) }
        }
    }

    fun cuadros(letra: String): List<FloatArray> = cuadros.getValue(letra)
    fun conTrazo(letra: String) = trazo[letras.indexOf(letra)]
}

/** La mano en el instante t (0-1) del trazo, interpolada entre los cuadros con un movimiento suave. */
fun manoEn(cuadros: List<FloatArray>, t: Float): FloatArray {
    val s = t * t * (3 - 2 * t)  // empieza y termina despacio
    val x = s * (cuadros.size - 1)
    val i = minOf(x.toInt(), cuadros.size - 2)
    val f = x - i
    return FloatArray(cuadros[i].size) { (1 - f) * cuadros[i][it] + f * cuadros[i + 1][it] }
}

/** El mismo movimiento con el recorrido de la muñeca reducido (factor < 1): la mano conserva su tamaño. */
fun acercarTrazo(cuadros: List<FloatArray>, factor: Float): List<FloatArray> {
    val x0 = cuadros[0][0]
    val y0 = cuadros[0][1]
    return cuadros.map { c ->
        val dx = (c[0] - x0) * (factor - 1)
        val dy = (c[1] - y0) * (factor - 1)
        FloatArray(c.size) { if (it % 2 == 0) c[it] + dx else c[it] + dy }
    }
}

