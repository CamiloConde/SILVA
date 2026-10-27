package co.edu.utb.silva.nucleo

import kotlin.math.hypot

/*
 * Modo Palabras (silva.palabras): cada cuadro es un vector de 100 valores; el segmentador decide
 * cuándo empieza y termina una seña; la seña se remuestrea a 20 cuadros y se clasifica.
 */

const val OTRA = "__otra__"  // clase de rechazo: movimientos que no son ninguna seña conocida

private val I_MUNECA = intArrayOf(N_POSE, N_POSE + N_MANO)  // inicio de cada mano; la muñeca es el punto 0
private val I_MUNECAS_POSE = intArrayOf(10, 12)  // muñecas de la pose dentro del bloque de pose

private fun munecas(f: FloatArray): List<FloatArray> =
    I_MUNECA.filter { f[it + 42] > 0f }.map { floatArrayOf(f[it], f[it + 1]) }

/** Alguna muñeca (de la mano o, si se perdió, de la pose) está por encima del reposo. */
private fun levantada(f: FloatArray, munecas: List<FloatArray>): Boolean =
    munecas.any { it[1] < Config.ALTURA_ACTIVA } || I_MUNECAS_POSE.any { f[it + 1] < Config.ALTURA_ACTIVA }

private fun distancia(a: FloatArray, b: FloatArray): Double =
    hypot(a[0].toDouble() - b[0], a[1].toDouble() - b[1])

data class EstadoSegmentador(val grabando: Boolean, val cuadros: Int, val terminada: List<FloatArray>?)

/** Máquina de estados reposo → seña → reposo sobre el flujo de cuadros en vivo. */
class SegmentadorSenas {
    private val previo = ArrayDeque<FloatArray>()
    private var actual = mutableListOf<FloatArray>()
    private var reposo = 0
    private var activos = 0
    private var munecasPrevias: List<FloatArray> = emptyList()

    val grabando get() = actual.isNotEmpty()

    fun reiniciar() {
        previo.clear()
        actual = mutableListOf()
        reposo = 0
        activos = 0
        munecasPrevias = emptyList()
    }

    private fun esActivo(f: FloatArray): Boolean {
        val m = munecas(f)
        val arriba = levantada(f, m)
        val movida = munecasPrevias.isNotEmpty() && m.isNotEmpty() &&
            m.any { a -> munecasPrevias.minOf { distancia(a, it) } > Config.MOVIMIENTO_ACTIVO }
        munecasPrevias = m
        return arriba || movida
    }

    /** f = vector del cuadro, o null si no hay pose (el cuadro se ignora). */
    fun agregar(f: FloatArray?): EstadoSegmentador {
        if (f == null) return EstadoSegmentador(grabando, actual.size, null)
        val activo = esActivo(f)
        var terminada: List<FloatArray>? = null
        if (actual.isEmpty()) {
            if (activo) {
                actual = (previo + f).toMutableList()
                reposo = 0
                activos = 1
            } else {
                previo.addLast(f)
                while (previo.size > Config.MARGEN) previo.removeFirst()
            }
        } else {
            actual.add(f)
            reposo = if (activo) 0 else reposo + 1
            if (activo) activos++
            if (reposo >= Config.CUADROS_FIN || actual.size >= Config.MAX_CUADROS) {
                var seq: List<FloatArray> = actual
                if (reposo >= Config.CUADROS_FIN) seq = seq.subList(0, seq.size - reposo + Config.MARGEN)
                if (activos >= Config.MIN_ACTIVOS) terminada = seq.toList()
                actual = mutableListOf()
                previo.clear()
                reposo = 0
            }
        }
        return EstadoSegmentador(grabando, actual.size, terminada)
    }
}

/** np.interp(x, xp, fp) con xp creciente. */
internal fun interp(x: Double, xp: DoubleArray, fp: DoubleArray): Double {
    if (x <= xp[0]) return fp[0]
    if (x >= xp[xp.size - 1]) return fp[fp.size - 1]
    var lo = 0
    var hi = xp.size - 1
    while (hi - lo > 1) {
        val mid = (lo + hi) / 2
        if (xp[mid] <= x) lo = mid else hi = mid
    }
    if (x == xp[lo]) return fp[lo]
    val pendiente = (fp[hi] - fp[lo]) / (xp[hi] - xp[lo])
    return pendiente * (x - xp[lo]) + fp[lo]
}

/** np.linspace(0, 1, n). */
internal fun linspace01(n: Int): DoubleArray {
    if (n == 1) return doubleArrayOf(0.0)
    val paso = 1.0 / (n - 1)
    return DoubleArray(n) { if (it == n - 1) 1.0 else it * paso }
}

/** Interpola la mano en los cuadros donde se perdió entre dos detecciones. */
fun rellenarManos(cuadros: List<FloatArray>): List<FloatArray> {
    val s = cuadros.map { it.copyOf() }
    for (i in I_MUNECA) {
        val presentes = s.indices.filter { s[it][i + 42] > 0f }
        if (presentes.size < 2 || presentes.size == s.size) continue
        val xp = DoubleArray(presentes.size) { presentes[it].toDouble() }
        val primero = presentes.first()
        val ultimo = presentes.last()
        val huecos = s.indices.filter { s[it][i + 42] <= 0f && it > primero && it < ultimo }
        if (huecos.isEmpty()) continue
        for (j in i until i + 42) {
            val fp = DoubleArray(presentes.size) { s[presentes[it]][j].toDouble() }
            for (t in huecos) s[t][j] = interp(t.toDouble(), xp, fp).toFloat()
        }
        for (t in huecos) s[t][i + 42] = 1f
    }
    return s
}

/** Lleva la secuencia a n cuadros por interpolación lineal. */
fun remuestrear(cuadros: List<FloatArray>, n: Int = Config.LONGITUD_FIJA): Array<DoubleArray> {
    val tOrig = linspace01(cuadros.size)
    val tNuevo = linspace01(n)
    val d = cuadros[0].size
    val salida = Array(n) { DoubleArray(d) }
    for (j in 0 until d) {
        val fp = DoubleArray(cuadros.size) { cuadros[it][j].toDouble() }
        for (k in 0 until n) salida[k][j] = interp(tNuevo[k], tOrig, fp)
    }
    return salida
}

/** Vector fijo de una seña: posiciones, velocidades y forma de cada mano (5 580 valores). */
fun vectorSecuencia(cuadros: List<FloatArray>): FloatArray {
    val r = remuestrear(rellenarManos(cuadros))
    val n = r.size
    val d = r[0].size
    val salida = FloatArray(n * d + (n - 1) * d + n * 84)
    var k = 0
    for (fila in r) for (v in fila) salida[k++] = v.toFloat()
    for (t in 1 until n) for (j in 0 until d) salida[k++] = (r[t][j] - r[t - 1][j]).toFloat()
    // forma de cada mano respecto a su muñeca, escalada por el largo de la palma
    for (t in 0 until n) {
        for (i in I_MUNECA) {
            val presente = r[t][i + 42]
            val bx = r[t][i]
            val by = r[t][i + 1]
            val escala = hypot(r[t][i + 18] - bx, r[t][i + 19] - by) + 1e-6
            for (p in 0 until 21) {
                salida[k++] = ((r[t][i + 2 * p] - bx) / escala * presente).toFloat()
                salida[k++] = ((r[t][i + 2 * p + 1] - by) / escala * presente).toFloat()
            }
        }
    }
    return salida
}

data class Evaluacion(val opciones: List<Prediccion>, val probOtra: Double) {
    val mejor get() = opciones[0]
}

/** Clasificador de palabras: probabilidades de cada seña conocida y de «otra cosa». */
class ClasificadorPalabras(
    private val bosque: Bosque,
    private val clases: List<String>,
    private val nombres: Map<String, String>,
    val umbral: Double,
    val umbralSugerencia: Double,
) {
    val palabras: List<String> = clases.filter { it != OTRA }.map { nombres[it] ?: it }

    fun evaluar(cuadros: List<FloatArray>): Evaluacion {
        val p = bosque.probabilidades(vectorSecuencia(cuadros))
        var otra = 0.0
        val opciones = mutableListOf<Prediccion>()
        for ((i, clave) in clases.withIndex()) {
            if (clave == OTRA) otra = p[i] else opciones.add(Prediccion(nombres[clave] ?: clave, p[i]))
        }
        opciones.sortByDescending { it.confianza }
        return Evaluacion(opciones, otra)
    }
}
