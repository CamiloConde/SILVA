package co.edu.utb.silva.nucleo

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import kotlin.math.abs

/**
 * La app Android debe reconocer igual que la de PC. casos.json (scripts/exportar_movil.py) trae
 * entradas reales y lo que responde Python; aquí se comparan con el cálculo en Kotlin.
 */
class IgualQuePythonTest {
    private val casos = JSONObject(javaClass.getResource("/casos.json")!!.readText())
    private val dirModelos = File("src/main/assets/modelos")
    private val indice = JSONObject(File(dirModelos, "modelos.json").readText())

    private fun bosque(nombre: String) = Bosque(File(dirModelos, "$nombre.bin").readBytes())
    private fun JSONArray.floats() = FloatArray(length()) { getDouble(it).toFloat() }
    private fun JSONArray.doubles() = DoubleArray(length()) { getDouble(it) }
    private fun JSONArray.strings() = List(length()) { getString(it) }
    private fun JSONArray.puntos() = List(length()) { getJSONArray(it).let { p -> Punto(p.getDouble(0).toFloat(), p.getDouble(1).toFloat()) } }

    private fun cerca(esperado: FloatArray, obtenido: FloatArray, tolerancia: Double = 1e-4) {
        assertEquals(esperado.size, obtenido.size)
        for (i in esperado.indices) {
            val margen = tolerancia * maxOf(1.0, abs(esperado[i].toDouble()))
            assertTrue("valor $i: esperado ${esperado[i]}, obtenido ${obtenido[i]}", abs(esperado[i] - obtenido[i]) <= margen)
        }
    }

    /** Mismas probabilidades (salvo algún árbol que cae justo en un umbral) y misma clase ganadora. */
    private fun mismasProbabilidades(esperado: DoubleArray, obtenido: DoubleArray) {
        assertEquals(esperado.indices.maxBy { esperado[it] }, obtenido.indices.maxBy { obtenido[it] })
        for (i in esperado.indices) assertTrue("clase $i: ${esperado[i]} vs ${obtenido[i]}", abs(esperado[i] - obtenido[i]) < 0.02)
    }

    @Test
    fun constantesIgualesALasDelPc() {
        val c = casos.getJSONObject("config")
        assertEquals(c.getDouble("UMBRAL_CONFIANZA"), Config.UMBRAL_CONFIANZA, 0.0)
        assertEquals(c.getInt("CUADROS_ESTABLES"), Config.CUADROS_ESTABLES)
        assertEquals(c.getDouble("MOVIMIENTO_INICIO"), Config.MOVIMIENTO_INICIO, 0.0)
        assertEquals(c.getDouble("MOVIMIENTO_FIN"), Config.MOVIMIENTO_FIN, 0.0)
        assertEquals(c.getInt("CUADROS_QUIETO"), Config.CUADROS_QUIETO)
        assertEquals(c.getInt("MIN_CUADROS_MOVIMIENTO"), Config.MIN_CUADROS_MOVIMIENTO)
        assertEquals(c.getInt("MAX_CUADROS_MOVIMIENTO"), Config.MAX_CUADROS_MOVIMIENTO)
        assertEquals(c.getDouble("UMBRAL_MOVIMIENTO"), Config.UMBRAL_MOVIMIENTO, 0.0)
        assertEquals(c.getDouble("RECORRIDO_MINIMO"), Config.RECORRIDO_MINIMO, 0.0)
        assertEquals(c.getDouble("SEGUNDOS_INICIO_TRAZO"), Config.SEGUNDOS_INICIO_TRAZO, 0.0)
        assertEquals(c.getInt("LONGITUD_FIJA"), Config.LONGITUD_FIJA)
        assertEquals(c.getInt("MIN_ACTIVOS"), Config.MIN_ACTIVOS)
        assertEquals(c.getInt("MAX_CUADROS"), Config.MAX_CUADROS)
        assertEquals(c.getInt("CUADROS_FIN"), Config.CUADROS_FIN)
        assertEquals(c.getInt("MARGEN"), Config.MARGEN)
        assertEquals(c.getDouble("ALTURA_ACTIVA"), Config.ALTURA_ACTIVA, 0.0)
        assertEquals(c.getDouble("MOVIMIENTO_ACTIVO"), Config.MOVIMIENTO_ACTIVO, 0.0)
        assertEquals(c.getInt("BRILLO_MINIMO"), Config.BRILLO_MINIMO)
        assertEquals(c.getJSONArray("ENCUADRE_HOMBROS").doubles().toList(), Config.ENCUADRE_HOMBROS.toList())
        assertEquals(c.getJSONArray("ENCUADRE_CENTRO_X").doubles().toList(), Config.ENCUADRE_CENTRO_X.toList())
        assertEquals(c.getDouble("ENCUADRE_NARIZ_Y_MIN"), Config.ENCUADRE_NARIZ_Y_MIN, 0.0)
        assertEquals(c.getDouble("ENCUADRE_HOMBROS_Y_MAX"), Config.ENCUADRE_HOMBROS_Y_MAX, 0.0)
        assertEquals(c.getDouble("RECORTE_RECUPERACION"), Config.RECORTE_RECUPERACION, 0.0)
        assertEquals(c.getInt("TAM_RECORTE"), Config.TAM_RECORTE)
        assertEquals(c.getDouble("CONFIANZA_RECUPERACION"), Config.CONFIANZA_RECUPERACION.toDouble(), 1e-6)
        assertEquals(c.getDouble("CONFIANZA_MANOS_PALABRAS"), Config.CONFIANZA_MANOS_PALABRAS.toDouble(), 1e-6)
        assertEquals(c.getDouble("CONFIANZA_DETECCION"), Config.CONFIANZA_DETECCION.toDouble(), 1e-6)
    }

    @Test
    fun letrasEstaticas() {
        val b = bosque("letras")
        val casosLetras = casos.getJSONArray("letras")
        for (k in 0 until casosLetras.length()) {
            val c = casosLetras.getJSONObject(k)
            val x = normalizarLandmarks(c.getJSONArray("puntos").puntos(), c.getBoolean("izquierda"))
            cerca(c.getJSONArray("vector").floats(), x, 1e-5)
            mismasProbabilidades(c.getJSONArray("proba").doubles(), b.probabilidades(x))
        }
    }

    @Test
    fun letrasConMovimiento() {
        val b = bosque("letras_movimiento")
        val lista = casos.getJSONArray("letras_movimiento")
        for (k in 0 until lista.length()) {
            val c = lista.getJSONObject(k)
            val pts = c.getJSONArray("puntos")
            val trazo = List(pts.length()) { t ->
                val cuadro = pts.getJSONArray(t)
                Array(21) { j -> cuadro.getJSONArray(j).floats() }
            }
            val x = caracteristicasTrazo(trazo, c.getBoolean("izquierda"))
            cerca(c.getJSONArray("vector").floats(), x, 1e-4)
            mismasProbabilidades(c.getJSONArray("proba").doubles(), b.probabilidades(x))
        }
    }

    @Test
    fun cuerpoYEncuadre() {
        val lista = casos.getJSONArray("cuerpo")
        for (k in 0 until lista.length()) {
            val c = lista.getJSONObject(k)
            val pose = c.getJSONArray("pose").puntos()
            val manos = c.getJSONArray("manos").let { m -> List(m.length()) { m.getJSONArray(it).puntos() } }
            val (izq, der) = asignarManos(pose, manos)
            assertEquals(if (c.isNull("izquierda")) null else manos[c.getInt("izquierda")], izq)
            assertEquals(if (c.isNull("derecha")) null else manos[c.getInt("derecha")], der)
            val cuadro = CuadroCuerpo(pose, izq, der, 16f / 9f)
            cerca(c.getJSONArray("vector").floats(), caracteristicasCuadro(cuadro)!!, 1e-5)
            assertEquals(if (c.isNull("encuadre")) null else c.getString("encuadre"), evaluarEncuadre(cuadro))
        }
    }

    @Test
    fun palabrasSegmentacionVectorYClasificacion() {
        val p = indice.getJSONObject("palabras")
        val nombres = p.getJSONObject("nombres").let { n -> n.keys().asSequence().associateWith { k -> n.getString(k) } }
        val clasificador = ClasificadorPalabras(bosque("palabras"), p.getJSONArray("clases").strings(), nombres,
            p.getDouble("umbral"), p.getDouble("umbral_sugerencia"))
        val lista = casos.getJSONArray("palabras")
        assertTrue(lista.length() >= 3)
        for (k in 0 until lista.length()) {
            val c = lista.getJSONObject(k)
            val cuadros = c.getJSONArray("cuadros").let { a -> List(a.length()) { if (a.isNull(it)) null else a.getJSONArray(it).floats() } }
            val seg = SegmentadorSenas()
            val terminadas = mutableListOf<List<FloatArray>>()
            for (f in cuadros + List(15) { cuadros.last() }) seg.agregar(f).terminada?.let { terminadas.add(it) }
            assertEquals(c.getInt("terminada"), terminadas.first().size)
            cerca(c.getJSONArray("vector").floats(), vectorSecuencia(terminadas.first()), 1e-4)
            val ev = clasificador.evaluar(terminadas.first())
            val opciones = c.getJSONArray("opciones")
            assertEquals(opciones.getJSONArray(0).getString(0), ev.mejor.texto)
            assertEquals(opciones.getJSONArray(0).getDouble(1), ev.mejor.confianza, 0.02)
            assertEquals(c.getDouble("prob_otra"), ev.probOtra, 0.02)
        }
    }

    @Test
    fun animacionesBuscanLasMismasSenas() {
        val nombres = indice.getJSONArray("animaciones").strings()
        val a = Animaciones(File(dirModelos, "animaciones.bin").readBytes(), nombres)
        val lista = casos.getJSONArray("animaciones")
        for (k in 0 until lista.length()) {
            val c = lista.getJSONObject(k)
            assertEquals(c.getJSONArray("senas").strings(), a.buscar(c.getString("texto")))
        }
        assertEquals(45, a.cuadros(nombres[0]).size)
        assertEquals(N_CUADRO, a.cuadros(nombres[0])[0].size)
    }
}

class SugerenciasTest {
    @Test
    fun mismasSugerenciasQueElPc() {
        val casos = JSONObject(javaClass.getResource("/casos.json")!!.readText()).getJSONArray("sugerencias")
        val s = Sugerencias(File("src/main/assets/modelos/palabras_es.txt").readLines())
        for (k in 0 until casos.length()) {
            val c = casos.getJSONObject(k)
            val esperadas = c.getJSONArray("opciones").let { a -> List(a.length()) { a.getString(it) } }
            assertEquals(c.getString("texto"), esperadas, s.para(c.getString("texto")))
        }
    }

    @Test
    fun completarCambiaLaPalabraEnCurso() {
        val b = BufferTexto()
        "HOLA".forEach { b.agregarLetra(it.toString()) }
        b.agregarEspacio()
        "MU".forEach { b.agregarLetra(it.toString()) }
        assertEquals("MU", b.palabraEnCurso)
        b.completar("MÚSICA")
        assertEquals("HOLA MÚSICA ", b.texto)
    }
}

class VerticalTest {
    @Test
    fun laManoEnUnaImagenVerticalTieneLaMismaFormaQueEn4x3() {
        // la misma mano, en píxeles, vista en una imagen 640×480 y en una vertical 360×640
        val px = List(21) { (200f + 9f * it) to (300f - 7f * (it % 5) - 3f * it) }
        val en4x3 = px.map { (x, y) -> Punto(x / 640f, y / 480f) }
        val enVertical = px.map { (x, y) -> Punto(x / 360f, y / 640f) }
        val a = normalizarLandmarks(como4x3(en4x3, 640, 480), false)
        val b = normalizarLandmarks(como4x3(enVertical, 360, 640), false)
        for (i in a.indices) assertEquals(a[i], b[i], 1e-5f)
        assertEquals(en4x3, como4x3(en4x3, 480, 360))  // el recorte 4:3 horizontal no cambia
    }

    @Test
    fun encuadreVerticalSeMideSobreElAnchoDeLaImagen() {
        fun pose(ancho: Float) = List(33) { Punto(0.5f, 0.45f) }.toMutableList().apply {
            this[0] = Punto(0.5f, 0.3f); this[11] = Punto(0.5f + ancho / 2, 0.45f); this[12] = Punto(0.5f - ancho / 2, 0.45f)
        }
        assertNull(evaluarEncuadre(CuadroCuerpo(pose(0.30f), null, null, 9f / 16f)))
        assertTrue(evaluarEncuadre(CuadroCuerpo(pose(0.55f), null, null, 9f / 16f))!!.startsWith("Aléjate"))
        assertTrue(evaluarEncuadre(CuadroCuerpo(pose(0.12f), null, null, 9f / 16f))!!.startsWith("Acércate"))
    }
}

class MotorTest {
    @Test
    fun bufferConfirmaTrasCincoCuadros() {
        val b = BufferTexto()
        repeat(4) { assertNull(b.procesar(Prediccion("A", 0.9))) }
        assertEquals("A", b.procesar(Prediccion("A", 0.9)))
        repeat(10) { assertNull(b.procesar(Prediccion("A", 0.9))) }  // sostenida no se repite
        b.procesar(null)
        repeat(5) { b.procesar(Prediccion("A", 0.9)) }
        assertEquals("AA", b.texto)
    }

    @Test
    fun segmentadorDeLetrasEntregaUnTrazo() {
        val seg = SegmentadorLetras()
        fun mano(dx: Float) = Array(21) { i -> floatArrayOf(0.5f + dx + i * 0.01f, 0.5f - i * 0.01f) }
        repeat(5) { assertNull(seg.agregar(mano(0f))) }
        for (k in 1..12) assertNull(seg.agregar(mano(0.03f * k)))
        assertTrue(seg.moviendo)
        var trazo: TrazoTerminado? = null
        repeat(Config.CUADROS_QUIETO) { trazo = seg.agregar(mano(0.36f)) ?: trazo }
        assertNotNull(trazo)
        assertTrue(trazo!!.puntos.size >= 12)
    }
}

/** Reposo aprendido (silva.palabras): sentada, la persona descansa las manos sobre la mesa. */
class ReposoTest {
    /** Cuadro con la mano izquierda (y su muñeca de la pose) a cierta altura; la derecha queda abajo. */
    private fun sentado(altura: Float) = FloatArray(N_CUADRO).also { f ->
        f[2] = 0.5f; f[4] = -0.5f  // hombros
        f[10] = 0.6f; f[11] = altura; f[12] = -0.6f; f[13] = 1.5f  // muñecas de la pose
        for (k in 0 until 21) { f[N_POSE + 2 * k] = 0.6f; f[N_POSE + 2 * k + 1] = altura }
        f[N_POSE + 42] = 1f
    }

    private fun cortes(aprender: Boolean): List<Double> {
        val cuadros = List(45) { sentado(0.5f) } + List(24) { sentado(-0.3f + 0.02f * (it % 6)) } + List(60) { sentado(0.5f) }
        val seg = SegmentadorSenas(aprender)
        return cuadros.mapIndexedNotNull { i, f -> seg.agregar(f, i / 30.0).terminada?.let { it.size / 30.0 } }
    }

    @Test
    fun conReposoAprendidoLaSenaTerminaAlVolverALaMesa() {
        val con = cortes(true)
        assertEquals(1, con.size)  // la seña, y no un tramo quieto al empezar
        assertTrue(con[0] < 1.5)
        assertTrue(cortes(false).all { it >= Config.SEGUNDOS_MAX - 0.1 })  // sin él se cortaba a los 4 s
    }
}
