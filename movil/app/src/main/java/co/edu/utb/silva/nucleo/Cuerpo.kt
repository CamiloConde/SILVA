package co.edu.utb.silva.nucleo

import kotlin.math.abs
import kotlin.math.hypot

/** Puntos de la pose usados: nariz, hombros, codos y muñecas (izq./der. de la persona). */
val POSE_USADOS = intArrayOf(0, 11, 12, 13, 14, 15, 16)
const val MUNECA_IZQ = 15
const val MUNECA_DER = 16
const val N_POSE = 14
const val N_MANO = 43  // 21 puntos (x, y) + presencia
const val N_CUADRO = N_POSE + 2 * N_MANO  // 100

/** Puntos de la mano que también estima la pose: muñeca, meñique, índice y pulgar. */
val MANO_POSE_IZQ = intArrayOf(15, 17, 19, 21)
val MANO_POSE_DER = intArrayOf(16, 18, 20, 22)
val POSE_CONEXIONES = listOf(11 to 12, 11 to 13, 13 to 15, 12 to 14, 14 to 16, 11 to 23, 12 to 24, 23 to 24)

/** Un cuadro del modo Palabras: pose (33 puntos) y la mano de cada lado de la persona. */
data class CuadroCuerpo(
    val pose: List<Punto>?,
    val manoIzquierda: List<Punto>?,
    val manoDerecha: List<Punto>?,
    val aspecto: Float,  // ancho / alto de la imagen
) {
    val hayMano get() = manoIzquierda != null || manoDerecha != null
}

/**
 * Asigna cada mano al lado de la persona según la muñeca de la pose más cercana (silva.cuerpo).
 * No se usa la lateralidad de MediaPipe porque depende de si la imagen está espejada.
 */
fun asignarManos(pose: List<Punto>?, manos: List<List<Punto>>): Pair<List<Punto>?, List<Punto>?> {
    if (manos.isEmpty()) return null to null
    if (pose == null) {
        val ordenadas = manos.sortedBy { it[0].x }
        if (ordenadas.size == 1) return if (ordenadas[0][0].x > 0.5f) ordenadas[0] to null else null to ordenadas[0]
        return ordenadas[1] to ordenadas[0]
    }
    fun dist(mano: List<Punto>, m: Punto): Double {
        val dx = mano[0].x.toDouble() - m.x
        val dy = mano[0].y.toDouble() - m.y
        return dx * dx + dy * dy
    }
    val mi = pose[MUNECA_IZQ]
    val md = pose[MUNECA_DER]
    if (manos.size == 1) {
        val m = manos[0]
        return if (dist(m, mi) <= dist(m, md)) m to null else null to m
    }
    val a = manos[0]
    val b = manos[1]
    return if (dist(a, mi) + dist(b, md) <= dist(b, mi) + dist(a, md)) a to b else b to a
}

/** Vector de 100 valores del cuadro, centrado en los hombros y escalado por su ancho; null sin pose. */
fun caracteristicasCuadro(c: CuadroCuerpo): FloatArray? {
    val pose = c.pose ?: return null
    val a = c.aspecto.toDouble()
    val hix = pose[11].x * a
    val hiy = pose[11].y.toDouble()
    val hdx = pose[12].x * a
    val hdy = pose[12].y.toDouble()
    val ox = (hix + hdx) / 2
    val oy = (hiy + hdy) / 2
    val escala = hypot(hix - hdx, hiy - hdy)
    if (escala < 1e-6) return null
    val v = FloatArray(N_CUADRO)
    for ((k, i) in POSE_USADOS.withIndex()) {
        v[2 * k] = ((pose[i].x * a - ox) / escala).toFloat()
        v[2 * k + 1] = ((pose[i].y - oy) / escala).toFloat()
    }
    for ((lado, mano) in listOf(c.manoIzquierda, c.manoDerecha).withIndex()) {
        if (mano == null) continue
        val base = N_POSE + lado * N_MANO
        for (j in 0 until 21) {
            v[base + 2 * j] = ((mano[j].x * a - ox) / escala).toFloat()
            v[base + 2 * j + 1] = ((mano[j].y - oy) / escala).toFloat()
        }
        v[base + 42] = 1f
    }
    return v
}

/**
 * Indicación para ubicarse como en los videos de entrenamiento, o null si el encuadre es bueno.
 * Las indicaciones laterales son desde el punto de vista de la persona.
 */
fun evaluarEncuadre(c: CuadroCuerpo): String? {
    val pose = c.pose ?: return null
    val hi = pose[11]
    val hd = pose[12]
    val vertical = c.aspecto < 1f  // teléfono vertical: el ancho de hombros se mide sobre el ancho de la imagen
    val ancho = if (vertical) abs(hi.x - hd.x).toDouble() else abs(hi.x - hd.x) * c.aspecto / (16.0 / 9.0)
    val rango = if (vertical) Config.ENCUADRE_HOMBROS_VERTICAL else Config.ENCUADRE_HOMBROS
    val centroX = (hi.x + hd.x) / 2.0
    val alturaHombros = (hi.y + hd.y) / 2.0
    return when {
        ancho < rango[0] -> "Acércate un poco a la cámara"
        ancho > rango[1] -> "Aléjate un poco: las manos deben caber en la imagen"
        centroX > Config.ENCUADRE_CENTRO_X[1] -> "Muévete un poco hacia tu derecha"
        centroX < Config.ENCUADRE_CENTRO_X[0] -> "Muévete un poco hacia tu izquierda"
        pose[0].y < Config.ENCUADRE_NARIZ_Y_MIN -> "Baja un poco la cámara (o inclínala hacia abajo)"
        alturaHombros > Config.ENCUADRE_HOMBROS_Y_MAX -> "Sube un poco la cámara"
        else -> null
    }
}
