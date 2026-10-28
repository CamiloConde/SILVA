package co.edu.utb.silva.nucleo

/**
 * Constantes de silva.config y silva.palabras. Las pruebas comprueban que coincidan con las de la
 * app de PC (casos.json, generado por scripts/exportar_movil.py).
 */
object Config {
    // Deletreo
    const val UMBRAL_CONFIANZA = 0.60  // con 0,80 muchas letras de manos nuevas no llegaban a escribirse
    const val CUADROS_ESTABLES = 5
    const val CONFIANZA_DETECCION = 0.6f
    const val CONFIANZA_SEGUIMIENTO = 0.4f  // con 0,6 una mano rápida se perdía a mitad del trazo

    // Letras con movimiento
    const val MOVIMIENTO_INICIO = 0.08
    const val MOVIMIENTO_FIN = 0.04
    const val CUADROS_QUIETO = 4
    const val MIN_CUADROS_MOVIMIENTO = 6
    const val SEGUNDOS_SIN_MANO_TRAZO = 0.3  // una mano rápida sale borrosa y se pierde un instante
    const val MAX_CUADROS_MOVIMIENTO = 75
    const val UMBRAL_MOVIMIENTO = 0.4
    const val RECORRIDO_MINIMO = 0.4
    const val SEGUNDOS_INICIO_TRAZO = 0.6

    // Palabras
    const val LONGITUD_FIJA = 20
    const val MIN_ACTIVOS = 8
    const val MAX_CUADROS = 120
    const val CUADROS_FIN = 10
    const val MARGEN = 2
    const val ALTURA_ACTIVA = 0.8
    const val MOVIMIENTO_ACTIVO = 0.12
    const val CONFIANZA_MANOS_PALABRAS = 0.4f
    const val SEGUNDOS_CORRECCION = 8.0
    const val SEGUNDOS_SUGERENCIA = 10.0
    const val CUADROS_REPETICION = 20

    // El segmentador de Palabras mide en segundos (silva.palabras): los valores en cuadros de arriba se
    // calibraron a 30 cuadros/s y el teléfono procesa 10-20
    const val FPS_REFERENCIA = 30.0
    const val SEGUNDOS_MIN_ACTIVOS = MIN_ACTIVOS / FPS_REFERENCIA
    const val SEGUNDOS_FIN = CUADROS_FIN / FPS_REFERENCIA
    const val SEGUNDOS_MAX = (MAX_CUADROS - 1) / FPS_REFERENCIA
    const val SEGUNDOS_MARGEN = MARGEN / FPS_REFERENCIA
    const val VELOCIDAD_ACTIVA = MOVIMIENTO_ACTIVO * FPS_REFERENCIA  // anchos de hombro por segundo
    const val SEGUNDOS_REPETICION = 0.4  // pausa entre la palabra escrita y la siguiente seña (silva.controlador)

    // Reposo de cada persona (silva.palabras): sentada, las manos descansan más arriba que de pie
    const val SEGUNDOS_QUIETA = 1.0  // tiempo con la muñeca quieta para tomar su altura como reposo
    const val VELOCIDAD_QUIETA = 0.6  // anchos de hombro por segundo
    const val REPOSO_MAS_ALTO = 0.3  // un reposo nunca se aprende más arriba que esto
    const val MARGEN_REPOSO = 0.25  // cuánto debe subir la mano sobre su reposo para contar como levantada

    // Recuperación de la mano perdida
    const val RECORTE_RECUPERACION = 1.8
    const val TAM_RECORTE = 256
    const val CONFIANZA_RECUPERACION = 0.3f

    // Imagen
    const val BRILLO_MINIMO = 55
    val ENCUADRE_HOMBROS = doubleArrayOf(0.15, 0.30)
    // Teléfono vertical (solo la app Android): ancho de hombros como fracción del ancho de la imagen. Las
    // señas ocupan unos 2,5-3 anchos de hombro a lo ancho, así que con hombros de ~0,30 los brazos caben.
    val ENCUADRE_HOMBROS_VERTICAL = doubleArrayOf(0.22, 0.40)
    val ENCUADRE_CENTRO_X = doubleArrayOf(0.38, 0.62)
    const val ENCUADRE_NARIZ_Y_MIN = 0.12
    const val ENCUADRE_HOMBROS_Y_MAX = 0.70
}
