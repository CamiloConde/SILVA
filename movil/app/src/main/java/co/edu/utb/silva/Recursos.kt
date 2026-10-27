package co.edu.utb.silva

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import co.edu.utb.silva.nucleo.Animaciones
import co.edu.utb.silva.nucleo.Bosque
import co.edu.utb.silva.nucleo.ClasificadorLetras
import co.edu.utb.silva.nucleo.ClasificadorMovimiento
import co.edu.utb.silva.nucleo.ClasificadorPalabras
import co.edu.utb.silva.nucleo.Sugerencias
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Modelos de la app (assets/modelos, generados por scripts/exportar_movil.py), o un modelo propio importado. */
class Modelos(
    val letras: ClasificadorLetras,
    val movimiento: ClasificadorMovimiento,
    val palabras: ClasificadorPalabras,
    val animaciones: Animaciones,
    val sugerencias: Sugerencias,
    val origen: String?,  // null = el modelo original; si no, de dónde salió el modelo propio importado
) {
    companion object {
        /**
         * Carga los modelos. Los tres clasificadores salen de `propio` (al importar un paquete) o de
         * files/modelo_propio si se importó uno; si no, de los assets. Un modelo propio que no carga se
         * descarta y se usa el original.
         */
        fun cargar(context: Context, propio: ((String) -> ByteArray?)? = null): Modelos {
            val carpeta = Muestras.carpetaModeloPropio(context)
            val buscar = propio ?: { nombre: String -> File(carpeta, nombre).takeIf { it.exists() }?.readBytes() }
            return try {
                construir(context, buscar)
            } catch (e: Exception) {
                if (propio != null) throw e
                android.util.Log.e("SILVA", "El modelo propio no carga; se usa el original", e)
                Muestras.quitarModeloPropio(context)
                construir(context) { null }
            }
        }

        private fun construir(context: Context, propio: (String) -> ByteArray?): Modelos {
            fun leer(nombre: String) = context.assets.open("modelos/$nombre").use { it.readBytes() }
            fun modelo(nombre: String) = propio(nombre) ?: leer(nombre)
            fun JSONArray.textos() = List(length()) { getString(it) }
            val original = JSONObject(String(leer("modelos.json"), Charsets.UTF_8))
            val indice = JSONObject(String(modelo("modelos.json"), Charsets.UTF_8))
            val p = indice.getJSONObject("palabras")
            val n = p.getJSONObject("nombres")
            return Modelos(
                ClasificadorLetras(Bosque(modelo("letras.bin")), indice.getJSONObject("letras").getJSONArray("clases").textos()),
                ClasificadorMovimiento(Bosque(modelo("letras_movimiento.bin")),
                    indice.getJSONObject("letras_movimiento").getJSONArray("clases").textos()),
                ClasificadorPalabras(Bosque(modelo("palabras.bin")), p.getJSONArray("clases").textos(),
                    n.keys().asSequence().associateWith { n.getString(it) }, p.getDouble("umbral"), p.getDouble("umbral_sugerencia")),
                Animaciones(leer("animaciones.bin"), original.getJSONArray("animaciones").textos()),
                Sugerencias(String(leer("palabras_es.txt"), Charsets.UTF_8).lines()),
                if (propio("modelos.json") == null) null else indice.optString("origen", "modelo propio"),
            )
        }
    }
}

data class Sesion(val inicio: String, val texto: String)
data class Respuesta(val hora: String, val texto: String)

/** Historial local (SQLite), como silva.repositorio_historial: sesiones, letras/palabras y respuestas. */
class Historial(context: Context) : SQLiteOpenHelper(context, "historial.db", null, 1) {
    private val formato = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)
    private fun ahora() = formato.format(Date())

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE sesiones (id INTEGER PRIMARY KEY AUTOINCREMENT, inicio TEXT NOT NULL, fin TEXT, texto TEXT NOT NULL DEFAULT '')")
        db.execSQL("CREATE TABLE letras (id INTEGER PRIMARY KEY AUTOINCREMENT, sesion_id INTEGER NOT NULL, letra TEXT NOT NULL, confianza REAL NOT NULL, hora TEXT NOT NULL)")
        db.execSQL("CREATE TABLE respuestas (id INTEGER PRIMARY KEY AUTOINCREMENT, hora TEXT NOT NULL, texto TEXT NOT NULL)")
    }

    override fun onUpgrade(db: SQLiteDatabase, anterior: Int, nueva: Int) = Unit

    fun iniciarSesion(): Long = writableDatabase.insert("sesiones", null, ContentValues().apply { put("inicio", ahora()) })

    fun registrar(sesion: Long, letra: String, confianza: Double) {
        writableDatabase.insert("letras", null, ContentValues().apply {
            put("sesion_id", sesion); put("letra", letra); put("confianza", confianza); put("hora", ahora())
        })
    }

    fun guardarSesion(sesion: Long, texto: String) {
        writableDatabase.update("sesiones", ContentValues().apply { put("fin", ahora()); put("texto", texto) },
            "id = ?", arrayOf(sesion.toString()))
    }

    fun guardarRespuesta(texto: String) {
        writableDatabase.insert("respuestas", null, ContentValues().apply { put("hora", ahora()); put("texto", texto) })
    }

    fun sesiones(): List<Sesion> = readableDatabase.rawQuery(
        "SELECT inicio, texto FROM sesiones WHERE texto != '' ORDER BY id DESC LIMIT 200", null).use { c ->
        List(c.count) { c.moveToPosition(it); Sesion(c.getString(0), c.getString(1)) }
    }

    fun respuestas(): List<Respuesta> = readableDatabase.rawQuery(
        "SELECT hora, texto FROM respuestas ORDER BY id DESC LIMIT 200", null).use { c ->
        List(c.count) { c.moveToPosition(it); Respuesta(c.getString(0), c.getString(1)) }
    }
}
