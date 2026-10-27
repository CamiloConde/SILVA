package co.edu.utb.silva

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.resolutionselector.AspectRatioStrategy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import co.edu.utb.silva.nucleo.Modo
import co.edu.utb.silva.nucleo.Motor
import co.edu.utb.silva.nucleo.Resultado
import java.util.concurrent.Executors

/** Lo que muestra la pantalla en cada cuadro: la imagen procesada y lo que se reconoció. */
class Fotograma(val imagen: Bitmap, val resultado: Resultado, val modo: Modo, val brillo: Double, val fps: Double)

/**
 * Cámara (CameraX) → MediaPipe → Motor, en un hilo aparte (la pantalla nunca se congela).
 *
 * Se pide imagen 4:3 y el lado largo se reduce a 640, como en el PC. Con el teléfono vertical la imagen
 * queda vertical (480×640). En horizontal, Deletreo usa el centro en 4:3, el formato del modelo de letras. La imagen que se procesa no está
 * espejada (como la de una cámara web); solo la vista de la cámara frontal se muestra como espejo.
 */
class Camara(
    private val context: Context,
    private val motor: Motor,
    private val detectores: Detectores,
    private val alCuadro: (Fotograma) -> Unit,
) {
    private val hilo = Executors.newSingleThreadExecutor()
    private val principal = Handler(Looper.getMainLooper())
    private var proveedor: ProcessCameraProvider? = null
    private var fps = 0.0
    private var anterior = 0L
    @Volatile var frontal = false
    private var ultimoBrillo = 128.0
    private var cuadros = 0

    /** El brillo cambia lento: se mide cada 10 cuadros. */
    private fun brilloCada10(b: Bitmap): Double {
        if (cuadros++ % 10 == 0) ultimoBrillo = brillo(b)
        return ultimoBrillo
    }

    fun iniciar(dueno: LifecycleOwner, alFallar: (String) -> Unit) {
        val futuro = ProcessCameraProvider.getInstance(context)
        futuro.addListener({
            try {
                val p = futuro.get()
                proveedor = p
                val resolucion = ResolutionSelector.Builder()
                    // 4:3: la proporción del sensor (el campo de visión más amplio). Con el teléfono vertical la
                    // imagen es 3:4 y llena el recuadro de la cámara sin bandas negras.
                    .setAspectRatioStrategy(AspectRatioStrategy.RATIO_4_3_FALLBACK_AUTO_STRATEGY)
                    // 640×480: es lo que se procesa (el lado largo se lleva a 640); pedir más solo cuesta convertir
                    // más píxeles en cada cuadro
                    .setResolutionStrategy(ResolutionStrategy(Size(640, 480), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                    .build()
                val analisis = ImageAnalysis.Builder()
                    .setResolutionSelector(resolucion)
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                    .build()
                analisis.setAnalyzer(hilo) { procesar(it) }
                val selector = if (frontal) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA
                p.unbindAll()
                p.bindToLifecycle(dueno, selector, analisis)
                anterior = 0L
            } catch (e: Exception) {
                alFallar("No se pudo abrir la cámara: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(context))
    }

    fun detener() {
        proveedor?.unbindAll()
    }

    fun cerrar() {
        detener()
        hilo.execute { detectores.close() }
        hilo.shutdown()
    }

    private fun procesar(proxy: ImageProxy) {
        try {
            val imagen = preparar(proxy)
            val ms = SystemClock.uptimeMillis()
            val modo: Modo
            val resultado: Resultado
            if (motor.modo == Modo.LETRAS) {
                // horizontal: el centro en 4:3, como el PC; vertical: la imagen completa (Motor corrige la proporción)
                val recorte = if (imagen.width > imagen.height) recortarCentro(imagen, 4, 3) else imagen
                val mano = detectores.mano(recorte, ms)
                resultado = synchronized(motor) { motor.procesarLetras(mano, recorte.width, recorte.height) }
                modo = Modo.LETRAS
                entregar(Fotograma(recorte, resultado, modo, brilloCada10(recorte), medirFps()))
            } else {
                val cuerpo = detectores.cuerpo(imagen, ms)
                resultado = synchronized(motor) {
                    if (motor.modo == Modo.PALABRAS) motor.procesarPalabras(cuerpo) else null
                } ?: return
                modo = Modo.PALABRAS
                entregar(Fotograma(imagen, resultado, modo, brilloCada10(imagen), medirFps()))
            }
        } catch (e: Exception) {
            android.util.Log.e("SILVA", "Error al procesar un cuadro", e)
        } finally {
            proxy.close()
        }
    }

    private fun entregar(f: Fotograma) {
        principal.post { alCuadro(f) }
    }

    private fun preparar(proxy: ImageProxy): Bitmap {
        val original = proxy.toBitmap()
        val grados = proxy.imageInfo.rotationDegrees
        val escala = minOf(1f, 640f / maxOf(original.width, original.height, 1))  // el lado largo a 640
        val m = Matrix().apply {
            postRotate(grados.toFloat())
            postScale(escala, escala)
        }
        return Bitmap.createBitmap(original, 0, 0, original.width, original.height, m, true)
    }

    private fun recortarCentro(b: Bitmap, ancho: Int, alto: Int): Bitmap {
        val w = minOf(b.width, b.height * ancho / alto)
        val h = minOf(b.height, b.width * alto / ancho)
        return Bitmap.createBitmap(b, (b.width - w) / 2, (b.height - h) / 2, w, h)
    }

    /** Brillo medio (0-255) sobre una versión pequeña de la imagen. */
    private fun brillo(b: Bitmap): Double {
        val p = Bitmap.createScaledBitmap(b, 64, 48, true)
        val pixeles = IntArray(64 * 48).also { p.getPixels(it, 0, 64, 0, 0, 64, 48) }
        return pixeles.sumOf { (((it shr 16) and 0xFF) + ((it shr 8) and 0xFF) + (it and 0xFF)).toDouble() } / (pixeles.size * 3)
    }

    private fun medirFps(): Double {
        val ahora = SystemClock.elapsedRealtimeNanos()
        if (anterior != 0L) {
            val instantaneo = 1e9 / (ahora - anterior)
            fps = if (fps == 0.0) instantaneo else 0.9 * fps + 0.1 * instantaneo
        }
        anterior = ahora
        return fps
    }
}
