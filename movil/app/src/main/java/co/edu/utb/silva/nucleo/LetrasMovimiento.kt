package co.edu.utb.silva.nucleo

import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.min

/*
 * Letras con movimiento (silva.letras_movimiento): G, H, J, Ñ, Q, S y Z. Se segmenta el trazo de la
 * mano y se clasifica completo, remuestreado a 6 cuadros como las señas de LSC70.
 */

const val CUADROS_TRAZO = 6
val LETRAS = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ".map { it.toString() }
val LETRAS_ESTATICAS = "ABCDEFIKLMNOPRTUVWXY".map { it.toString() }
val LETRAS_MOVIMIENTO = LETRAS.filter { it !in LETRAS_ESTATICAS }

/** Puntos (21) en coordenadas de imagen → mismas unidades en x e y. */
fun aIsotropicas(puntos: List<Punto>, ancho: Int, alto: Int): Array<FloatArray> =
    Array(puntos.size) { floatArrayOf(puntos[it].x * ancho / alto, puntos[it].y) }

/** (T, 21, 2) → (n, 21, 2), como silva.letras_movimiento.remuestrear. */
fun remuestrearTrazo(p: List<Array<FloatArray>>, n: Int = CUADROS_TRAZO): List<Array<FloatArray>> {
    val t = p.size
    if (t == n) return p
    return List(n) { k ->
        val origen = if (n == 1) 0.0 else if (k == n - 1) (t - 1).toDouble() else k * ((t - 1).toDouble() / (n - 1))
        val i0 = floor(origen).toInt()
        val i1 = min(i0 + 1, t - 1)
        val f = origen - i0
        Array(21) { j -> FloatArray(2) { c -> ((1 - f) * p[i0][j][c] + f * p[i1][j][c]).toFloat() } }
    }
}

/** Vector de 264 valores de un trazo: forma de la mano en 6 cuadros, trayectoria de la muñeca y recorrido. */
fun caracteristicasTrazo(puntos: List<Array<FloatArray>>, izquierda: Boolean): FloatArray {
    val p = remuestrearTrazo(puntos).map { cuadro ->
        Array(21) { j -> floatArrayOf(if (izquierda) -cuadro[j][0] else cuadro[j][0], cuadro[j][1]) }
    }
    val escalas = FloatArray(CUADROS_TRAZO) {
        val e = hypot((p[it][9][0] - p[it][0][0]).toDouble(), (p[it][9][1] - p[it][0][1]).toDouble()).toFloat()
        if (e > 1e-6f) e else 1f
    }
    val ordenadas = escalas.sorted()
    val escala = (ordenadas[CUADROS_TRAZO / 2 - 1].toDouble() + ordenadas[CUADROS_TRAZO / 2]) / 2  // mediana
    val salida = FloatArray(21 * 2 * CUADROS_TRAZO + 2 * (CUADROS_TRAZO - 1) + 2)
    var k = 0
    for (t in 0 until CUADROS_TRAZO) for (j in 0 until 21) {
        salida[k++] = (p[t][j][0] - p[t][0][0]) / escalas[t]
        salida[k++] = (p[t][j][1] - p[t][0][1]) / escalas[t]
    }
    val tx = FloatArray(CUADROS_TRAZO) { ((p[it][0][0] - p[0][0][0]) / escala).toFloat() }
    val ty = FloatArray(CUADROS_TRAZO) { ((p[it][0][1] - p[0][0][1]) / escala).toFloat() }
    for (t in 1 until CUADROS_TRAZO) {
        salida[k++] = tx[t]
        salida[k++] = ty[t]
    }
    var recorrido = 0f
    for (t in 1 until CUADROS_TRAZO) recorrido += hypot((tx[t] - tx[t - 1]).toDouble(), (ty[t] - ty[t - 1]).toDouble()).toFloat()
    salida[k++] = recorrido
    salida[k] = hypot(tx.last().toDouble(), ty.last().toDouble()).toFloat()
    return salida
}

class TrazoTerminado(val puntos: List<Array<FloatArray>>, val izquierda: Boolean)

/** Detecta el tramo en que la mano se mueve (traslación o cambio de forma, en tamaños de mano). */
class SegmentadorLetras {
    private var anterior: Array<FloatArray>? = null
    private var previos = mutableListOf<Array<FloatArray>>()
    private var grabados = mutableListOf<Array<FloatArray>>()
    private var izquierdas = mutableListOf<Boolean>()
    private var quieto = 0
    private val velocidades = ArrayDeque<Double>()
    var moviendo = false
        private set

    fun reiniciar() {
        anterior = null
        previos = mutableListOf()
        grabados = mutableListOf()
        izquierdas = mutableListOf()
        quieto = 0
        velocidades.clear()
        moviendo = false
    }

    /** Devuelve el trazo cuando termina. `puntos` = 21 puntos isotrópicos, o null si no se ve la mano. */
    fun agregar(puntos: Array<FloatArray>?, izquierda: Boolean = false): TrazoTerminado? {
        if (puntos == null) {
            val t = cerrar()
            anterior = null
            previos = mutableListOf()
            velocidades.clear()
            return t
        }
        var velocidad = 0.0
        anterior?.let { a ->
            val escala = maxOf(hypot((puntos[9][0] - puntos[0][0]).toDouble(), (puntos[9][1] - puntos[0][1]).toDouble()), 1e-6)
            var suma = 0.0
            for (j in 0 until 21) suma += hypot((puntos[j][0] - a[j][0]).toDouble(), (puntos[j][1] - a[j][1]).toDouble())
            velocidad = suma / 21 / escala
        }
        anterior = puntos
        velocidades.addLast(velocidad)
        while (velocidades.size > 3) velocidades.removeFirst()

        if (!moviendo) {
            previos.add(puntos)
            while (previos.size > 3) previos.removeAt(0)
            if (velocidades.size == 3 && velocidades.average() >= Config.MOVIMIENTO_INICIO) {
                moviendo = true
                grabados = previos.toMutableList()
                izquierdas = MutableList(grabados.size) { izquierda }
                quieto = 0
            }
            return null
        }
        grabados.add(puntos)
        izquierdas.add(izquierda)
        quieto = if (velocidad < Config.MOVIMIENTO_FIN) quieto + 1 else 0
        if (quieto >= Config.CUADROS_QUIETO || grabados.size >= Config.MAX_CUADROS_MOVIMIENTO) {
            val t = cerrar()
            previos = mutableListOf(puntos)
            return t
        }
        return null
    }

    private fun cerrar(): TrazoTerminado? {
        if (!moviendo) return null
        moviendo = false
        var g: List<Array<FloatArray>> = grabados
        if (quieto > 0) g = g.subList(0, g.size - quieto + 1)
        val izquierda = izquierdas.count { it } * 2 >= izquierdas.size
        val salida = if (g.size >= Config.MIN_CUADROS_MOVIMIENTO) TrazoTerminado(g.toList(), izquierda) else null
        grabados = mutableListOf()
        izquierdas = mutableListOf()
        quieto = 0
        return salida
    }
}

/** Clasificador de trazos: devuelve OTRA si la muñeca casi no se desplazó (cambio entre letras). */
class ClasificadorMovimiento(private val bosque: Bosque, private val clases: List<String>) {
    val letras: List<String> = LETRAS_MOVIMIENTO.filter { it in clases }

    fun predecir(trazo: TrazoTerminado): Prediccion {
        val x = caracteristicasTrazo(trazo.puntos, trazo.izquierda)
        if (x[x.size - 2] < Config.RECORRIDO_MINIMO) return Prediccion(OTRA, 1.0)
        val p = bosque.probabilidades(x)
        val i = p.indices.maxBy { p[it] }
        return Prediccion(clases[i], p[i])
    }
}
