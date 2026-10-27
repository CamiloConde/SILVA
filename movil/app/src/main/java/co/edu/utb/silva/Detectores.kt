package co.edu.utb.silva

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Rect
import android.os.SystemClock
import co.edu.utb.silva.nucleo.Config
import co.edu.utb.silva.nucleo.CuadroCuerpo
import co.edu.utb.silva.nucleo.MANO_POSE_DER
import co.edu.utb.silva.nucleo.MANO_POSE_IZQ
import co.edu.utb.silva.nucleo.ManoDetectada
import co.edu.utb.silva.nucleo.Punto
import co.edu.utb.silva.nucleo.asignarManos
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import kotlin.math.hypot

/**
 * MediaPipe en el teléfono, con la misma configuración que la app de PC (silva.detector_manos y
 * silva.cuerpo): una mano para Deletreo; pose y dos manos para Palabras, calculadas en paralelo, y
 * recuperación de la mano perdida en un recorte ampliado alrededor de la muñeca de la pose.
 */
class Detectores(private val context: Context, palabras: Boolean) : AutoCloseable {
    private fun base(modelo: String) = BaseOptions.builder().setModelAssetPath("modelos/$modelo").build()

    private fun manos(n: Int, confianza: Float, modo: RunningMode) = HandLandmarker.createFromOptions(context,
        HandLandmarker.HandLandmarkerOptions.builder()
            .setBaseOptions(base("hand_landmarker.task"))
            .setRunningMode(modo)
            .setNumHands(n)
            .setMinHandDetectionConfidence(confianza)
            .setMinHandPresenceConfidence(confianza)
            .setMinTrackingConfidence(confianza)
            .build())

    private val manoLetras = manos(1, Config.CONFIANZA_DETECCION, RunningMode.VIDEO)
    private val manosPalabras = if (palabras) manos(2, Config.CONFIANZA_MANOS_PALABRAS, RunningMode.VIDEO) else null
    private val pose = if (palabras) PoseLandmarker.createFromOptions(context,
        PoseLandmarker.PoseLandmarkerOptions.builder()
            .setBaseOptions(base("pose_landmarker_lite.task"))
            .setRunningMode(RunningMode.VIDEO)
            .setNumPoses(1)
            .build()) else null
    private val recuperadores = if (palabras) List(2) { manos(1, Config.CONFIANZA_RECUPERACION, RunningMode.IMAGE) } else emptyList()
    private val hilos = Executors.newFixedThreadPool(2)
    private var ultimoLetras = -1L
    private var ultimoPalabras = -1L
    private var cuadroLento = false  // el cuadro anterior tardó más de 70 ms
    private var saltarRecuperacion = false

    /** Modo Deletreo: la mano y si es la izquierda (según MediaPipe, igual que en el PC). */
    fun mano(imagen: Bitmap, ms: Long): ManoDetectada? {
        ultimoLetras = maxOf(ms, ultimoLetras + 1)
        val r = manoLetras.detectForVideo(BitmapImageBuilder(imagen).build(), ultimoLetras)
        if (r.landmarks().isEmpty()) return null
        val puntos = r.landmarks()[0].map { Punto(it.x(), it.y()) }
        // por el nombre y no por el índice: en MediaPipe para Android el índice puede venir vacío (-1)
        return ManoDetectada(puntos, r.handednesses()[0][0].categoryName() == "Left")
    }

    /** Modo Palabras: pose y la mano de cada lado de la persona. */
    fun cuerpo(imagen: Bitmap, ms: Long): CuadroCuerpo {
        val inicio = SystemClock.uptimeMillis()
        ultimoPalabras = maxOf(ms, ultimoPalabras + 1)
        val ts = ultimoPalabras
        val mp = BitmapImageBuilder(imagen).build()
        val enCurso = hilos.submit(Callable { pose!!.detectForVideo(mp, ts) })
        val rManos = manosPalabras!!.detectForVideo(mp, ts)
        val rPose = enCurso.get()
        val puntosPose = rPose.landmarks().firstOrNull()?.map { Punto(it.x(), it.y()) }
        val manos = rManos.landmarks().map { m -> m.map { Punto(it.x(), it.y()) } }
        var (izq, der) = asignarManos(puntosPose, manos)
        // En un teléfono lento la recuperación de la mano perdida se hace un cuadro sí y otro no
        saltarRecuperacion = cuadroLento && !saltarRecuperacion
        if (puntosPose != null && !saltarRecuperacion) {
            val r = recuperar(imagen, puntosPose, izq, der)
            izq = r.first
            der = r.second
        }
        cuadroLento = SystemClock.uptimeMillis() - inicio > 70
        return CuadroCuerpo(puntosPose, izq, der, imagen.width.toFloat() / imagen.height)
    }

    private fun recuperar(imagen: Bitmap, pose: List<Punto>, izq: List<Punto>?, der: List<Punto>?): Pair<List<Punto>?, List<Punto>?> {
        val ancho = imagen.width
        val alto = imagen.height
        val hombros = hypot(((pose[11].x - pose[12].x) * ancho).toDouble(), ((pose[11].y - pose[12].y) * alto).toDouble())
        if (hombros < 8) return izq to der
        val alturaHombros = (pose[11].y + pose[12].y) / 2.0 * alto
        val tareas = mutableMapOf<Int, java.util.concurrent.Future<List<Punto>?>>()
        for ((lado, datos) in listOf(Triple(izq, MANO_POSE_IZQ, der), Triple(der, MANO_POSE_DER, izq)).withIndex()) {
            val (mano, puntos, otra) = datos
            if (mano != null || pose[puntos[0]].y * alto > alturaHombros + 1.2 * hombros) continue  // detectada o en reposo
            tareas[lado] = hilos.submit(Callable { buscarEnRecorte(recuperadores[lado], imagen, pose, puntos, otra, hombros) })
        }
        return (tareas[0]?.get() ?: izq) to (tareas[1]?.get() ?: der)
    }

    private fun buscarEnRecorte(detector: HandLandmarker, imagen: Bitmap, pose: List<Punto>, puntos: IntArray,
                                otra: List<Punto>?, hombros: Double): List<Punto>? {
        val ancho = imagen.width
        val alto = imagen.height
        val cx = puntos.map { pose[it].x * ancho }.average()
        val cy = puntos.map { pose[it].y * alto }.average()
        val lado = Config.RECORTE_RECUPERACION * hombros
        val x0 = (cx - lado / 2).toInt()
        val y0 = (cy - lado / 2).toInt()
        val x1 = (x0 + lado).toInt()
        val y1 = (y0 + lado).toInt()
        // la parte del recorte que cae fuera de la imagen queda negra
        val ax0 = maxOf(x0, 0)
        val ay0 = maxOf(y0, 0)
        val ax1 = minOf(x1, ancho)
        val ay1 = minOf(y1, alto)
        if (ax1 <= ax0 || ay1 <= ay0) return null
        val f = Config.TAM_RECORTE.toDouble() / (x1 - x0)
        val recorte = Bitmap.createBitmap(Config.TAM_RECORTE, Config.TAM_RECORTE, Bitmap.Config.ARGB_8888)
        Canvas(recorte).apply {
            drawColor(Color.BLACK)
            drawBitmap(imagen, Rect(ax0, ay0, ax1, ay1),
                Rect(((ax0 - x0) * f).toInt(), ((ay0 - y0) * f).toInt(), ((ax1 - x0) * f).toInt(), ((ay1 - y0) * f).toInt()), null)
        }
        val r = detector.detect(BitmapImageBuilder(recorte).build())
        if (r.landmarks().isEmpty()) return null
        val mano = r.landmarks()[0].map { Punto((x0 + it.x() * (x1 - x0)) / ancho, (y0 + it.y() * (y1 - y0)) / alto) }
        val muneca = pose[puntos[0]]
        if (hypot(((mano[0].x - muneca.x) * ancho).toDouble(), ((mano[0].y - muneca.y) * alto).toDouble()) > 0.6 * lado) return null
        if (otra != null) {  // ¿encontró otra vez la otra mano?
            val d = mano.indices.map { hypot(((mano[it].x - otra[it].x) * ancho).toDouble(), ((mano[it].y - otra[it].y) * alto).toDouble()) }.average()
            if (d < 0.05 * lado) return null
        }
        return mano
    }

    override fun close() {
        manoLetras.close()
        manosPalabras?.close()
        pose?.close()
        recuperadores.forEach { it.close() }
        hilos.shutdown()
    }
}
