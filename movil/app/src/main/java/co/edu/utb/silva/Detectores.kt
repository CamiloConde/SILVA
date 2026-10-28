package co.edu.utb.silva

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Rect
import android.os.SystemClock
import android.util.Log
import co.edu.utb.silva.nucleo.Config
import co.edu.utb.silva.nucleo.CuadroCuerpo
import co.edu.utb.silva.nucleo.MANO_POSE_DER
import co.edu.utb.silva.nucleo.MANO_POSE_IZQ
import co.edu.utb.silva.nucleo.ManoDetectada
import co.edu.utb.silva.nucleo.Punto
import co.edu.utb.silva.nucleo.asignarManos
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.core.Delegate
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.Future
import kotlin.math.hypot

/**
 * MediaPipe en el teléfono, con la misma configuración que la app de PC (silva.detector_manos y
 * silva.cuerpo): una mano para Deletreo; pose y dos manos para Palabras, calculadas en paralelo, y
 * recuperación de la mano perdida en un recorte ampliado alrededor de la muñeca de la pose.
 *
 * Rendimiento:
 * - Las manos corren en la GPU del teléfono y la pose en la CPU, al mismo tiempo (ver Aceleracion); si la GPU
 *   falla al crear o al probar un detector, ese detector usa la CPU.
 * - Cada detector se crea la primera vez que su modo lo necesita, en el hilo de la cámara.
 * - Si la búsqueda de una mano perdida no la encuentra, no se repite en los 2 cuadros siguientes
 *   (si la mano está fuera de la imagen, buscarla en cada cuadro solo cuesta tiempo).
 */
/**
 * Dónde corre cada parte. Medido en un Galaxy A35 (modo Palabras): todo en CPU 7-10 fps; todo en GPU ~13 fps
 * (pose y manos se estorban en la GPU); manos en GPU y pose en CPU, a la vez, 16-17 fps. Las manos (dos manos
 * y la búsqueda de la palma) son lo más pesado, así que van a la GPU. La versión de desarrollo permite
 * cambiarlo para medir (ver MainActivity).
 */
data class Aceleracion(val gpuPose: Boolean = false, val gpuManos: Boolean = true, val paralelo: Boolean = true)

class Detectores(private val context: Context, private val config: Aceleracion = Aceleracion()) : AutoCloseable {
    /** "GPU", "CPU" o "GPU+CPU" según cómo quedaron los detectores creados. */
    @Volatile var aceleracion = ""; private set
    private val enGpu = mutableListOf<Boolean>()

    private fun base(modelo: String, delegado: Delegate) =
        BaseOptions.builder().setModelAssetPath("modelos/$modelo").setDelegate(delegado).build()

    /** Crea el detector en la GPU y lo prueba con una imagen vacía; si algo falla, lo crea en la CPU. */
    private fun <T : AutoCloseable> crear(nombre: String, usarGpu: Boolean, fabrica: (Delegate) -> T, probar: (T) -> Unit): T {
        if (usarGpu) {
            var detector: T? = null
            try {
                detector = fabrica(Delegate.GPU)
                probar(detector)
                anotar(true)
                return detector
            } catch (e: Throwable) {
                Log.w("SILVA", "$nombre: la GPU no está disponible, se usa la CPU (${e.message})")
                try { detector?.close() } catch (_: Throwable) {}
            }
        }
        val detector = fabrica(Delegate.CPU)
        anotar(false)
        return detector
    }

    private fun anotar(gpu: Boolean) = synchronized(enGpu) {
        enGpu.add(gpu)
        aceleracion = when {
            enGpu.all { it } -> "GPU"
            enGpu.none { it } -> "CPU"
            else -> "GPU+CPU"
        }
    }

    private val vacia: Bitmap by lazy { Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888) }

    private fun manos(n: Int, confianza: Float, modo: RunningMode, seguimiento: Float = confianza) = crear("Manos", config.gpuManos, { d ->
        HandLandmarker.createFromOptions(context,
            HandLandmarker.HandLandmarkerOptions.builder()
                .setBaseOptions(base("hand_landmarker.task", d))
                .setRunningMode(modo)
                .setNumHands(n)
                .setMinHandDetectionConfidence(confianza)
                .setMinHandPresenceConfidence(confianza)
                .setMinTrackingConfidence(seguimiento)
                .build())
    }) { if (modo == RunningMode.VIDEO) it.detectForVideo(BitmapImageBuilder(vacia).build(), 0) else it.detect(BitmapImageBuilder(vacia).build()) }

    private val manoLetrasPerezosa = lazy { manos(1, Config.CONFIANZA_DETECCION, RunningMode.VIDEO, Config.CONFIANZA_SEGUIMIENTO) }
    private val manosPalabrasPerezosa = lazy { manos(2, Config.CONFIANZA_MANOS_PALABRAS, RunningMode.VIDEO) }
    private val posePerezosa = lazy {
        crear("Pose", config.gpuPose, { d ->
            PoseLandmarker.createFromOptions(context,
                PoseLandmarker.PoseLandmarkerOptions.builder()
                    .setBaseOptions(base("pose_landmarker_lite.task", d))
                    .setRunningMode(RunningMode.VIDEO)
                    .setNumPoses(1)
                    .build())
        }) { it.detectForVideo(BitmapImageBuilder(vacia).build(), 0) }
    }
    private val recuperadoresPerezosos = lazy { List(2) { manos(1, Config.CONFIANZA_RECUPERACION, RunningMode.IMAGE) } }
    private val hilos = Executors.newFixedThreadPool(2)
    // 0 ya lo usó la prueba de la GPU con la imagen vacía: MediaPipe exige marcas de tiempo crecientes
    private var ultimoLetras = 0L
    private var ultimoPalabras = 0L
    private var cuadroLento = false  // el cuadro anterior tardó más de 70 ms
    private var saltarRecuperacion = false
    private val esperaRecuperar = IntArray(2)  // cuadros que faltan para volver a buscar cada mano perdida

    /** Milisegundos acumulados por etapa (para el registro de rendimiento). */
    val tiempos = Tiempos()

    class Tiempos {
        var cuadros = 0; var pose = 0L; var manos = 0L; var recuperar = 0L; var recuperaciones = 0
        fun reiniciar() { cuadros = 0; pose = 0; manos = 0; recuperar = 0; recuperaciones = 0 }
        override fun toString() = if (cuadros == 0) "" else
            "pose ${pose / cuadros} ms · manos ${manos / cuadros} ms · recuperar ${recuperar / cuadros} ms ($recuperaciones búsquedas)"
    }

    /** Crea por adelantado los detectores de un modo (para no hacerlo con el primer cuadro). */
    fun preparar(palabras: Boolean) {
        if (palabras) {
            posePerezosa.value; manosPalabrasPerezosa.value; recuperadoresPerezosos.value
        } else manoLetrasPerezosa.value
    }

    /** Modo Deletreo: la mano y si es la izquierda (según MediaPipe, igual que en el PC). */
    fun mano(imagen: Bitmap, ms: Long): ManoDetectada? {
        val inicio = SystemClock.uptimeMillis()
        ultimoLetras = maxOf(ms, ultimoLetras + 1)
        val r = manoLetrasPerezosa.value.detectForVideo(BitmapImageBuilder(imagen).build(), ultimoLetras)
        tiempos.manos += SystemClock.uptimeMillis() - inicio
        tiempos.cuadros++
        if (r.landmarks().isEmpty()) return null
        val puntos = r.landmarks()[0].map { Punto(it.x(), it.y()) }
        // por el nombre y no por el índice: en MediaPipe para Android el índice puede venir vacío (-1)
        return ManoDetectada(puntos, r.handednesses()[0][0].categoryName() == "Left")
    }

    /** Modo Palabras: pose y la mano de cada lado de la persona. */
    fun cuerpo(imagen: Bitmap, ms: Long): CuadroCuerpo {
        val pose = posePerezosa.value
        val manosPalabras = manosPalabrasPerezosa.value
        val inicio = SystemClock.uptimeMillis()
        ultimoPalabras = maxOf(ms, ultimoPalabras + 1)
        val ts = ultimoPalabras
        val mp = BitmapImageBuilder(imagen).build()
        val rPose: com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarkerResult
        val rManos: com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarkerResult
        if (config.paralelo) {
            var finPose = 0L
            val enCurso = hilos.submit(Callable { pose.detectForVideo(mp, ts).also { finPose = SystemClock.uptimeMillis() } })
            rManos = manosPalabras.detectForVideo(mp, ts)
            val finManos = SystemClock.uptimeMillis()
            rPose = enCurso.get()
            tiempos.pose += finPose - inicio
            tiempos.manos += finManos - inicio
        } else {
            rPose = pose.detectForVideo(mp, ts)
            val finPose = SystemClock.uptimeMillis()
            rManos = manosPalabras.detectForVideo(mp, ts)
            tiempos.pose += finPose - inicio
            tiempos.manos += SystemClock.uptimeMillis() - finPose
        }
        val puntosPose = rPose.landmarks().firstOrNull()?.map { Punto(it.x(), it.y()) }
        val manos = rManos.landmarks().map { m -> m.map { Punto(it.x(), it.y()) } }
        var (izq, der) = asignarManos(puntosPose, manos)
        // En un teléfono lento la recuperación de la mano perdida se hace un cuadro sí y otro no
        saltarRecuperacion = cuadroLento && !saltarRecuperacion
        if (puntosPose != null && !saltarRecuperacion) {
            val antes = SystemClock.uptimeMillis()
            val r = recuperar(imagen, puntosPose, izq, der)
            tiempos.recuperar += SystemClock.uptimeMillis() - antes
            izq = r.first
            der = r.second
        }
        tiempos.cuadros++
        cuadroLento = SystemClock.uptimeMillis() - inicio > 70
        return CuadroCuerpo(puntosPose, izq, der, imagen.width.toFloat() / imagen.height)
    }

    private fun recuperar(imagen: Bitmap, pose: List<Punto>, izq: List<Punto>?, der: List<Punto>?): Pair<List<Punto>?, List<Punto>?> {
        val ancho = imagen.width
        val alto = imagen.height
        val hombros = hypot(((pose[11].x - pose[12].x) * ancho).toDouble(), ((pose[11].y - pose[12].y) * alto).toDouble())
        if (hombros < 8) return izq to der
        val alturaHombros = (pose[11].y + pose[12].y) / 2.0 * alto
        val tareas = mutableMapOf<Int, Future<List<Punto>?>>()
        for ((lado, datos) in listOf(Triple(izq, MANO_POSE_IZQ, der), Triple(der, MANO_POSE_DER, izq)).withIndex()) {
            val (mano, puntos, otra) = datos
            if (mano != null || pose[puntos[0]].y * alto > alturaHombros + 1.2 * hombros) {  // detectada o en reposo
                esperaRecuperar[lado] = 0
                continue
            }
            if (esperaRecuperar[lado] > 0) {  // se buscó hace poco y no estaba
                esperaRecuperar[lado]--
                continue
            }
            val recuperador = recuperadoresPerezosos.value[lado]
            tiempos.recuperaciones++
            tareas[lado] = hilos.submit(Callable { buscarEnRecorte(recuperador, imagen, pose, puntos, otra, hombros) })
        }
        val resultado = (tareas[0]?.get() ?: izq) to (tareas[1]?.get() ?: der)
        for ((lado, tarea) in tareas) if (tarea.get() == null) esperaRecuperar[lado] = 2
        return resultado
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
        if (manoLetrasPerezosa.isInitialized()) manoLetrasPerezosa.value.close()
        if (manosPalabrasPerezosa.isInitialized()) manosPalabrasPerezosa.value.close()
        if (posePerezosa.isInitialized()) posePerezosa.value.close()
        if (recuperadoresPerezosos.isInitialized()) recuperadoresPerezosos.value.forEach { it.close() }
        hilos.shutdown()
    }
}
