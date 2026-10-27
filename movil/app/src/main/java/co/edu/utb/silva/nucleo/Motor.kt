package co.edu.utb.silva.nucleo

enum class Modo { LETRAS, PALABRAS }

/**
 * Los 42 valores de la mano no dependen de la posición ni del tamaño, pero sí de la proporción de la imagen
 * (x va de 0 a 1 en el ancho, y en el alto). El modelo de letras se entrenó con imágenes 640×480 (4:3):
 * con el teléfono vertical (o cualquier otra proporción) se escala la x para que la mano tenga la misma forma
 * que tendría en una imagen 4:3. En una imagen 4:3 no cambia nada.
 */
fun como4x3(puntos: List<Punto>, ancho: Int, alto: Int): List<Punto> {
    val f = (ancho.toFloat() / alto) / (4f / 3f)
    return if (kotlin.math.abs(f - 1f) < 1e-3f) puntos else puntos.map { Punto(it.x * f, it.y) }
}

/** Mano detectada en modo Deletreo: 21 puntos (0-1) y si es la izquierda. */
data class ManoDetectada(val puntos: List<Punto>, val izquierda: Boolean)

/**
 * Palabra reconocida con sus opciones, para corregirla (RF-13).
 * - escrita (`automatica`): era segura y ya se escribió; hasta que vence se puede cambiar o borrar.
 * - sugerencia: era dudosa; solo se escribe si alguien elige una opción.
 */
data class PalabraPendiente(val opciones: List<Prediccion>, val automatica: Boolean, val creada: Double, val vence: Double) {
    fun progreso(ahora: Double) = ((ahora - creada) / (vence - creada)).coerceIn(0.0, 1.0)
}

data class Resultado(
    val prediccion: Prediccion?,
    val confirmada: String?,
    val texto: String,
    val progreso: Double,
    val ahora: Double,
    val mano: ManoDetectada? = null,  // Deletreo
    val trazando: Boolean = false,  // Deletreo: la mano traza una letra con movimiento
    val cuerpo: CuadroCuerpo? = null,  // Palabras
    val grabandoSena: Boolean = false,
    val pendiente: PalabraPendiente? = null,
    // al entrenar: lo que se guarda como muestra
    val senaTerminada: List<FloatArray>? = null,  // Palabras: la seña completa (vectores de 100 valores)
    val vectorLetra: FloatArray? = null,  // Deletreo: los 42 valores que recibe el modelo de letras
    val puntosIsotropicos: Array<FloatArray>? = null,  // Deletreo: la mano en unidades iguales en x e y
    val trazo: TrazoTerminado? = null,  // Deletreo: un trazo terminado
)

/**
 * Lógica de ControladorSILVA sin cámara ni detectores: recibe lo que detectó MediaPipe en cada
 * cuadro y decide qué se escribe. `alEscribir` registra cada letra o palabra en el historial.
 */
class Motor(
    private val clasificadorLetras: ClasificadorLetras,
    val clasificadorMovimiento: ClasificadorMovimiento?,
    val clasificadorPalabras: ClasificadorPalabras?,
    private val reloj: () -> Double = { System.nanoTime() / 1e9 },
    var alEscribir: (String, Double) -> Unit = { _, _ -> },
) {
    val buffer = BufferTexto()
    var modo = if (clasificadorPalabras != null) Modo.PALABRAS else Modo.LETRAS
        private set
    var pendiente: PalabraPendiente? = null
        private set
    var ultimaConfianza: Double? = null
        private set

    /**
     * Al entrenar (grabar muestras) se reconoce igual, para mostrar qué entiende el modelo, pero no se
     * escribe nada ni se sugiere: cada seña o trazo terminado se entrega en el Resultado para guardarlo.
     */
    var entrenando = false
        set(valor) {
            field = valor
            segmentador.reiniciar()
            segmentadorLetras.reiniciar()
            buffer.reiniciarDeteccion()
            pendiente = null
        }

    private val segmentador = SegmentadorSenas()
    private val segmentadorLetras = SegmentadorLetras()
    private var ultimaPalabra: String? = null
    private var tPalabra = Double.NEGATIVE_INFINITY  // cuándo se escribió (o sugirió) la última palabra
    private var tEstatica: Double? = null
    private var tInicioTrazo: Double? = null

    /** Letras del modo Deletreo, en orden alfabético. */
    val letras: List<String>
        get() {
            val todas = clasificadorLetras.letras.toSet() + (clasificadorMovimiento?.letras ?: emptyList())
            return LETRAS.filter { it in todas }
        }

    fun cambiarModo(nuevo: Modo) {
        cerrarPendiente()
        modo = nuevo
        segmentador.reiniciar()
        segmentadorLetras.reiniciar()
        buffer.reiniciarDeteccion()
    }

    fun reiniciar() {
        buffer.limpiar()
        segmentador.reiniciar()
        segmentadorLetras.reiniciar()
        pendiente = null
        ultimaConfianza = null
        tEstatica = null
    }

    // ------------------------------------------------------------------ Deletreo
    fun procesarLetras(mano: ManoDetectada?, ancho: Int, alto: Int): Resultado {
        if (entrenando) return letrasAlEntrenar(mano, ancho, alto)
        val ahora = reloj()
        var prediccion = mano?.let { clasificadorLetras.predecir(normalizarLandmarks(como4x3(it.puntos, ancho, alto), it.izquierda)) }
        var confirmada: String? = null
        val trazo = seguirTrazo(mano, ancho, alto, prediccion, ahora)
        if (trazo != null) {
            confirmada = trazo.texto
            prediccion = trazo
        } else if (segmentadorLetras.moviendo) {
            buffer.pausar()
        } else {
            confirmada = buffer.procesar(prediccion)
            if (confirmada != null) tEstatica = ahora
        }
        if (confirmada != null) {
            ultimaConfianza = prediccion!!.confianza
            alEscribir(confirmada, prediccion.confianza)
        }
        return Resultado(prediccion, confirmada, buffer.texto, buffer.progreso, ahora, mano = mano,
            trazando = segmentadorLetras.moviendo)
    }

    private fun letrasAlEntrenar(mano: ManoDetectada?, ancho: Int, alto: Int): Resultado {
        val ahora = reloj()
        val vector = mano?.let { normalizarLandmarks(como4x3(it.puntos, ancho, alto), it.izquierda) }
        val iso = mano?.let { aIsotropicas(it.puntos, ancho, alto) }
        var prediccion = vector?.let { clasificadorLetras.predecir(it) }
        val trazo = segmentadorLetras.agregar(iso, mano?.izquierda ?: false)
        if (trazo != null) clasificadorMovimiento?.let { prediccion = it.predecir(trazo) }
        return Resultado(prediccion, null, buffer.texto, 0.0, ahora, mano = mano, trazando = segmentadorLetras.moviendo,
            vectorLetra = vector, puntosIsotropicos = iso, trazo = trazo)
    }

    private fun seguirTrazo(mano: ManoDetectada?, ancho: Int, alto: Int, estatica: Prediccion?, ahora: Double): Prediccion? {
        val clasificador = clasificadorMovimiento ?: return null
        val antes = segmentadorLetras.moviendo
        val trazo = segmentadorLetras.agregar(mano?.let { aIsotropicas(it.puntos, ancho, alto) }, mano?.izquierda ?: false)
        if (segmentadorLetras.moviendo && !antes) tInicioTrazo = ahora
        if (trazo == null) return null
        val p = clasificador.predecir(trazo)
        if (p.texto !in LETRAS_MOVIMIENTO || p.confianza < Config.UMBRAL_MOVIMIENTO) return null
        val te = tEstatica
        val ti = tInicioTrazo
        // la letra estática escrita justo antes del trazo era su comienzo (la I de la J): se reemplaza
        if (te != null && ti != null && ti - te <= Config.SEGUNDOS_INICIO_TRAZO && buffer.ultima != null && buffer.ultima != " ") {
            buffer.borrarUltima()
        }
        tEstatica = null
        buffer.agregarLetra(p.texto, bloquear = estatica?.texto)
        return p
    }

    // ------------------------------------------------------------------ Palabras
    fun procesarPalabras(cuadro: CuadroCuerpo): Resultado {
        val clasificador = clasificadorPalabras ?: error("Falta el modelo de palabras")
        val ahora = reloj()
        val estado = segmentador.agregar(caracteristicasCuadro(cuadro), ahora)
        if (entrenando) {
            val terminada = estado.terminada
            val p = terminada?.let { clasificador.evaluar(it).mejor }
            val progreso = if (estado.grabando) minOf(estado.segundos / Config.SEGUNDOS_MAX, 1.0) else 0.0
            return Resultado(p, null, buffer.texto, progreso, ahora, cuerpo = cuadro, grabandoSena = estado.grabando,
                senaTerminada = terminada)
        }
        var confirmada: String? = null
        pendiente?.let { if (estado.grabando || ahora >= it.vence) cerrarPendiente() }

        var prediccion: Prediccion? = null
        val terminada = estado.terminada
        if (terminada != null) {
            val ev = clasificador.evaluar(terminada)
            prediccion = ev.mejor
            val inicio = estado.inicio
            val repetida = prediccion.texto == ultimaPalabra && inicio != null && inicio - tPalabra < Config.SEGUNDOS_REPETICION
            val segura = prediccion.confianza >= clasificador.umbral && prediccion.confianza >= ev.probOtra
            val dudosa = prediccion.confianza >= clasificador.umbralSugerencia && prediccion.confianza >= 0.5 * ev.probOtra
            if (!repetida && (segura || dudosa)) {
                cerrarPendiente()
                if (segura) {  // se escribe apenas se reconoce; queda unos segundos para corregirla
                    escribir(prediccion)
                    confirmada = prediccion.texto
                }
                val plazo = if (segura) Config.SEGUNDOS_CORRECCION else Config.SEGUNDOS_SUGERENCIA
                pendiente = PalabraPendiente(ev.opciones.take(3), segura, ahora, ahora + plazo)
                ultimaPalabra = prediccion.texto
                tPalabra = ahora
            }
        }
        val progreso = if (estado.grabando) minOf(estado.segundos / Config.SEGUNDOS_MAX, 1.0) else 0.0
        return Resultado(prediccion, confirmada, buffer.texto, progreso, ahora, cuerpo = cuadro,
            grabandoSena = estado.grabando, pendiente = pendiente)
    }

    /** Elige una opción: en una sugerencia la escribe; en una palabra ya escrita, la cambia. */
    fun confirmarPendiente(opcion: Int = 0): String? {
        val p = pendiente ?: return null
        if (opcion >= p.opciones.size) return null
        val elegida = p.opciones[opcion]
        pendiente = null
        if (p.automatica) {
            if (opcion == 0) return elegida.texto
            buffer.borrarUltima()
        }
        escribir(elegida)
        return elegida.texto
    }

    /** Descarta la sugerencia, o borra la palabra que se acaba de escribir. */
    fun descartarPendiente() {
        val p = pendiente ?: return
        if (p.automatica && buffer.ultima == p.opciones[0].texto) buffer.borrarUltima()
        ultimaPalabra = null
        pendiente = null
    }

    fun cerrarPendiente() {
        pendiente = null
    }

    private fun escribir(p: Prediccion) {
        ultimaPalabra = p.texto
        buffer.agregarPalabra(p.texto)
        ultimaConfianza = p.confianza
        alEscribir(p.texto, p.confianza)
    }
}
