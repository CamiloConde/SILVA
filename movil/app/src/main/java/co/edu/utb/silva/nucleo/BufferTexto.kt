package co.edu.utb.silva.nucleo

/**
 * Texto de la sesión y regla de confirmación de letras (RF-04, silva.buffer_texto): una letra se
 * escribe con confianza >= 0,80 durante 5 cuadros seguidos, y no se repite mientras se sostenga.
 */
class BufferTexto(
    val umbral: Double = Config.UMBRAL_CONFIANZA,
    private val cuadrosEstables: Int = Config.CUADROS_ESTABLES,
) {
    private val partes = mutableListOf<String>()
    private var candidata: String? = null
    private var racha = 0
    private var bloqueada: String? = null

    val texto get() = partes.joinToString("")
    val ultima get() = partes.lastOrNull()
    val progreso get() = minOf(racha.toDouble() / cuadrosEstables, 1.0)
    val vacio get() = partes.isEmpty()

    /** Registra la predicción de un cuadro; devuelve la letra si quedó confirmada. */
    fun procesar(p: Prediccion?): String? {
        if (p == null) {
            reiniciarRacha()
            bloqueada = null
            return null
        }
        if (p.confianza < umbral) {
            reiniciarRacha()
            return null
        }
        if (p.texto == candidata) {
            racha++
        } else {
            candidata = p.texto
            racha = 1
            if (p.texto != bloqueada) bloqueada = null
        }
        if (racha >= cuadrosEstables && p.texto != bloqueada) {
            partes.add(p.texto)
            bloqueada = p.texto
            return p.texto
        }
        return null
    }

    /** Interrumpe la letra en curso sin olvidar la bloqueada (mientras la mano traza una letra). */
    fun pausar() = reiniciarRacha()

    fun agregarLetra(letra: String, bloquear: String? = null) {
        partes.add(letra)
        reiniciarRacha()
        bloqueada = bloquear
    }

    /** Lo escrito después del último espacio (en Deletreo, la palabra que se está deletreando). */
    val palabraEnCurso: String
        get() = partes.takeLastWhile { it != " " }.joinToString("")

    /** «¿Quisiste decir?»: cambia la palabra en curso por `palabra` (letra por letra) y agrega un espacio. */
    fun completar(palabra: String) {
        while (partes.isNotEmpty() && partes.last() != " ") partes.removeAt(partes.size - 1)
        palabra.forEach { partes.add(it.toString()) }
        partes.add(" ")
        reiniciarRacha()
        bloqueada = null
    }

    fun agregarPalabra(palabra: String) {
        if (partes.isNotEmpty() && partes.last() != " ") partes.add(" ")
        partes.add(palabra)
    }

    fun reiniciarDeteccion() {
        reiniciarRacha()
        bloqueada = null
    }

    fun agregarEspacio() {
        if (partes.isNotEmpty() && partes.last() != " ") partes.add(" ")
    }

    fun borrarUltima() {
        if (partes.isNotEmpty()) partes.removeAt(partes.size - 1)
    }

    fun limpiar() {
        partes.clear()
        reiniciarRacha()
        bloqueada = null
    }

    private fun reiniciarRacha() {
        candidata = null
        racha = 0
    }
}
