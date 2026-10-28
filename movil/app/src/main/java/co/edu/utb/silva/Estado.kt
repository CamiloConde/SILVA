package co.edu.utb.silva

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.LifecycleOwner
import co.edu.utb.silva.nucleo.Config
import co.edu.utb.silva.nucleo.LETRAS_MOVIMIENTO
import co.edu.utb.silva.nucleo.CuadroCuerpo
import co.edu.utb.silva.nucleo.Modo
import co.edu.utb.silva.nucleo.Motor
import co.edu.utb.silva.nucleo.PalabraPendiente
import co.edu.utb.silva.nucleo.evaluarEncuadre
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.ceil

const val AVISO_POCA_LUZ = "Poca luz: los movimientos salen borrosos y se pierde la mano. Enciende una luz de frente."
const val AVISO_SIN_MANO = "Mantén la mano dentro del recuadro."

/**
 * Señas a texto (la cámara), texto a señas (escribir o dictar y verlo en señas), conversación, historial y
 * entrenar (grabar muestras propias para reentrenar los modelos en el PC).
 */
enum class Pantalla { TRADUCIR, TEXTO_A_SENAS, CONVERSAR, HISTORIAL, ENTRENAR }

/** Letra quieta: cuadros que se guardan por toma, tras dejar este tiempo para formar la seña. */
const val CUADROS_TOMA_LETRA = 30
const val SEGUNDOS_PREPARAR_LETRA = 0.6
enum class Origen(val rotulo: String) { SENAS("SEÑAS"), VOZ("VOZ"), ESCRITO("ESCRITO") }

/** Una intervención de la conversación: lo que se signó (traducido) o lo que respondió la persona oyente. */
data class Mensaje(val origen: Origen, val texto: String, val hora: String, val senas: List<String>)

/**
 * Estado de la pantalla y acciones del usuario (lo que en el PC hace VentanaPrincipal).
 * El motor se usa desde el hilo de la cámara y desde la pantalla: todo acceso va con synchronized.
 */
class Estado(private val context: Context, val modelos: Modelos, aceleracion: Aceleracion = Aceleracion()) {
    val historial = Historial(context)
    val motor = Motor(modelos.letras, modelos.movimiento, modelos.palabras)
    val pantallaCamara = PantallaCamara(context)
    val vista = pantallaCamara.vista
    val voz = Voz(context)
    private val camara = Camara(context, motor, Detectores(context, aceleracion), pantallaCamara.previa,
        alUsarVistaPrevia = { vista.sobreVideo = it }) { mostrar(it) }
    private var sesion = -1L
    private var confirmadaHasta = 0.0
    private val horaCorta = SimpleDateFormat("HH:mm", Locale.US)
    private val principal = android.os.Handler(android.os.Looper.getMainLooper())

    var pantalla by mutableStateOf(Pantalla.TRADUCIR); private set
    var activo by mutableStateOf(false); private set
    var modo by mutableStateOf(motor.modo); private set
    var frontal by mutableStateOf(false); private set
    var detectado by mutableStateOf("–"); private set
    var dudosa by mutableStateOf(true); private set
    var confianza by mutableStateOf<Double?>(null); private set
    var segmentos by mutableStateOf(0); private set  // estado de la detección en 5 segmentos
    var segmentosAzules by mutableStateOf(false); private set  // azul = confirmada; ocre = leyendo seña
    var estadoTexto by mutableStateOf("Cámara apagada"); private set
    var texto by mutableStateOf(""); private set
    var sugerencias by mutableStateOf<List<String>>(emptyList()); private set
    var pendiente by mutableStateOf<PalabraPendiente?>(null); private set
    var progresoPendiente by mutableStateOf(0.0); private set
    var banda by mutableStateOf<String?>(null); private set
    var leyendo by mutableStateOf(false); private set
    var fps by mutableStateOf(0); private set  // entero: la pantalla solo se vuelve a dibujar si cambia
    var aceleracion by mutableStateOf(""); private set  // "GPU" o "CPU": dónde corre MediaPipe
    val mensajes = mutableStateListOf<Mensaje>()
    var escuchando by mutableStateOf<String?>(null); private set  // lo que va entendiendo «Hablar»
    var textoGrande by mutableStateOf(false)
    var maximizado by mutableStateOf(false)  // cámara en pantalla completa, con lo traducido debajo
    var error by mutableStateOf<String?>(null)

    init {
        motor.alEscribir = { palabra, confianza -> if (sesion >= 0) historial.registrar(sesion, palabra, confianza) }
        // las correcciones de palabras se guardan como muestras para entrenar, junto a las de Entrenar
        motor.alCorregir = { clave, cuadros, fps ->
            principal.post {
                muestras.agregarPalabra(clave, persona.trim(), cuadros, fps)
                actualizarConteo()
                estadoTexto = "Corrección guardada para entrenar"
            }
        }
    }

    // ------------------------------------------------------------------ navegación
    /**
     * Al pasar a Conversar se apaga la cámara y lo que se tradujo queda como un mensaje de SEÑAS;
     * «Señar» vuelve a Traducir y enciende la cámara.
     */
    fun irA(destino: Pantalla, dueno: LifecycleOwner) {
        if (destino == pantalla) return
        if (pantalla == Pantalla.ENTRENAR) {
            detener()
            synchronized(motor) { motor.entrenando = false }
        }
        if (destino == Pantalla.ENTRENAR) synchronized(motor) { motor.entrenando = true }
        if (pantalla == Pantalla.TRADUCIR && destino != Pantalla.TRADUCIR) {
            detener()
            val traducido = synchronized(motor) { motor.buffer.texto.trim() }
            if (traducido.isNotEmpty()) {
                mensajes.add(Mensaje(Origen.SENAS, traducido.uppercase(), horaCorta.format(Date()), emptyList()))
                editar { buffer.limpiar() }
            }
        }
        detenerEscucha()
        pantalla = destino
    }

    fun senar(dueno: LifecycleOwner, conPermiso: Boolean) {
        irA(Pantalla.TRADUCIR, dueno)
        if (conPermiso) iniciar(dueno)
    }

    // ------------------------------------------------------------------ cámara
    fun iniciar(dueno: LifecycleOwner) {
        if (activo) return
        synchronized(motor) { motor.reiniciar() }
        sesion = if (pantalla == Pantalla.ENTRENAR) -1 else historial.iniciarSesion()  // grabar muestras no es una sesión
        camara.frontal = frontal
        vista.espejo = frontal
        camara.iniciar(dueno) { error = it; detener() }
        activo = true
        texto = ""
        reiniciarDeteccion()
        estadoTexto = if (modo == Modo.LETRAS) "Sin mano en el recuadro" else "Manos abajo · haz la seña y vuelve a bajarlas"
    }

    fun detener() {
        if (!activo) return
        camara.detener()
        synchronized(motor) { motor.cerrarPendiente() }
        if (sesion >= 0) historial.guardarSesion(sesion, motor.buffer.texto)
        detenerGrabacion()
        activo = false
        vista.limpiar()
        reiniciarDeteccion()
        estadoTexto = "Cámara apagada"
    }

    fun cerrar() {
        detener()
        camara.cerrar()
        voz.close()
    }

    fun cambiarCamara(dueno: LifecycleOwner) {
        frontal = !frontal
        if (activo) {
            camara.frontal = frontal
            vista.espejo = frontal
            camara.iniciar(dueno) { error = it; detener() }
        }
    }

    fun cambiarModo(nuevo: Modo) {
        if (nuevo == modo) return
        synchronized(motor) { motor.cambiarModo(nuevo) }
        modo = nuevo
        reiniciarDeteccion()
        actualizarSugerencias()
    }

    private fun reiniciarDeteccion() {
        detectado = "–"
        dudosa = true
        confianza = null
        segmentos = 0
        pendiente = null
        banda = null
        leyendo = false
        vista.guia = null
        vista.recuadro = false
    }

    // ------------------------------------------------------------------ texto
    private fun editar(accion: Motor.() -> Unit) {
        synchronized(motor) { motor.accion() }
        texto = motor.buffer.texto
        actualizarSugerencias()
    }

    fun borrar() = editar { buffer.borrarUltima() }
    fun limpiar() = editar { buffer.limpiar() }
    fun espacio() = editar { buffer.agregarEspacio() }
    fun completar(palabra: String) = editar { buffer.completar(palabra) }

    fun escuchar() = voz.leer(texto)

    fun copiar() {
        if (texto.isBlank()) return
        (context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
            .setPrimaryClip(ClipData.newPlainText("SILVA", texto.trim()))
        estadoTexto = "Texto copiado"
    }

    private fun actualizarSugerencias() {
        sugerencias = if (modo == Modo.LETRAS && pendiente == null)
            modelos.sugerencias.para(synchronized(motor) { motor.buffer.palabraEnCurso }) else emptyList()
    }

    /** RF-13: elige una opción de la palabra pendiente (0 = la más probable). */
    fun elegir(opcion: Int) {
        val p = pendiente ?: return
        var escrita: String? = null
        editar { escrita = confirmarPendiente(opcion) }
        escrita?.let { confirmar(it, p.opciones[opcion].confianza) }
        pendiente = null
    }

    fun descartar() {
        editar { descartarPendiente() }
        pendiente = null
    }

    // ------------------------------------------------------------------ conversación (RF-09)
    fun responderPorEscrito(t: String) = agregarRespuesta(Origen.ESCRITO, t)

    private fun agregarRespuesta(origen: Origen, t: String) {
        val limpio = t.trim()
        if (limpio.isEmpty()) return
        historial.guardarRespuesta(limpio)
        mensajes.add(Mensaje(origen, limpio, horaCorta.format(Date()), modelos.animaciones.buscar(limpio)))
    }

    /** «Hablar»: lo dicho queda en la conversación o, en «Texto a señas», se muestra en señas. */
    fun hablar(paraSenas: Boolean = false) {
        if (escuchando != null) {
            detenerEscucha()
            return
        }
        escuchando = ""
        voz.escuchar(parcial = { escuchando = it }) { frase ->
            escuchando = null
            val texto = frase?.replaceFirstChar { it.uppercase() }
            when {
                texto == null -> error = "No se entendió. Toca «Hablar» e inténtalo de nuevo cerca del teléfono."
                paraSenas -> mostrarEnSenas(texto)
                else -> agregarRespuesta(Origen.VOZ, texto)
            }
        }
    }

    // ------------------------------------------------------------------ texto a señas
    var mostrado by mutableStateOf<String?>(null); private set
    var senasMostradas by mutableStateOf<List<String>>(emptyList()); private set

    /** Muestra el texto en grande y anima las señas conocidas que contiene (como «Responder» en el PC). */
    fun mostrarEnSenas(t: String) {
        val limpio = t.trim()
        if (limpio.isEmpty()) return
        historial.guardarRespuesta(limpio)
        mostrado = limpio
        senasMostradas = modelos.animaciones.buscar(limpio)
    }

    private fun detenerEscucha() {
        voz.detenerEscucha()
        escuchando = null
    }

    // ------------------------------------------------------------------ cada cuadro
    private fun ahora() = System.nanoTime() / 1e9

    private fun mostrar(f: Fotograma) {
        if (!activo || f.modo != modo) return
        fps = Math.round(f.fps).toInt()
        aceleracion = f.aceleracion
        if (pantalla == Pantalla.ENTRENAR) {
            entrenarCuadro(f)
            return
        }
        val r = f.resultado
        if (r.texto != texto) {
            texto = r.texto
            actualizarSugerencias()
        }
        val confirmando = ahora() < confirmadaHasta
        if (f.modo == Modo.LETRAS) {
            vista.guia = null
            vista.recuadro = true
            leyendo = r.trazando
            val p = r.prediccion
            when {
                r.confirmada != null -> confirmar(r.confirmada, p?.confianza ?: 0.0)
                r.trazando -> {
                    banda = null; detectado = "…"; dudosa = true; confianza = null
                    segmentosAzules = false; segmentos = ((ahora() * 6).toInt() % (Config.CUADROS_ESTABLES + 1))
                    estadoTexto = "Leyendo el trazo de la letra…"
                }
                p == null -> {
                    banda = if (f.brillo < Config.BRILLO_MINIMO) AVISO_POCA_LUZ else AVISO_SIN_MANO
                    if (!confirmando) {
                        detectado = "–"; dudosa = true; confianza = null; segmentos = 0
                        estadoTexto = "Sin mano en el recuadro"
                    }
                }
                confirmando && r.progreso == 0.0 -> banda = null  // se deja ver «confirmada y agregada al texto»
                else -> {
                    banda = null
                    val aceptable = p.confianza >= motor.buffer.umbral
                    detectado = p.texto; dudosa = !aceptable; confianza = p.confianza
                    segmentosAzules = false
                    segmentos = Math.round(r.progreso * Config.CUADROS_ESTABLES).toInt()
                    estadoTexto = if (aceptable) "Leyendo seña · $segmentos de ${Config.CUADROS_ESTABLES} cuadros"
                    else "Seña poco clara: sostén la mano quieta"
                }
            }
        } else {
            val c = r.cuerpo!!
            vista.recuadro = false
            leyendo = r.grabandoSena
            if (r.confirmada != null) confirmar(r.confirmada, motor.ultimaConfianza ?: 0.0)
            pendiente = r.pendiente
            val p = r.pendiente
            when {
                p != null -> {
                    progresoPendiente = p.progreso(r.ahora)
                    detectado = p.opciones[0].texto; dudosa = !p.automatica; confianza = p.opciones[0].confianza
                    segmentosAzules = p.automatica
                    segmentos = if (p.automatica) Config.CUADROS_ESTABLES else 2
                    estadoTexto = if (p.automatica) "Palabra escrita · si no era, elige otra" else "Seña dudosa · elige una opción"
                }
                r.grabandoSena -> {
                    segmentosAzules = false
                    // un segmento cada 0,3 s de seña
                    segmentos = maxOf(1, ceil(r.progreso * Config.SEGUNDOS_MAX / 0.3).toInt()).coerceAtMost(Config.CUADROS_ESTABLES)
                    estadoTexto = "Leyendo seña…"
                }
                !confirmando -> {
                    segmentos = 0
                    estadoTexto = "Manos abajo · haz la seña y vuelve a bajarlas"
                }
            }
            val encuadre = evaluarEncuadre(c)
            val enReposo = !r.grabandoSena && r.pendiente == null
            vista.guia = if (enReposo) (if (encuadre != null || c.pose == null) "ajustar" else "ok") else null
            banda = when {
                f.brillo < Config.BRILLO_MINIMO -> AVISO_POCA_LUZ
                c.pose == null -> "Colócate frente a la cámara: deben verse los hombros y las manos."
                encuadre != null && enReposo -> "$encuadre (ubícate dentro de la silueta)."
                manoEnBorde(c) -> "Aléjate un poco: una mano se sale del cuadro."
                else -> null
            }
        }
        vista.mostrar(f)
    }

    // ------------------------------------------------------------------ entrenar (muestras propias)
    val muestras = Muestras(context)
    private val preferencias = context.getSharedPreferences("silva", Context.MODE_PRIVATE)
    var persona by mutableStateOf(preferencias.getString("persona", "") ?: ""); private set
    var objetivo by mutableStateOf<String?>(null); private set  // clave de la palabra o letra que se graba
    var grabandoMuestras by mutableStateOf(false); private set
    var avisoEntrenar by mutableStateOf(""); private set
    var conteoMuestras by mutableStateOf(muestras.conteo()); private set
    var totalMuestras by mutableStateOf(muestras.total); private set
    var progresoToma by mutableStateOf(0f); private set  // letra quieta: cuánto lleva la toma (0-1)
    private val tomaCuadros = mutableListOf<FloatArray>()
    private val tomaPuntos = mutableListOf<Array<FloatArray>>()
    private var tomaIzquierdas = 0
    private var tomaAciertos = 0
    private var tomaPrimeraMano: Double? = null

    /** Qué se graba para la clave elegida, según el modo. */
    fun tipoMuestra(clave: String) = when {
        modo == Modo.PALABRAS -> TipoMuestra.PALABRA
        clave in LETRAS_MOVIMIENTO -> TipoMuestra.TRAZO
        else -> TipoMuestra.LETRA
    }

    fun nombreObjetivo(clave: String) = if (modo == Modo.PALABRAS) modelos.palabras.nombre(clave) else clave

    fun cuantas(clave: String) = conteoMuestras[tipoMuestra(clave).clave to clave] ?: 0

    fun ponerPersona(p: String) {
        persona = p
        preferencias.edit().putString("persona", p.trim()).apply()
    }

    fun elegirObjetivo(clave: String) {
        detenerGrabacion()
        objetivo = clave
        avisoEntrenar = instruccion(clave)
    }

    fun cambiarModoEntrenar(nuevo: Modo) {
        detenerGrabacion()
        objetivo = null
        avisoEntrenar = ""
        cambiarModo(nuevo)
    }

    private fun instruccion(clave: String) = when (tipoMuestra(clave)) {
        TipoMuestra.PALABRA -> "Toca «Grabar» y haz «${nombreObjetivo(clave)}» varias veces, bajando las manos entre una y otra."
        TipoMuestra.TRAZO -> "Toca «Grabar» y traza la $clave varias veces; quédate quieto al terminar cada una."
        TipoMuestra.LETRA -> "Toca «Grabar» y sostén la $clave quieta dentro del recuadro hasta que se llene la barra."
    }

    /** Empieza o termina de grabar. La cámara la enciende la pantalla (necesita el permiso). */
    fun alternarGrabacion(): Boolean {
        if (grabandoMuestras) {
            detenerGrabacion()
            return true
        }
        val clave = objetivo ?: run { error = "Elige primero qué vas a grabar."; return false }
        if (persona.isBlank()) {
            error = "Escribe quién graba (tu nombre o un apodo): sirve para medir si el modelo funciona con personas nuevas."
            return false
        }
        grabandoMuestras = true
        reiniciarToma()
        avisoEntrenar = when (tipoMuestra(clave)) {
            TipoMuestra.PALABRA -> "Grabando: haz «${nombreObjetivo(clave)}» y baja las manos. Repite las veces que quieras."
            TipoMuestra.TRAZO -> "Grabando: traza la $clave y quédate quieto. Repite las veces que quieras."
            TipoMuestra.LETRA -> "Forma la $clave dentro del recuadro y sostenla…"
        }
        return true
    }

    fun detenerGrabacion() {
        grabandoMuestras = false
        reiniciarToma()
    }

    private fun reiniciarToma() {
        tomaCuadros.clear()
        tomaPuntos.clear()
        tomaIzquierdas = 0
        tomaAciertos = 0
        tomaPrimeraMano = null
        progresoToma = 0f
    }

    fun borrarUltimaMuestra() {
        val (tipo, clave) = muestras.borrarUltima() ?: return
        actualizarConteo()
        avisoEntrenar = "Se borró la última muestra ($tipo «$clave»)."
    }

    fun borrarTodasLasMuestras() {
        muestras.borrarTodas()
        actualizarConteo()
        avisoEntrenar = "Se borraron todas las muestras."
    }

    private fun actualizarConteo() {
        conteoMuestras = muestras.conteo()
        totalMuestras = muestras.total
    }

    /** Cada cuadro mientras se entrena: el esqueleto, los avisos, lo que entiende el modelo y la muestra. */
    private fun entrenarCuadro(f: Fotograma) {
        val r = f.resultado
        leyendo = r.trazando || r.grabandoSena
        if (f.modo == Modo.PALABRAS) {
            vista.recuadro = false
            val c = r.cuerpo
            val encuadre = c?.let { evaluarEncuadre(it) }
            vista.guia = if (!r.grabandoSena) (if (encuadre != null || c?.pose == null) "ajustar" else "ok") else null
            banda = when {
                f.brillo < Config.BRILLO_MINIMO -> AVISO_POCA_LUZ
                c?.pose == null -> "Colócate frente a la cámara: deben verse los hombros y las manos."
                encuadre != null && !r.grabandoSena -> "$encuadre (ubícate dentro de la silueta)."
                else -> null
            }
        } else {
            vista.guia = null
            vista.recuadro = true
            banda = if (f.brillo < Config.BRILLO_MINIMO) AVISO_POCA_LUZ else if (r.mano == null) AVISO_SIN_MANO else null
        }
        r.prediccion?.let { detectado = it.texto; confianza = it.confianza; dudosa = false }
        val clave = objetivo
        if (grabandoMuestras && clave != null) capturar(clave, f)
        vista.mostrar(f)
    }

    private fun capturar(clave: String, f: Fotograma) {
        val r = f.resultado
        val nombre = nombreObjetivo(clave)
        fun entendio() = r.prediccion?.let { " · el modelo entendió «${it.texto}» (${(it.confianza * 100).toInt()} %)" } ?: ""
        when (tipoMuestra(clave)) {
            TipoMuestra.PALABRA -> r.senaTerminada?.let { cuadros ->
                muestras.agregarPalabra(clave, persona.trim(), cuadros, f.fps)
                actualizarConteo()
                avisoEntrenar = "Muestra ${cuantas(clave)} de «$nombre» guardada${entendio()}. Haz la siguiente."
            }
            TipoMuestra.TRAZO -> r.trazo?.let { t ->
                muestras.agregarTrazo(clave, persona.trim(), t.puntos, t.izquierda)
                actualizarConteo()
                avisoEntrenar = "Muestra ${cuantas(clave)} de la $clave guardada${entendio()}. Haz la siguiente."
            }
            TipoMuestra.LETRA -> {
                val vector = r.vectorLetra ?: return
                val puntos = r.puntosIsotropicos ?: return
                val t = ahora()
                val primera = tomaPrimeraMano ?: t.also { tomaPrimeraMano = it }
                if (t - primera < SEGUNDOS_PREPARAR_LETRA) return  // se deja formar la seña
                tomaCuadros.add(vector)
                tomaPuntos.add(puntos)
                if (r.mano?.izquierda == true) tomaIzquierdas++
                if (r.prediccion?.texto == clave) tomaAciertos++
                progresoToma = tomaCuadros.size.toFloat() / CUADROS_TOMA_LETRA
                if (tomaCuadros.size >= CUADROS_TOMA_LETRA) {
                    muestras.agregarLetra(clave, persona.trim(), tomaCuadros.toList(), tomaPuntos.toList(),
                        tomaIzquierdas * 2 > tomaCuadros.size)
                    val acierto = tomaAciertos * 100 / tomaCuadros.size
                    actualizarConteo()
                    detenerGrabacion()
                    avisoEntrenar = "Muestra ${cuantas(clave)} de la $clave guardada · el modelo actual la reconoció en el " +
                        "$acierto % de los cuadros. Toca «Grabar» para otra (mejor moviendo un poco la mano)."
                }
            }
        }
    }

    private fun confirmar(t: String, conf: Double) {
        detectado = t
        dudosa = false
        confianza = conf
        segmentos = Config.CUADROS_ESTABLES
        segmentosAzules = true
        estadoTexto = if (modo == Modo.PALABRAS) "Palabra «$t» escrita" else "Letra $t confirmada y agregada al texto"
        confirmadaHasta = ahora() + 0.8
        texto = motor.buffer.texto
        actualizarSugerencias()
    }

    private fun manoEnBorde(c: CuadroCuerpo): Boolean {
        for (mano in listOf(c.manoIzquierda, c.manoDerecha)) {
            if (mano != null && mano.any { it.x < 0.03f || it.x > 0.97f || it.y < 0.03f }) return true
        }
        val pose = c.pose ?: return false
        return intArrayOf(15, 16).any { pose[it].x !in 0f..1f || pose[it].y !in 0f..1f }
    }
}
