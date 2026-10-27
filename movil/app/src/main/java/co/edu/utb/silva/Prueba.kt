package co.edu.utb.silva

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import co.edu.utb.silva.nucleo.Modo
import co.edu.utb.silva.nucleo.Motor
import java.io.File

/**
 * Modo de prueba (solo en la versión de desarrollo): reproduce secuencias de imágenes en vez de la cámara,
 * por el mismo camino que el video en vivo (MediaPipe Android → Detectores → Motor), y escribe en el
 * registro lo que se reconoce, para compararlo con la app de PC con las mismas imágenes.
 *
 *   adb push <carpetas> /data/local/tmp/prueba/ && adb shell run-as co.edu.utb.silva cp -r /data/local/tmp/prueba files/
 *   adb shell am start -n co.edu.utb.silva/.MainActivity --ez prueba true
 *   adb logcat -s SILVA-PRUEBA
 */
object Prueba {
    private const val TAG = "SILVA-PRUEBA"

    fun ejecutar(context: Context, modelos: Modelos, config: Aceleracion) = Thread {
        val raiz = File(context.filesDir, "prueba")
        val carpetas = raiz.listFiles()?.filter { it.isDirectory }?.sortedBy { it.name } ?: emptyList()
        Log.i(TAG, "Inicio: ${carpetas.size} secuencias en $raiz")
        val detectores = Detectores(context, config)
        detectores.preparar(palabras = true)
        Log.i(TAG, "Detectores: ${detectores.aceleracion}")
        var ms = 0L
        for (carpeta in carpetas.filter { it.name.startsWith("L_") }) probarLetras(carpeta, modelos, detectores)
        for (carpeta in carpetas.filterNot { it.name.startsWith("L_") }) {
            var t = 0.0
            val motor = Motor(modelos.letras, modelos.movimiento, modelos.palabras, reloj = { t })
            motor.cambiarModo(Modo.PALABRAS)
            val imagenes = carpeta.listFiles { f -> f.name.endsWith(".jpg") }!!.sortedBy { it.name }
            val reconocido = mutableListOf<String>()
            var conPose = 0
            var conMano = 0
            var duracion = 0L
            for (archivo in imagenes + List(15) { imagenes.last() }) {  // reposo al final para cerrar la seña
                val original = BitmapFactory.decodeFile(archivo.path)
                val escala = minOf(1f, 640f / maxOf(original.width, original.height))
                val img = if (escala < 1f) Bitmap.createScaledBitmap(original, (original.width * escala).toInt(),
                    (original.height * escala).toInt(), true) else original
                val inicio = System.nanoTime()
                val cuerpo = detectores.cuerpo(img, ms)
                val r = motor.procesarPalabras(cuerpo)
                duracion += System.nanoTime() - inicio
                if (cuerpo.pose != null) conPose++
                if (cuerpo.hayMano) conMano++
                r.prediccion?.let { p ->
                    val tipo = when {
                        r.confirmada != null -> "escrita"
                        r.pendiente != null -> "sugerida"
                        else -> "nada"
                    }
                    reconocido.add("${p.texto} ${"%.2f".format(p.confianza)} → $tipo")
                }
                ms += 33
                t += 1 / 30.0
            }
            ms += 1000
            val n = imagenes.size + 15
            Log.i(TAG, "${carpeta.name}: ${imagenes.size} cuadros · pose ${100 * conPose / n}% · mano ${100 * conMano / n}% · " +
                "${duracion / n / 1_000_000} ms/cuadro (${detectores.tiempos}) · teléfono: $reconocido")
            detectores.tiempos.reiniciar()
        }
        detectores.close()
        Log.i(TAG, "Fin")
    }.start()

    /** Deletreo: cada imagen (una letra sostenida) se repite 8 cuadros; se registra lo que se escribe. */
    private fun probarLetras(carpeta: File, modelos: Modelos, detectores: Detectores) {
        var t = 0.0
        val motor = Motor(modelos.letras, modelos.movimiento, modelos.palabras, reloj = { t })
        motor.cambiarModo(Modo.LETRAS)
        val esperado = StringBuilder()
        var sinMano = 0
        var ms = 500_000L
        for (archivo in carpeta.listFiles { f -> f.name.endsWith(".jpg") }!!.sortedBy { it.name }) {
            esperado.append(archivo.name.substringBefore("_"))
            val img = BitmapFactory.decodeFile(archivo.path)
            repeat(8) {
                val mano = detectores.mano(img, ms)
                if (mano == null) sinMano++
                motor.procesarLetras(mano, img.width, img.height)
                ms += 33
                t += 1 / 30.0
            }
            repeat(3) { motor.procesarLetras(null, img.width, img.height); ms += 33; t += 1 / 30.0 }  // retira la mano
        }
        Log.i(TAG, "${carpeta.name}: esperado $esperado · teléfono ${motor.buffer.texto} · cuadros sin mano $sinMano")
    }
}
