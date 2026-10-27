package co.edu.utb.silva

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.GZIPOutputStream
import java.util.zip.ZipInputStream

/** Qué se graba: una palabra (seña completa), una letra quieta (la mano sostenida) o una letra con trazo. */
enum class TipoMuestra(val clave: String) { PALABRA("palabra"), LETRA("letra"), TRAZO("trazo") }

/**
 * Muestras propias para reentrenar los modelos en el PC (scripts/entrenar_con_muestras.py).
 *
 * Solo se guardan los puntos que detecta MediaPipe (cuerpo y manos), nunca la imagen. Cada muestra es una
 * línea JSON en files/muestras.jsonl; al exportar se comprimen todas en un .jsonl.gz con una primera línea
 * que describe el archivo. Formato de cada muestra:
 *   palabra: {"tipo","clave","persona","fecha","cuadros": [[100 valores]...], "fps"}
 *   letra:   {"tipo","clave","persona","fecha","cuadros": [[42 valores]...], "puntos": [[[x,y]×21]...], "izquierda"}
 *   trazo:   {"tipo","clave","persona","fecha","puntos": [[[x,y]×21]...], "izquierda"}
 * Los 100 y 42 valores son exactamente lo que reciben los modelos; los puntos de la mano van en unidades
 * iguales en x e y (aIsotropicas), como los trazos de LSC70.
 */
class Muestras(private val context: Context) {
    private val archivo = File(context.filesDir, "muestras.jsonl")
    private val fecha = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)
    // tipo y clave de cada muestra, en orden (para contar y borrar la última sin leer todo el archivo)
    private val indice = mutableListOf<Pair<String, String>>()

    init {
        if (archivo.exists()) archivo.forEachLine { linea ->
            REGEX_CABECERA.find(linea.take(200))?.let { indice.add(it.groupValues[1] to it.groupValues[2]) }
        }
    }

    val total get() = indice.size

    /** Muestras por tipo y clave, p. ej. ("palabra", "Hola") → 5. */
    fun conteo(): Map<Pair<String, String>, Int> = indice.groupingBy { it }.eachCount()

    private fun inicio(tipo: TipoMuestra, clave: String, persona: String) = JSONObject().apply {
        put("tipo", tipo.clave)  // tipo y clave primero: el índice los lee del comienzo de la línea
        put("clave", clave)
        put("persona", persona)
        put("fecha", fecha.format(Date()))
    }

    private fun agregar(tipo: TipoMuestra, clave: String, cuerpo: JSONObject) {
        archivo.appendText(cuerpo.toString() + "\n")
        indice.add(tipo.clave to clave)
    }

    fun agregarPalabra(clave: String, persona: String, cuadros: List<FloatArray>, fps: Double) =
        agregar(TipoMuestra.PALABRA, clave, inicio(TipoMuestra.PALABRA, clave, persona).apply {
            put("cuadros", lista(cuadros.map { vector(it) }))
            put("fps", redondear(fps.toFloat(), 10f))
        })

    fun agregarLetra(clave: String, persona: String, cuadros: List<FloatArray>, puntos: List<Array<FloatArray>>, izquierda: Boolean) =
        agregar(TipoMuestra.LETRA, clave, inicio(TipoMuestra.LETRA, clave, persona).apply {
            put("cuadros", lista(cuadros.map { vector(it) }))
            put("puntos", lista(puntos.map { mano(it) }))
            put("izquierda", izquierda)
        })

    fun agregarTrazo(clave: String, persona: String, puntos: List<Array<FloatArray>>, izquierda: Boolean) =
        agregar(TipoMuestra.TRAZO, clave, inicio(TipoMuestra.TRAZO, clave, persona).apply {
            put("puntos", lista(puntos.map { mano(it) }))
            put("izquierda", izquierda)
        })

    fun borrarUltima(): Pair<String, String>? {
        if (indice.isEmpty()) return null
        val lineas = archivo.readLines().filter { it.isNotBlank() }
        archivo.writeText(lineas.dropLast(1).joinToString("") { it + "\n" })
        return indice.removeAt(indice.lastIndex)
    }

    fun borrarTodas() {
        archivo.delete()
        indice.clear()
    }

    /** Todas las muestras en un .jsonl.gz (en la caché de la app, para compartirlo o copiarlo a Descargas). */
    fun exportar(): File {
        val carpeta = File(context.cacheDir, "compartir").apply { mkdirs() }
        carpeta.listFiles()?.forEach { it.delete() }
        val sello = SimpleDateFormat("yyyyMMdd_HHmm", Locale.US).format(Date())
        val salida = File(carpeta, "silva_muestras_$sello.jsonl.gz")
        GZIPOutputStream(salida.outputStream()).bufferedWriter().use { w ->
            w.write(JSONObject().apply {
                put("formato", "silva-muestras")
                put("version", 1)
                put("app", context.packageManager.getPackageInfo(context.packageName, 0).versionName)
                put("dispositivo", "${Build.MANUFACTURER} ${Build.MODEL}")
                put("exportado", fecha.format(Date()))
                put("muestras", total)
            }.toString())
            w.write("\n")
            if (archivo.exists()) archivo.forEachLine { if (it.isNotBlank()) { w.write(it); w.write("\n") } }
        }
        return salida
    }

    /** Copia el archivo exportado a Descargas/SILVA (Android 10 o más reciente). Devuelve dónde quedó. */
    fun guardarEnDescargas(f: File): String? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return null
        val datos = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, f.name)
            put(MediaStore.Downloads.MIME_TYPE, "application/gzip")
            put(MediaStore.Downloads.RELATIVE_PATH, "Download/SILVA")
        }
        val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, datos) ?: return null
        context.contentResolver.openOutputStream(uri)?.use { salida -> f.inputStream().use { it.copyTo(salida) } }
        return "Descargas/SILVA/${f.name}"
    }

    /** Hoja de «Compartir» de Android (Drive, Quick Share, correo…) con el archivo exportado. */
    fun compartir(f: File): Intent {
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.archivos", f)
        return Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "application/gzip"
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_SUBJECT, f.name)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }, "Enviar las muestras al PC")
    }

    companion object {
        private val REGEX_CABECERA = Regex("\"tipo\":\"(\\w+)\",\"clave\":\"((?:[^\"\\\\]|\\\\.)*)\"")

        private fun redondear(v: Float, escala: Float = 10000f) = if (v.isNaN()) 0.0 else Math.round(v * escala) / escala.toDouble()
        private fun vector(v: FloatArray) = org.json.JSONArray().apply { for (x in v) put(redondear(x)) }
        private fun mano(p: Array<FloatArray>) = org.json.JSONArray().apply {
            for (punto in p) put(org.json.JSONArray().apply { put(redondear(punto[0])); put(redondear(punto[1])) })
        }
        private fun <T> lista(xs: List<T>) = org.json.JSONArray().apply { xs.forEach { put(it) } }

        /** Archivos de un modelo propio (scripts/exportar_movil.py --paquete). */
        val ARCHIVOS_MODELO = listOf("letras.bin", "letras_movimiento.bin", "palabras.bin", "modelos.json")

        fun carpetaModeloPropio(context: Context) = File(context.filesDir, "modelo_propio")

        /**
         * Lee un paquete .zip con un modelo entrenado en el PC, comprueba que se pueda cargar y lo deja en
         * files/modelo_propio. Devuelve un error para mostrar, o null si quedó listo (hay que reiniciar SILVA).
         */
        fun importarModelo(context: Context, uri: Uri): String? {
            val leidos = mutableMapOf<String, ByteArray>()
            try {
                context.contentResolver.openInputStream(uri)?.use { entrada ->
                    ZipInputStream(entrada).use { zip ->
                        while (true) {
                            val e = zip.nextEntry ?: break
                            val nombre = e.name.substringAfterLast('/')
                            if (nombre in ARCHIVOS_MODELO) leidos[nombre] = zip.readBytes()
                        }
                    }
                } ?: return "No se pudo abrir el archivo."
            } catch (e: Exception) {
                return "El archivo no es un paquete de modelo de SILVA (.zip): ${e.message}"
            }
            val faltan = ARCHIVOS_MODELO.filter { it !in leidos }
            if (faltan.isNotEmpty()) return "Al paquete le faltan: ${faltan.joinToString(", ")}."
            try {
                Modelos.cargar(context) { nombre -> leidos[nombre] }  // si no carga, no se instala
            } catch (e: Exception) {
                return "El modelo no se pudo cargar: ${e.message}"
            }
            val carpeta = carpetaModeloPropio(context)
            carpeta.deleteRecursively()
            carpeta.mkdirs()
            for ((nombre, datos) in leidos) File(carpeta, nombre).writeBytes(datos)
            return null
        }

        fun quitarModeloPropio(context: Context) {
            carpetaModeloPropio(context).deleteRecursively()
        }
    }
}
