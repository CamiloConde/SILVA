package co.edu.utb.silva

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.ViewGroup
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.isImeVisible
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import co.edu.utb.silva.nucleo.Animaciones
import co.edu.utb.silva.nucleo.GuiasLetras
import co.edu.utb.silva.nucleo.acercarTrazo
import co.edu.utb.silva.nucleo.encuadre
import co.edu.utb.silva.nucleo.manoEn
import co.edu.utb.silva.nucleo.CONEXIONES_MANO
import co.edu.utb.silva.nucleo.LETRAS
import co.edu.utb.silva.nucleo.LETRAS_MOVIMIENTO
import co.edu.utb.silva.nucleo.LETRAS_ESTATICAS
import co.edu.utb.silva.nucleo.Modo
import co.edu.utb.silva.nucleo.N_MANO
import co.edu.utb.silva.nucleo.N_POSE
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

// Identidad v2 (propuesta de diseño)
private val TINTA = Color(0xFF16181D)  // texto, cámara
private val GRAFITO = Color(0xFF5B616B)  // texto secundario
private val LINEA = Color(0xFFE3E1DA)  // bordes, divisiones
private val PAPEL = Color(0xFFF7F6F2)  // fondo
private val AZUL = Color(0xFF1F4FD8)  // acción, confirmado
private val OCRE = Color(0xFFE8A317)  // leyendo seña
private val BLANCO = Color(0xFFFFFFFF)
private val APAGADO = Color(0xFFA9ADB4)
private val BORDE_BOTON = Color(0xFFCFCCC3)

private val PLEX = FontFamily(
    Font(R.font.ibm_plex_sans_regular, FontWeight.Normal),
    Font(R.font.ibm_plex_sans_medium, FontWeight.Medium),
    Font(R.font.ibm_plex_sans_semibold, FontWeight.SemiBold),
    Font(R.font.ibm_plex_sans_bold, FontWeight.Bold),
)
private val PLEX_MONO = FontFamily(Font(R.font.ibm_plex_mono_regular, FontWeight.Normal))

class MainActivity : ComponentActivity() {
    private var estado: Estado? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(primary = TINTA, background = PAPEL, surface = BLANCO)) {
                var cargado by remember { mutableStateOf<Estado?>(null) }
                LaunchedEffect(Unit) {
                    val modelos = withContext(Dispatchers.Default) { Modelos.cargar(applicationContext) }
                    // versión de desarrollo: --ez poseGpu / manosCpu / secuencial true cambian dónde corre MediaPipe (para medir)
                    val depuracion = applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE != 0
                    val aceleracion = if (!depuracion) Aceleracion() else Aceleracion(
                        gpuPose = intent.getBooleanExtra("poseGpu", false),
                        gpuManos = !intent.getBooleanExtra("manosCpu", false),
                        paralelo = !intent.getBooleanExtra("secuencial", false))
                    cargado = Estado(this@MainActivity, modelos, aceleracion).also { estado = it }
                    // modo de prueba: después de crear los detectores de la app (MediaPipe no tolera crear dos a la vez)
                    if (depuracion && intent.getBooleanExtra("prueba", false)) Prueba.ejecutar(applicationContext, modelos, aceleracion)
                }
                val e = cargado
                if (e == null) PantallaDeCarga() else App(e, this)
            }
        }
    }

    override fun onStop() {
        super.onStop()
        estado?.detener()  // guarda la sesión al salir de la app
    }

    override fun onDestroy() {
        estado?.cerrar()
        super.onDestroy()
    }
}

@Composable
private fun T(texto: String, tam: TextUnit = 14.sp, color: Color = TINTA, peso: FontWeight = FontWeight.Normal,
              modifier: Modifier = Modifier, alinear: TextAlign? = null, subrayado: Boolean = false,
              familia: FontFamily = PLEX, maxLineas: Int = Int.MAX_VALUE, espaciado: TextUnit = TextUnit.Unspecified) =
    Text(texto, modifier, color = color, fontSize = tam, fontWeight = peso, fontFamily = familia, textAlign = alinear,
        textDecoration = if (subrayado) TextDecoration.Underline else null, maxLines = maxLineas,
        overflow = TextOverflow.Ellipsis, letterSpacing = espaciado)

@Composable
private fun PantallaDeCarga() {
    Column(Modifier.fillMaxSize().background(PAPEL), verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Image(painterResource(R.drawable.silva_marca), null, Modifier.height(54.dp))
            Spacer(Modifier.width(14.dp))
            T("SILVA", 34.sp, peso = FontWeight.Bold, espaciado = 3.sp)
        }
        Spacer(Modifier.height(12.dp))
        T("Traductor de Lengua de Señas Colombiana", 14.sp, GRAFITO)
        T("Cargando modelos…", 13.sp, APAGADO, modifier = Modifier.padding(top = 6.dp))
    }
}

/** Línea divisoria abajo (o arriba) de un elemento, como los bordes de la propuesta. */
private fun Modifier.borde(arriba: Boolean = false, color: Color = LINEA) = drawBehind {
    val y = if (arriba) 0f else size.height
    drawLine(color, Offset(0f, y), Offset(size.width, y), 1.dp.toPx())
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun App(e: Estado, actividad: ComponentActivity) {
    // con el teclado abierto se oculta la navegación de abajo, para que se vea lo que se escribe
    val teclado = WindowInsets.isImeVisible
    var verLista by remember { mutableStateOf(false) }
    var verVocabulario by remember { mutableStateOf(false) }
    var verSena by remember { mutableStateOf<List<String>?>(null) }
    var verLetra by remember { mutableStateOf<String?>(null) }
    fun tiene(p: String) = ContextCompat.checkSelfPermission(actividad, p) == PackageManager.PERMISSION_GRANTED
    val permisoCamara = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        if (ok) e.iniciar(actividad) else e.error = "SILVA necesita la cámara para reconocer las señas."
    }
    val permisoMicrofono = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        if (ok) e.hablar(paraSenas = e.pantalla == Pantalla.TEXTO_A_SENAS) else e.error = "Para «Hablar», SILVA necesita el micrófono."
    }
    val hablar = { paraSenas: Boolean ->
        if (tiene(Manifest.permission.RECORD_AUDIO)) e.hablar(paraSenas)
        else permisoMicrofono.launch(Manifest.permission.RECORD_AUDIO)
    }
    val alternar = {
        if (e.activo) e.detener()
        else if (tiene(Manifest.permission.CAMERA)) e.iniciar(actividad)
        else permisoCamara.launch(Manifest.permission.CAMERA)
    }

    val completa = e.maximizado && e.pantalla == Pantalla.TRADUCIR
    BackHandler(enabled = completa) { e.maximizado = false }
    LaunchedEffect(completa) {
        val barras = WindowCompat.getInsetsController(actividad.window, actividad.window.decorView)
        if (completa) {
            barras.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            barras.hide(WindowInsetsCompat.Type.systemBars())
        } else barras.show(WindowInsetsCompat.Type.systemBars())
    }

    Column(Modifier.fillMaxSize().background(if (completa) TINTA else PAPEL).windowInsetsPadding(WindowInsets.safeDrawing)) {
        Box(Modifier.weight(1f).fillMaxWidth()) {
            when (e.pantalla) {
                Pantalla.TRADUCIR -> if (completa) PantallaMaximizada(e, actividad, alternar) { verLista = true }
                    else PantallaTraducir(e, actividad, alternar) { verLista = true }
                Pantalla.TEXTO_A_SENAS -> PantallaTextoASenas(e, hablar = { hablar(true) }) { verVocabulario = true }
                Pantalla.CONVERSAR -> PantallaConversar(e,
                    hablar = { hablar(false) },
                    senar = {
                        val ok = tiene(Manifest.permission.CAMERA)
                        e.senar(actividad, ok)
                        if (!ok) permisoCamara.launch(Manifest.permission.CAMERA)
                    },
                    verSenas = { verSena = it })
                Pantalla.HISTORIAL -> PantallaHistorial(e.historial)
                Pantalla.ENTRENAR -> PantallaEntrenar(e, actividad,
                    encender = {
                        if (tiene(Manifest.permission.CAMERA)) e.iniciar(actividad)
                        else permisoCamara.launch(Manifest.permission.CAMERA)
                    },
                    verGuia = { clave ->
                        if (e.modo == Modo.PALABRAS) verSena = listOf(e.nombreObjetivo(clave)) else verLetra = clave
                    })
            }
        }
        if (!teclado && !completa) BarraInferior(e.pantalla) { e.irA(it, actividad) }
    }

    if (verLista) DialogoDisponibles(e, e.modo == Modo.PALABRAS, { verLista = false }, { verLetra = it }) { verSena = listOf(it) }
    if (verVocabulario) DialogoDisponibles(e, true, { verVocabulario = false }, { verLetra = it }) { verSena = listOf(it) }
    verSena?.let { DialogoSena(it, e.modelos.animaciones) { verSena = null } }
    verLetra?.let { l -> e.modelos.guias?.let { DialogoLetra(l, it) { verLetra = null } } }
    e.error?.let { msg ->
        AlertDialog(onDismissRequest = { e.error = null }, containerColor = BLANCO,
            confirmButton = { TextButton({ e.error = null }) { T("Aceptar", color = AZUL, peso = FontWeight.Medium) } },
            title = { T("SILVA", 18.sp, peso = FontWeight.SemiBold) }, text = { T(msg, 14.sp, GRAFITO) })
    }
}

// ---------------------------------------------------------------------- barras
/** Cabecera de Traducir: la marca a la izquierda y las pestañas Deletreo / Palabras a la derecha. */
@Composable
private fun CabeceraTraducir(e: Estado) {
    Row(Modifier.fillMaxWidth().height(58.dp).padding(start = 20.dp, end = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        Image(painterResource(R.drawable.silva_marca), null, Modifier.height(22.dp))
        Spacer(Modifier.width(10.dp))
        T("SILVA", 17.sp, peso = FontWeight.Bold, espaciado = 2.sp)
        Spacer(Modifier.weight(1f))
        for ((m, nombre) in listOf(Modo.PALABRAS to "Palabras", Modo.LETRAS to "Deletreo")) {
            Pestana(nombre, e.modo == m) { e.cambiarModo(m) }
        }
    }
}

@Composable
private fun Pestana(texto: String, activa: Boolean, alPulsar: () -> Unit) {
    Box(Modifier.fillMaxHeight().clickable(onClick = alPulsar).padding(horizontal = 12.dp)
        .drawBehind { if (activa) drawRect(AZUL, Offset(0f, size.height - 3.dp.toPx()), Size(size.width, 3.dp.toPx())) },
        contentAlignment = Alignment.Center) {
        T(texto, 15.sp, if (activa) TINTA else GRAFITO, if (activa) FontWeight.SemiBold else FontWeight.Normal)
    }
}

@Composable
private fun BarraInferior(actual: Pantalla, alElegir: (Pantalla) -> Unit) {
    Row(Modifier.fillMaxWidth().height(60.dp).background(BLANCO).borde(arriba = true)) {
        for ((p, nombre) in listOf(Pantalla.TRADUCIR to "Señas a texto", Pantalla.TEXTO_A_SENAS to "Texto a señas",
                Pantalla.CONVERSAR to "Conversar", Pantalla.HISTORIAL to "Historial", Pantalla.ENTRENAR to "Entrenar")) {
            val activa = p == actual
            Box(Modifier.weight(1f).fillMaxHeight().clickable { alElegir(p) }
                .drawBehind { if (activa) drawRect(AZUL, Offset.Zero, Size(size.width, 3.dp.toPx())) },
                contentAlignment = Alignment.Center) {
                T(nombre, 13.sp, if (activa) TINTA else GRAFITO, if (activa) FontWeight.SemiBold else FontWeight.Normal,
                    alinear = TextAlign.Center, maxLineas = 2)
            }
        }
    }
}

// ---------------------------------------------------------------------- Traducir (propuesta, página 3)
/**
 * La cámara con sus capas: cambiar de cámara, pantalla completa, estado, avisos y la palabra por corregir.
 * La misma PantallaCamara (video y capas) se muestra en la pantalla normal y en la completa: al pasar de una a otra se
 * desprende de la anterior antes de agregarla a la nueva.
 */
@Composable
private fun CamaraConCapas(e: Estado, actividad: ComponentActivity, modifier: Modifier) {
    val completa = e.maximizado
    Box(modifier.clipToBounds().background(TINTA)) {
        AndroidView(factory = {
            (e.pantallaCamara.parent as? ViewGroup)?.removeView(e.pantallaCamara)
            e.pantallaCamara
        }, modifier = Modifier.fillMaxSize(), update = { it.rellenar = !completa })
        if (!e.activo) T("Presiona «Iniciar» para encender la cámara", 15.sp, APAGADO,
            alinear = TextAlign.Center, modifier = Modifier.align(Alignment.Center).padding(24.dp))
        Row(Modifier.align(Alignment.TopStart).padding(4.dp), verticalAlignment = Alignment.CenterVertically) {
            T(if (completa) "Reducir" else "Pantalla completa", 13.sp, PAPEL, FontWeight.Medium, subrayado = true,
                modifier = Modifier.clickable { e.maximizado = !completa }.padding(8.dp))
            T(if (e.frontal) "Cámara frontal" else "Cámara trasera", 13.sp, PAPEL, FontWeight.Medium, subrayado = true,
                modifier = Modifier.clickable { e.cambiarCamara(actividad) }.padding(8.dp))
        }
        // en su propia línea, bajo los enlaces: en un teléfono angosto no caben en la misma
        if (e.activo) Row(Modifier.align(Alignment.TopEnd).padding(top = 44.dp, end = 10.dp)
            .background(Color(0x9916181D), RoundedCornerShape(4.dp)).padding(horizontal = 8.dp, vertical = 3.dp),
            verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(7.dp).background(if (e.leyendo) OCRE else AZUL, RoundedCornerShape(50)))
            Spacer(Modifier.width(6.dp))
            T((if (e.leyendo) "leyendo seña" else "en vivo") + " · ${e.fps} fps", 12.sp, PAPEL, FontWeight.Medium)
            // dónde corre MediaPipe: «CPU» sola quiere decir que el teléfono no pudo usar la GPU (va más lento)
            if (e.aceleracion.isNotEmpty()) T(" · ${e.aceleracion}", 11.sp, APAGADO)
        }
        e.banda?.let { aviso ->
            Row(Modifier.align(if (e.pendiente != null) Alignment.TopStart else Alignment.BottomStart)
                .padding(start = 10.dp, end = 10.dp, top = if (e.pendiente != null) 72.dp else 10.dp, bottom = 10.dp)
                .background(Color(0xE616181D), RoundedCornerShape(4.dp))) {
                Box(Modifier.width(3.dp).heightIn(min = 34.dp).background(OCRE))
                T(aviso, 12.sp, PAPEL, modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp))
            }
        }
        e.pendiente?.let { p -> TarjetaPendiente(p.opciones.map { it.texto }, p.automatica, e.progresoPendiente,
            Modifier.align(Alignment.BottomCenter).padding(10.dp)) }
    }
}

/** Lo detectado: letra o palabra en grande, la barra de 5 segmentos y el estado. */
@Composable
private fun FranjaDeteccion(e: Estado, oscura: Boolean, verDisponibles: () -> Unit) {
    val palabras = e.modo == Modo.PALABRAS
    Row(Modifier.fillMaxWidth().background(if (oscura) TINTA else BLANCO).padding(horizontal = 18.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically) {
        T(e.detectado, if (palabras && e.detectado.length > 1) 22.sp else 40.sp,
            if (e.dudosa) (if (oscura) GRAFITO else APAGADO) else (if (oscura) PAPEL else TINTA),
            FontWeight.Bold, Modifier.widthIn(min = 36.dp, max = 160.dp), maxLineas = 1)
        Spacer(Modifier.width(16.dp))
        Column(Modifier.weight(1f)) {
            Segmentos(e.segmentos, if (e.segmentosAzules) AZUL else OCRE, if (oscura) Color(0xFF34373F) else LINEA)
            Spacer(Modifier.height(7.dp))
            val conf = e.confianza?.let { " · ${(it * 100).toInt()}%" } ?: ""
            Row(verticalAlignment = Alignment.CenterVertically) {
                T(e.estadoTexto + conf, 12.sp, if (oscura) APAGADO else GRAFITO, maxLineas = 1, modifier = Modifier.weight(1f))
                T(if (palabras) "Vocabulario" else "Abecedario", 12.sp, if (oscura) PAPEL else AZUL, subrayado = true,
                    modifier = Modifier.clickable(onClick = verDisponibles).padding(start = 8.dp))
            }
        }
    }
}

/** El texto traducido, con el cursor, y «¿Quisiste decir?» (sugerencias o la palabra por corregir). */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TextoTraducido(e: Estado, oscura: Boolean, tam: TextUnit, modifier: Modifier) {
    val palabras = e.modo == Modo.PALABRAS
    val principal = if (oscura) PAPEL else TINTA
    val secundario = if (oscura) APAGADO else GRAFITO
    val enlace = if (oscura) Color(0xFF9DB4F5) else AZUL  // en fondo tinta el azul de la marca no se lee bien
    Column(modifier.verticalScroll(rememberScrollState())) {
        if (e.texto.isEmpty()) {
            T(if (palabras) "Las palabras confirmadas aparecerán aquí." else "Las letras confirmadas aparecerán aquí.",
                15.sp, secundario, modifier = Modifier.padding(top = 6.dp))
        } else {
            Row(verticalAlignment = Alignment.CenterVertically) {
                T(e.texto, tam, principal, FontWeight.Medium, Modifier.weight(1f, fill = false))
                if (e.activo) Box(Modifier.padding(start = 2.dp).width(2.dp).height(tam.value.dp * 1.1f).background(AZUL))
            }
        }
        Spacer(Modifier.height(6.dp))
        val p = e.pendiente
        FlowRow(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            if (p != null) {
                T(if (p.automatica) "¿No era?" else "¿Quisiste decir?", 14.sp, secundario)
                p.opciones.forEachIndexed { i, o ->
                    if (!p.automatica || i > 0) T(o.texto.uppercase(), 15.sp, enlace, subrayado = true,
                        modifier = Modifier.clickable { e.elegir(i) })
                }
                T(if (p.automatica) "Borrar" else "Descartar", 14.sp, secundario, modifier = Modifier.clickable { e.descartar() })
            } else {
                for (s in e.sugerencias) T(s, 15.sp, enlace, subrayado = true, modifier = Modifier.clickable { e.completar(s) })
            }
        }
    }
}

@Composable
private fun BotonesTraducir(e: Estado, alternar: () -> Unit, oscura: Boolean, modifier: Modifier) {
    val palabras = e.modo == Modo.PALABRAS
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        BotonClaro("Borrar", Modifier.weight(1f), e.texto.isNotEmpty()) { e.borrar() }
        if (oscura) Button(alternar, Modifier.weight(1f).height(54.dp), shape = RoundedCornerShape(8.dp),
            colors = ButtonDefaults.buttonColors(containerColor = AZUL, contentColor = BLANCO)) {
            T(if (e.activo) "Detener" else "Iniciar", 16.sp, BLANCO, FontWeight.SemiBold, maxLineas = 1)
        } else BotonTinta(if (e.activo) "Detener" else "Iniciar", Modifier.weight(1f), alternar)
        if (palabras) BotonClaro("Limpiar", Modifier.weight(1f), e.texto.isNotEmpty()) { e.limpiar() }
        else BotonClaro("Espacio", Modifier.weight(1f), e.texto.isNotEmpty()) { e.espacio() }
    }
}

@Composable
private fun PantallaTraducir(e: Estado, actividad: ComponentActivity, alternar: () -> Unit, verDisponibles: () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        CabeceraTraducir(e)
        Column(Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp)) {
            Column(Modifier.weight(1f).fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(BLANCO)) {
                CamaraConCapas(e, actividad, Modifier.weight(1f).fillMaxWidth())
                FranjaDeteccion(e, oscura = false, verDisponibles)
            }
            Row(Modifier.padding(top = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                T("Texto", 14.sp, GRAFITO, FontWeight.SemiBold)
                Spacer(Modifier.weight(1f))
                T("Escuchar", 15.sp, if (e.texto.isBlank()) APAGADO else AZUL,
                    modifier = Modifier.clickable(enabled = e.texto.isNotBlank()) { e.escuchar() }.padding(6.dp))
                Spacer(Modifier.width(12.dp))
                T("Copiar", 15.sp, if (e.texto.isBlank()) APAGADO else AZUL,
                    modifier = Modifier.clickable(enabled = e.texto.isNotBlank()) { e.copiar() }.padding(6.dp))
            }
            TextoTraducido(e, oscura = false, 30.sp, Modifier.fillMaxWidth().heightIn(min = 80.dp, max = 140.dp))
            BotonesTraducir(e, alternar, oscura = false, Modifier.padding(top = 10.dp, bottom = 14.dp))
        }
    }
}

/**
 * Pantalla completa: la cámara ocupa todo lo posible (sin barras del sistema) y debajo, sobre tinta, se ve
 * lo que se va traduciendo en grande. «Reducir» o el botón Atrás vuelven a la pantalla normal.
 */
@Composable
private fun PantallaMaximizada(e: Estado, actividad: ComponentActivity, alternar: () -> Unit, verDisponibles: () -> Unit) {
    Column(Modifier.fillMaxSize().background(TINTA)) {
        CamaraConCapas(e, actividad, Modifier.weight(1f).fillMaxWidth())
        FranjaDeteccion(e, oscura = true, verDisponibles)
        Box(Modifier.fillMaxWidth().height(1.dp).background(Color(0xFF2A2D35)))
        TextoTraducido(e, oscura = true, 34.sp, Modifier.fillMaxWidth().heightIn(min = 70.dp, max = 170.dp)
            .padding(horizontal = 18.dp, vertical = 10.dp))
        BotonesTraducir(e, alternar, oscura = true, Modifier.padding(start = 16.dp, end = 16.dp, bottom = 14.dp))
    }
}

@Composable
private fun Segmentos(llenos: Int, color: Color, vacio: Color = LINEA) {
    Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
        repeat(5) { i -> Box(Modifier.weight(1f).height(5.dp).background(if (i < llenos) color else vacio)) }
    }
}

@Composable
private fun BotonTinta(texto: String, modifier: Modifier, alPulsar: () -> Unit) =
    Button(alPulsar, modifier.height(54.dp), shape = RoundedCornerShape(8.dp),
        colors = ButtonDefaults.buttonColors(containerColor = TINTA, contentColor = BLANCO)) {
        T(texto, 16.sp, BLANCO, FontWeight.SemiBold, maxLineas = 1)
    }

@Composable
private fun BotonClaro(texto: String, modifier: Modifier, habilitado: Boolean = true, alPulsar: () -> Unit) =
    OutlinedButton(alPulsar, modifier.height(54.dp), enabled = habilitado, shape = RoundedCornerShape(8.dp),
        border = BorderStroke(1.dp, if (habilitado) BORDE_BOTON else LINEA),
        colors = ButtonDefaults.outlinedButtonColors(containerColor = BLANCO)) {
        T(texto, 16.sp, if (habilitado) TINTA else APAGADO, maxLineas = 1)
    }

/** Palabra escrita (con sus alternativas) o «¿Quisiste decir?», en grande sobre el video. */
@Composable
private fun TarjetaPendiente(opciones: List<String>, escrita: Boolean, progreso: Double, modifier: Modifier) {
    val color = if (escrita) AZUL else OCRE
    Column(modifier.fillMaxWidth().background(BLANCO, RoundedCornerShape(6.dp)).border(1.dp, LINEA, RoundedCornerShape(6.dp))) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 8.dp)) {
            T(if (escrita) "ESCRITA" else "¿QUISISTE DECIR?", 10.sp, color, FontWeight.SemiBold)
            T(if (escrita) opciones[0].uppercase() else opciones.mapIndexed { i, o -> "${i + 1} $o" }.joinToString("   "),
                if (escrita) 22.sp else 15.sp, peso = if (escrita) FontWeight.Bold else FontWeight.Medium,
                alinear = TextAlign.Center, modifier = Modifier.fillMaxWidth(), maxLineas = 2)
        }
        Box(Modifier.fillMaxWidth(progreso.toFloat()).height(3.dp).background(color))
    }
}

// ---------------------------------------------------------------------- Texto a señas
/**
 * El sentido contrario a la cámara: la persona oyente escribe o dicta, y el texto se muestra en grande
 * con las señas animadas de las palabras conocidas (como «Responder» en la app de PC).
 */
@Composable
private fun PantallaTextoASenas(e: Estado, hablar: () -> Unit, verVocabulario: () -> Unit) {
    var texto by remember { mutableStateOf("") }
    fun mostrar() {
        e.mostrarEnSenas(texto)
        texto = ""
    }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().height(58.dp).borde().padding(start = 20.dp, end = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            T("Texto a señas", 20.sp, peso = FontWeight.SemiBold)
            Spacer(Modifier.weight(1f))
            TextButton(verVocabulario) { T("Vocabulario", 15.sp, AZUL) }
        }
        val mostrado = e.mostrado
        Column(Modifier.weight(1f).fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (mostrado == null) {
                T("Escribe o di una frase: se mostrará en grande y, si tiene palabras del vocabulario " +
                    "(hola, gracias, por favor, ayudar…), también en señas animadas.", 16.sp, GRAFITO)
            } else {
                T(mostrado, if (mostrado.length < 40) 30.sp else 22.sp, peso = FontWeight.Medium,
                    modifier = Modifier.heightIn(max = 150.dp).verticalScroll(rememberScrollState()))
                if (e.senasMostradas.isNotEmpty()) {
                    AnimacionSena(e.modelos.animaciones, e.senasMostradas, Modifier.weight(1f).fillMaxWidth())
                } else {
                    T("Ninguna palabra de esta frase tiene seña en el vocabulario: se muestra solo el texto.", 14.sp, GRAFITO)
                }
            }
            e.escuchando?.let { T(if (it.isEmpty()) "Escuchando…" else it, 18.sp, GRAFITO) }
        }
        Column(Modifier.fillMaxWidth().background(BLANCO).borde(arriba = true).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)) {
            T("Escribe o dicta lo que quieres decir", 13.sp, GRAFITO)
            OutlinedTextField(texto, { nuevo -> if (nuevo.endsWith("\n")) { texto = nuevo; mostrar() } else texto = nuevo },
                Modifier.fillMaxWidth().heightIn(min = 52.dp, max = 120.dp),
                placeholder = { T("Escribe aquí", 16.sp, APAGADO) },
                textStyle = TextStyle(fontFamily = PLEX, fontSize = 17.sp, color = TINTA),
                shape = RoundedCornerShape(6.dp),
                colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = BORDE_BOTON, focusedBorderColor = AZUL,
                    unfocusedContainerColor = PAPEL, focusedContainerColor = BLANCO, cursorColor = AZUL),
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences, imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { mostrar() }))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                BotonClaro(if (e.escuchando != null) "Escuchando…" else "Hablar", Modifier.weight(1f), alPulsar = hablar)
                BotonTinta("Ver en señas", Modifier.weight(1f)) { mostrar() }
            }
        }
    }
}

// ---------------------------------------------------------------------- Conversar (propuesta, página 4)
@Composable
private fun PantallaConversar(e: Estado, hablar: () -> Unit, senar: () -> Unit, verSenas: (List<String>) -> Unit) {
    var respuesta by remember { mutableStateOf("") }
    val lista = rememberLazyListState()
    LaunchedEffect(e.mensajes.size, e.escuchando) {
        val total = e.mensajes.size + if (e.escuchando != null) 1 else 0
        if (total > 0) lista.animateScrollToItem(total - 1)
    }
    val grande = e.textoGrande
    fun enviar() {
        e.responderPorEscrito(respuesta)
        respuesta = ""
    }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().height(58.dp).borde().padding(start = 20.dp, end = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            T("Conversación", 20.sp, peso = FontWeight.SemiBold)
            Spacer(Modifier.weight(1f))
            TextButton({ e.textoGrande = !e.textoGrande }) { T(if (grande) "Texto normal" else "Texto grande", 15.sp, AZUL) }
        }
        if (e.mensajes.isEmpty() && e.escuchando == null) {
            T("Aquí aparece la conversación: lo que se seña en Traducir y lo que responde la persona oyente, " +
                "por escrito o con la voz.", 15.sp, GRAFITO, modifier = Modifier.padding(20.dp))
        }
        LazyColumn(Modifier.weight(1f).fillMaxWidth().padding(horizontal = 20.dp), state = lista) {
            items(e.mensajes) { m ->
                Column(Modifier.fillMaxWidth().borde().padding(vertical = 14.dp)) {
                    T("${m.origen.rotulo} · ${m.hora}", 12.sp, if (m.origen == Origen.SENAS) AZUL else GRAFITO, FontWeight.SemiBold)
                    Spacer(Modifier.height(4.dp))
                    T(m.texto, if (grande) 32.sp else 21.sp,
                        peso = if (m.origen == Origen.SENAS) FontWeight.SemiBold else FontWeight.Normal)
                    if (m.senas.isNotEmpty()) T("Ver en señas: ${m.senas.joinToString(" · ")}", 13.sp, AZUL, subrayado = true,
                        modifier = Modifier.padding(top = 4.dp).clickable { verSenas(m.senas) })
                }
            }
            e.escuchando?.let { parcial ->
                item {
                    Column(Modifier.fillMaxWidth().padding(vertical = 14.dp)) {
                        T("VOZ · escuchando", 12.sp, GRAFITO, FontWeight.SemiBold)
                        Spacer(Modifier.height(4.dp))
                        T(parcial.ifEmpty { "…" }, if (grande) 32.sp else 21.sp, GRAFITO)
                    }
                }
            }
        }
        Column(Modifier.fillMaxWidth().background(BLANCO).borde(arriba = true).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)) {
            T("Responder por escrito", 13.sp, GRAFITO)
            // Enter (teclado físico) también envía, igual que la tecla de envío del teclado en pantalla
            OutlinedTextField(respuesta, { nuevo -> if (nuevo.endsWith("\n")) { respuesta = nuevo; enviar() } else respuesta = nuevo },
                Modifier.fillMaxWidth().heightIn(min = 52.dp, max = 140.dp),
                placeholder = { T("Escribe aquí", 16.sp, APAGADO) },
                textStyle = TextStyle(fontFamily = PLEX, fontSize = 17.sp, color = TINTA),
                shape = RoundedCornerShape(6.dp),
                colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = BORDE_BOTON, focusedBorderColor = AZUL,
                    unfocusedContainerColor = PAPEL, focusedContainerColor = BLANCO, cursorColor = AZUL),
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences, imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { enviar() }))
            if (respuesta.isNotBlank()) {
                val senas = e.modelos.animaciones.buscar(respuesta)
                if (senas.isNotEmpty()) T("Se podrá ver en señas: ${senas.joinToString(" · ")}", 12.sp, GRAFITO)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                BotonClaro(if (e.escuchando != null) "Escuchando…" else "Hablar", Modifier.weight(1f), alPulsar = hablar)
                BotonTinta("Señar", Modifier.weight(1f), senar)
            }
        }
    }
}

// ---------------------------------------------------------------------- Historial
@Composable
private fun PantallaHistorial(historial: Historial) {
    val sesiones = remember { historial.sesiones() }
    val respuestas = remember { historial.respuestas() }
    var pestana by remember { mutableIntStateOf(0) }
    Column(Modifier.fillMaxSize().padding(horizontal = 20.dp)) {
        T("Historial", 20.sp, peso = FontWeight.SemiBold, modifier = Modifier.padding(top = 16.dp, bottom = 4.dp))
        Row(Modifier.height(46.dp)) {
            Pestana("Sesiones (${sesiones.size})", pestana == 0) { pestana = 0 }
            Pestana("Respuestas (${respuestas.size})", pestana == 1) { pestana = 1 }
        }
        val filas = if (pestana == 0) sesiones.map { it.inicio to it.texto } else respuestas.map { it.hora to it.texto }
        if (filas.isEmpty()) T("Todavía no hay nada guardado.", 15.sp, GRAFITO, modifier = Modifier.padding(top = 12.dp))
        LazyColumn(Modifier.fillMaxSize()) {
            items(filas) { (hora, t) ->
                Column(Modifier.fillMaxWidth().borde().padding(vertical = 10.dp)) {
                    T(hora, 11.sp, GRAFITO, familia = PLEX_MONO)
                    T(t, 17.sp)
                }
            }
        }
    }
}

// ---------------------------------------------------------------------- Entrenar
/**
 * Grabar muestras propias (solo los puntos de cuerpo y manos) para reentrenar los modelos en el PC con
 * scripts/entrenar_con_muestras.py, e importar el modelo que resulta.
 */
@Composable
private fun PantallaEntrenar(e: Estado, actividad: ComponentActivity, encender: () -> Unit, verGuia: (String) -> Unit) {
    val palabras = e.modo == Modo.PALABRAS
    val claves = if (palabras) e.modelos.palabras.claves.sortedBy { e.modelos.palabras.nombre(it) } else LETRAS
    var verOpciones by remember { mutableStateOf(false) }
    var ocupado by remember { mutableStateOf<String?>(null) }
    val alcance = rememberCoroutineScope()
    fun exportar(compartir: Boolean) {
        ocupado = "Preparando el archivo…"
        alcance.launch {
            val (archivo, guardado) = withContext(Dispatchers.IO) {
                val f = e.muestras.exportar()
                f to (if (compartir) null else e.muestras.guardarEnDescargas(f))
            }
            ocupado = null
            if (compartir || guardado == null) actividad.startActivity(e.muestras.compartir(archivo))
            else e.error = "Listo: ${e.totalMuestras} muestras en $guardado. Pásalo al PC (por cable o por Drive) y ejecuta " +
                "scripts/entrenar_con_muestras.py con ese archivo."
        }
    }

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().height(58.dp).padding(start = 20.dp, end = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            T("Entrenar", 20.sp, peso = FontWeight.SemiBold)
            Spacer(Modifier.weight(1f))
            for ((m, nombre) in listOf(Modo.PALABRAS to "Palabras", Modo.LETRAS to "Deletreo")) {
                Pestana(nombre, e.modo == m) { e.cambiarModoEntrenar(m) }
            }
        }
        Column(Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp)) {
            OutlinedTextField(e.persona, { e.ponerPersona(it) }, Modifier.fillMaxWidth().heightIn(min = 52.dp),
                singleLine = true, label = { T("¿Quién graba? (nombre o apodo)", 13.sp, GRAFITO) },
                textStyle = TextStyle(fontFamily = PLEX, fontSize = 16.sp, color = TINTA), shape = RoundedCornerShape(6.dp),
                colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = BORDE_BOTON, focusedBorderColor = AZUL,
                    unfocusedContainerColor = BLANCO, focusedContainerColor = BLANCO, cursorColor = AZUL),
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words, imeAction = ImeAction.Done))
            Spacer(Modifier.height(10.dp))
            Box(Modifier.weight(1f).fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(TINTA)) {
                AndroidView(factory = {
                    (e.pantallaCamara.parent as? ViewGroup)?.removeView(e.pantallaCamara)
                    e.pantallaCamara
                }, modifier = Modifier.fillMaxSize(), update = { it.rellenar = true })
                if (!e.activo) T("La cámara se enciende al tocar «Grabar».", 15.sp, APAGADO, alinear = TextAlign.Center,
                    modifier = Modifier.align(Alignment.Center).padding(24.dp))
                T(if (e.frontal) "Cámara frontal" else "Cámara trasera", 13.sp, PAPEL, FontWeight.Medium, subrayado = true,
                    modifier = Modifier.align(Alignment.TopStart).clickable { e.cambiarCamara(actividad) }.padding(12.dp))
                if (e.activo) Row(Modifier.align(Alignment.TopEnd).padding(10.dp)
                    .background(Color(0x9916181D), RoundedCornerShape(4.dp)).padding(horizontal = 8.dp, vertical = 3.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(7.dp).background(if (e.grabandoMuestras) Color(0xFFD93025) else AZUL, RoundedCornerShape(50)))
                    Spacer(Modifier.width(6.dp))
                    T((if (e.grabandoMuestras) "grabando" else "en vivo") + " · ${e.fps} fps", 12.sp, PAPEL, FontWeight.Medium)
                }
                Column(Modifier.align(Alignment.BottomStart).fillMaxWidth().padding(10.dp)) {
                    e.banda?.let { aviso ->
                        T(aviso, 12.sp, PAPEL, modifier = Modifier.background(Color(0xE616181D), RoundedCornerShape(4.dp))
                            .padding(horizontal = 10.dp, vertical = 6.dp))
                        Spacer(Modifier.height(6.dp))
                    }
                    if (e.activo) Row(Modifier.background(Color(0xE616181D), RoundedCornerShape(4.dp))
                        .padding(horizontal = 10.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                        T("El modelo ve: ", 12.sp, APAGADO)
                        T(e.detectado, 14.sp, PAPEL, FontWeight.SemiBold)
                        e.confianza?.let { T(" · ${(it * 100).toInt()} %", 12.sp, APAGADO) }
                    }
                    if (e.grabandoMuestras && e.objetivo?.let { e.tipoMuestra(it) } == TipoMuestra.LETRA) {
                        Spacer(Modifier.height(6.dp))
                        Box(Modifier.fillMaxWidth().height(6.dp).background(Color(0xFF34373F))) {
                            Box(Modifier.fillMaxWidth(e.progresoToma.coerceIn(0f, 1f)).height(6.dp).background(OCRE))
                        }
                    }
                }
            }
            Spacer(Modifier.height(10.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(claves) { clave ->
                    val elegida = clave == e.objetivo
                    val n = e.cuantas(clave)
                    val trazo = !palabras && clave !in LETRAS_ESTATICAS
                    Row(Modifier.clip(RoundedCornerShape(18.dp)).background(if (elegida) AZUL else BLANCO)
                        .border(1.dp, if (elegida) AZUL else BORDE_BOTON, RoundedCornerShape(18.dp))
                        .clickable { e.elegirObjetivo(clave) }.padding(horizontal = 14.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        T(e.nombreObjetivo(clave) + if (trazo) " ↝" else "", 15.sp, if (elegida) BLANCO else TINTA, FontWeight.Medium)
                        if (n > 0) T("  $n", 13.sp, if (elegida) Color(0xFFC9D6FA) else AZUL, FontWeight.SemiBold)
                    }
                }
            }
            Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.Top) {
                T(ocupado ?: e.avisoEntrenar.ifEmpty { if (palabras) "Elige una palabra para grabarla." else "Elige una letra para grabarla." },
                    14.sp, GRAFITO, modifier = Modifier.weight(1f).heightIn(min = 40.dp), maxLineas = 3)
                val objetivo = e.objetivo
                val hayGuia = objetivo != null && (if (palabras) e.nombreObjetivo(objetivo) in e.modelos.animaciones.nombres
                    else e.modelos.guias?.letras?.contains(objetivo) == true)
                if (hayGuia) T("Ver cómo\nse hace", 14.sp, AZUL, subrayado = true, alinear = TextAlign.End,
                    modifier = Modifier.clickable { verGuia(objetivo!!) }.padding(start = 10.dp))
            }
            Row(Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                BotonClaro("Borrar última", Modifier.weight(1f), e.totalMuestras > 0 && !e.grabandoMuestras) { e.borrarUltimaMuestra() }
                BotonTinta(if (e.grabandoMuestras) "Detener" else "Grabar", Modifier.weight(1f)) {
                    if (e.alternarGrabacion() && e.grabandoMuestras && !e.activo) encender()
                }
            }
            Row(Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                T("${e.totalMuestras} muestras", 13.sp, GRAFITO)
                Spacer(Modifier.weight(1f))
                val hay = e.totalMuestras > 0 && ocupado == null
                T("Exportar", 15.sp, if (hay) AZUL else APAGADO,
                    modifier = Modifier.clickable(enabled = hay) { exportar(false) }.padding(8.dp))
                T("Compartir", 15.sp, if (hay) AZUL else APAGADO,
                    modifier = Modifier.clickable(enabled = hay) { exportar(true) }.padding(8.dp))
                T("Más…", 15.sp, AZUL, modifier = Modifier.clickable { verOpciones = true }.padding(8.dp))
            }
        }
    }
    if (verOpciones) DialogoEntrenar(e, actividad) { verOpciones = false }
}

/** Cómo se usan las muestras, importar el modelo entrenado en el PC y borrar las muestras. */
@Composable
private fun DialogoEntrenar(e: Estado, actividad: ComponentActivity, alCerrar: () -> Unit) {
    var confirmarBorrado by remember { mutableStateOf(false) }
    var importando by remember { mutableStateOf(false) }
    val alcance = rememberCoroutineScope()
    val importar = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        importando = true
        alcance.launch {
            val falla = withContext(Dispatchers.IO) { Muestras.importarModelo(actividad, uri) }
            importando = false
            if (falla != null) e.error = falla else actividad.recreate()  // se vuelve a abrir con el modelo nuevo
        }
    }
    Dialog(onDismissRequest = alCerrar) {
        Column(Modifier.widthIn(max = 560.dp).background(BLANCO, RoundedCornerShape(8.dp)).padding(20.dp)
            .verticalScroll(rememberScrollState())) {
            T("Entrenar el modelo con sus señas", 17.sp, peso = FontWeight.SemiBold)
            Spacer(Modifier.height(10.dp))
            T("1. Graben cada seña unas 5 veces por persona; mejor varias personas y lugares, con el teléfono como lo " +
                "van a usar. Solo se guardan los puntos del cuerpo y las manos, nunca la imagen.\n" +
                "2. «Exportar» deja el archivo en Descargas/SILVA. Pásalo al PC.\n" +
                "3. En el PC, en la carpeta de SILVA:\n    python scripts/entrenar_con_muestras.py <archivo>\n" +
                "   Reentrena los tres modelos, mide si mejoran y crea dist/silva_modelo_<fecha>.zip.\n" +
                "4. Pasa ese .zip al teléfono e impórtalo aquí.", 14.sp, GRAFITO)
            Spacer(Modifier.height(14.dp))
            T("Modelo en uso: " + (e.modelos.origen ?: "el original de SILVA"), 14.sp, TINTA, FontWeight.Medium)
            Spacer(Modifier.height(8.dp))
            BotonTinta(if (importando) "Importando…" else "Importar modelo (.zip)", Modifier.fillMaxWidth()) {
                if (!importando) importar.launch(arrayOf("application/zip", "application/x-zip-compressed", "application/octet-stream"))
            }
            if (e.modelos.origen != null) {
                Spacer(Modifier.height(8.dp))
                BotonClaro("Volver al modelo original", Modifier.fillMaxWidth()) {
                    Muestras.quitarModeloPropio(actividad)
                    actividad.recreate()
                }
            }
            Spacer(Modifier.height(8.dp))
            BotonClaro(if (confirmarBorrado) "Toca otra vez para borrar ${e.totalMuestras} muestras" else "Borrar todas las muestras",
                Modifier.fillMaxWidth(), e.totalMuestras > 0) {
                if (confirmarBorrado) {
                    e.borrarTodasLasMuestras()
                    confirmarBorrado = false
                } else confirmarBorrado = true
            }
            TextButton(alCerrar, Modifier.align(Alignment.End)) { T("Cerrar", 15.sp, AZUL, FontWeight.Medium) }
        }
    }
}

// ---------------------------------------------------------------------- diálogos
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DialogoDisponibles(e: Estado, palabras: Boolean, alCerrar: () -> Unit, alVerLetra: (String) -> Unit,
                               alVerSena: (String) -> Unit) {
    Dialog(onDismissRequest = alCerrar) {
        Column(Modifier.widthIn(max = 560.dp).background(BLANCO, RoundedCornerShape(8.dp)).padding(20.dp)) {
            Row {
                T(if (palabras) "Vocabulario" else "Abecedario", 17.sp, peso = FontWeight.SemiBold)
                Spacer(Modifier.weight(1f))
                T(if (palabras) "${e.modelos.palabras.palabras.size} palabras" else "${e.motor.letras.size} de ${LETRAS.size}",
                    13.sp, GRAFITO)
            }
            Spacer(Modifier.height(12.dp))
            FlowRow(horizontalArrangement = Arrangement.spacedBy(if (palabras) 14.dp else 18.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)) {
                if (palabras) {
                    for (w in e.modelos.palabras.palabras.sorted()) {
                        val con = w in e.modelos.animaciones.nombres
                        T(w, 15.sp, if (con) AZUL else TINTA, subrayado = con,
                            modifier = if (con) Modifier.clickable { alVerSena(w) } else Modifier)
                    }
                } else {
                    val guias = e.modelos.guias
                    for (l in LETRAS) {
                        val con = guias != null && l in guias.letras
                        T(l, 19.sp, if (con) AZUL else if (l in e.motor.letras) TINTA else APAGADO, FontWeight.Medium,
                            subrayado = con, modifier = if (con) Modifier.clickable { alVerLetra(l) }.padding(2.dp) else Modifier)
                    }
                }
            }
            Spacer(Modifier.height(12.dp))
            T(if (palabras) "Empieza con las manos abajo, haz la seña y vuelve a bajarlas. Toca una palabra para ver su seña."
                else "Toca una letra para ver cómo se hace. ${LETRAS_MOVIMIENTO.dropLast(1).joinToString(", ")} y ${LETRAS_MOVIMIENTO.last()} se trazan: " +
                    "haz el movimiento y quédate quieto al final.", 13.sp, GRAFITO)
            TextButton(alCerrar, Modifier.align(Alignment.End)) { T("Cerrar", 15.sp, AZUL, FontWeight.Medium) }
        }
    }
}

// Figura animada: una persona de frente con camisa, mangas y manos con dedos (sin puntos ni vértices)
private val PIEL = Color(0xFFD9A27F)
private val PIEL_BORDE = Color(0xFFB4795A)
private val MANGA = Color(0xFF3A66E6)
private val MANGA_BORDE = Color(0xFF15379A)
private val DEDOS = listOf(listOf(1, 2, 3, 4), listOf(5, 6, 7, 8), listOf(9, 10, 11, 12), listOf(13, 14, 15, 16), listOf(17, 18, 19, 20))

/** Como silva.animacion.dibujar_persona. f = 100 valores (en anchos de hombro); p = de esas unidades a la pantalla. */
private fun DrawScope.dibujarPersona(f: FloatArray, p: (Float, Float) -> Offset) {
    val escala = (p(1f, 0f) - p(0f, 0f)).x
    fun pose(i: Int) = p(f[2 * i], f[2 * i + 1])  // 0 nariz, 1-2 hombros, 3-4 codos, 5-6 muñecas
    fun trazo(ancho: Float) = Stroke(ancho, cap = StrokeCap.Round, join = StrokeJoin.Round)
    fun linea(puntos: List<Offset>) = Path().apply { moveTo(puntos[0].x, puntos[0].y); puntos.drop(1).forEach { lineTo(it.x, it.y) } }
    // camisa y cuello
    val torso = linea(listOf(pose(1), pose(2), p(f[4] * 0.85f, 2.2f), p(f[2] * 0.85f, 2.2f))).apply { close() }
    drawPath(torso, AZUL)
    drawPath(torso, AZUL, style = trazo(escala * 0.2f))
    drawLine(PIEL, p(f[0], -0.05f), p(f[0], f[1] + 0.1f), escala * 0.2f, StrokeCap.Round)
    // cabeza: cara, pelo y ojos
    val c = p(f[0], f[1] - 0.05f)
    val rx = 0.27f * escala
    val ry = 0.33f * escala
    drawOval(PIEL, Offset(c.x - rx, c.y - ry), Size(2 * rx, 2 * ry))
    drawArc(TINTA, 200f, 140f, false, Offset(c.x - rx - 0.02f * escala, c.y - ry - 0.03f * escala),
        Size(2 * rx + 0.04f * escala, 2 * ry + 0.03f * escala))
    for (dx in listOf(-0.1f, 0.1f)) drawOval(TINTA, p(f[0] + dx - 0.025f, f[1] - 0.04f - 0.03f), Size(0.05f * escala, 0.06f * escala))
    // brazos con manga larga: el antebrazo llega a la muñeca de la mano si se ve
    for ((articulaciones, inicio) in listOf(Triple(1, 3, 5) to N_POSE, Triple(2, 4, 6) to N_POSE + N_MANO)) {
        val (hombro, codo, muneca) = articulaciones
        val fin = if (f[inicio + 42] > 0f) p(f[inicio], f[inicio + 1]) else pose(muneca)
        val brazo = linea(listOf(pose(hombro), pose(codo), fin))
        drawPath(brazo, MANGA_BORDE, style = trazo(escala * 0.27f))
        drawPath(brazo, MANGA, style = trazo(escala * 0.22f))
    }
    // manos: palma y dedos con contorno
    for ((inicio, muneca) in listOf(N_POSE to 5, N_POSE + N_MANO to 6)) {
        if (f[inicio + 42] <= 0f) {  // sin mano en este cuadro: un puño en la muñeca
            drawCircle(PIEL, 0.09f * escala, pose(muneca))
            drawCircle(PIEL_BORDE, 0.09f * escala, pose(muneca), style = Stroke(maxOf(escala * 0.012f, 1f)))
            continue
        }
        fun m(k: Int) = p(f[inicio + 2 * k], f[inicio + 2 * k + 1])
        val palma = kotlin.math.hypot(f[inicio + 18] - f[inicio], f[inicio + 19] - f[inicio + 1])
        val dedo = maxOf(palma * 0.24f * escala, 2.5f)
        val contorno = linea(listOf(0, 1, 5, 9, 13, 17).map { m(it) }).apply { close() }
        for ((color, grosor) in listOf(PIEL_BORDE to dedo * 1.3f, PIEL to dedo)) {
            drawPath(contorno, color)
            drawPath(contorno, color, style = trazo(grosor))
            for (d in DEDOS) drawPath(linea(d.map { m(it) }), color, style = trazo(grosor))
        }
    }
}

@Composable
private fun DialogoSena(senas: List<String>, animaciones: Animaciones, alCerrar: () -> Unit) {
    Dialog(onDismissRequest = alCerrar) {
        Column(Modifier.width(330.dp).height(400.dp).background(BLANCO, RoundedCornerShape(8.dp)).padding(14.dp)) {
            AnimacionSena(animaciones, senas, Modifier.weight(1f).fillMaxWidth())
            T("Vista de frente, como la verías frente a ti. Grabación de LSC-54 (Mora-Zarate, 2025).",
                11.sp, GRAFITO, modifier = Modifier.padding(top = 8.dp))
            TextButton(alCerrar, Modifier.align(Alignment.End)) { T("Cerrar", 15.sp, AZUL, FontWeight.Medium) }
        }
    }
}

/** Dibuja en bucle una o varias señas (figura de esqueleto, vista de frente), como silva.animacion. */
@Composable
fun AnimacionSena(animaciones: Animaciones, senas: List<String>, modifier: Modifier = Modifier) {
    var actual by remember(senas) { mutableIntStateOf(0) }
    var cuadro by remember(senas) { mutableIntStateOf(0) }
    LaunchedEffect(senas) {
        var pausa = 0
        while (true) {
            delay(33)  // ~30 cuadros/s, la velocidad de la grabación
            val total = animaciones.cuadros(senas[actual]).size
            when {
                cuadro < total - 1 -> cuadro++
                pausa < 18 -> pausa++  // ~0,6 s quieto al final de cada seña
                else -> { actual = (actual + 1) % senas.size; cuadro = 0; pausa = 0 }
            }
        }
    }
    val nombre = senas[actual.coerceIn(senas.indices)]
    Column(modifier.background(BLANCO, RoundedCornerShape(6.dp)).border(1.dp, LINEA, RoundedCornerShape(6.dp)).padding(8.dp),
        horizontalAlignment = Alignment.CenterHorizontally) {
        Canvas(Modifier.weight(1f).fillMaxWidth()) {
            val cuadros = animaciones.cuadros(nombre)
            val f = cuadros[cuadro.coerceAtMost(cuadros.size - 1)]
            // la seña entera cabe en el recuadro (también las que suben las manos o abren los brazos)
            val (escala, ox, oy) = encuadre(animaciones.caja(nombre), size.width, size.height)
            clipRect { dibujarPersona(f) { x, y -> Offset(ox + x * escala, oy + y * escala) } }
        }
        T(nombre, 18.sp, peso = FontWeight.SemiBold)
        T(if (senas.size == 1) "SEÑA EN LSC" else "SEÑA ${actual + 1} DE ${senas.size} EN LSC", 10.sp, GRAFITO, familia = PLEX_MONO)
    }
}

// ---------------------------------------------------------------------- guías de las letras (Deletreo)
@Composable
private fun DialogoLetra(letra: String, guias: GuiasLetras, alCerrar: () -> Unit) {
    Dialog(onDismissRequest = alCerrar) {
        Column(Modifier.width(320.dp).height(420.dp).background(BLANCO, RoundedCornerShape(8.dp)).padding(14.dp)) {
            GuiaLetra(guias, letra, Modifier.weight(1f).fillMaxWidth())
            T("La mano derecha vista de frente, como la verías frente a ti. Imagen de LSC70 (Muñoz Galindez et al., 2024).",
                11.sp, GRAFITO, modifier = Modifier.padding(top = 8.dp))
            TextButton(alCerrar, Modifier.align(Alignment.End)) { T("Cerrar", 15.sp, AZUL, FontWeight.Medium) }
        }
    }
}

/** Cómo se hace una letra (silva.animacion.GuiaLetra): la mano en grande y, si se traza, su recorrido. */
@Composable
fun GuiaLetra(guias: GuiasLetras, letra: String, modifier: Modifier = Modifier) {
    val trazo = guias.conTrazo(letra)
    var cuadro by remember(letra) { mutableIntStateOf(0) }
    if (trazo) LaunchedEffect(letra) {
        while (true) {
            delay(33)
            cuadro = (cuadro + 1) % 60  // ~1,3 s de trazo y ~0,7 s quieta al final
        }
    }
    Column(modifier.background(BLANCO, RoundedCornerShape(6.dp)).border(1.dp, LINEA, RoundedCornerShape(6.dp)).padding(10.dp),
        horizontalAlignment = Alignment.CenterHorizontally) {
        Canvas(Modifier.weight(1f).fillMaxWidth()) {
            var cuadros = guias.cuadros(letra)
            if (trazo) {
                // la mano ocupa buena parte del recuadro; si el recorrido no cabe, se dibuja a escala reducida
                var ancho = 0f
                var alto = 0f
                var mx0 = Float.MAX_VALUE; var mx1 = -Float.MAX_VALUE; var my0 = Float.MAX_VALUE; var my1 = -Float.MAX_VALUE
                for (c in cuadros) {
                    for (k in 0 until 21) {
                        ancho = maxOf(ancho, kotlin.math.abs(c[2 * k] - c[0]))
                        alto = maxOf(alto, kotlin.math.abs(c[2 * k + 1] - c[1]))
                    }
                    mx0 = minOf(mx0, c[0]); mx1 = maxOf(mx1, c[0]); my0 = minOf(my0, c[1]); my1 = maxOf(my1, c[1])
                }
                val tamMano = 2 * maxOf(ancho, alto) + 0.7f
                val escalaMano = 0.62f * minOf(size.width, size.height) / tamMano
                val libreX = size.width - tamMano * escalaMano
                val libreY = size.height - tamMano * escalaMano
                val factor = minOf(1f, libreX / maxOf((mx1 - mx0) * escalaMano, 1e-6f), libreY / maxOf((my1 - my0) * escalaMano, 1e-6f))
                cuadros = acercarTrazo(cuadros, maxOf(factor, 0.15f))
            }
            val caja = floatArrayOf(Float.MAX_VALUE, Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE)
            for (c in cuadros) for (k in 0 until 21) {
                caja[0] = minOf(caja[0], c[2 * k] - 0.35f); caja[1] = minOf(caja[1], c[2 * k + 1] - 0.35f)
                caja[2] = maxOf(caja[2], c[2 * k] + 0.35f); caja[3] = maxOf(caja[3], c[2 * k + 1] + 0.35f)
            }
            val (escala, ox, oy) = encuadre(caja, size.width, size.height)
            fun p(x: Float, y: Float) = Offset(ox + x * escala, oy + y * escala)
            val mano = if (trazo) {
                val t = minOf(cuadro / 40f, 1f)
                // recorrido completo (punteado) y lo que ya se hizo (continuo), en la punta del índice
                val camino = Path()
                val hecho = Path()
                for (k in 0..30) {
                    val a = manoEn(cuadros, k / 30f)
                    val b = manoEn(cuadros, k / 30f * t)
                    if (k == 0) { camino.moveTo(p(a[16], a[17]).x, p(a[16], a[17]).y); hecho.moveTo(p(b[16], b[17]).x, p(b[16], b[17]).y) }
                    else { camino.lineTo(p(a[16], a[17]).x, p(a[16], a[17]).y); hecho.lineTo(p(b[16], b[17]).x, p(b[16], b[17]).y) }
                }
                drawPath(camino, AZUL, style = Stroke(maxOf(escala * 0.06f, 3f), cap = StrokeCap.Round,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(14f, 10f))))
                drawPath(hecho, AZUL, style = Stroke(maxOf(escala * 0.09f, 4f), cap = StrokeCap.Round, join = StrokeJoin.Round))
                manoEn(cuadros, t)
            } else cuadros[cuadros.size / 2]
            dibujarManoGuia(mano, escala) { x, y -> p(x, y) }
        }
        T(letra, 30.sp, peso = FontWeight.Bold)
        T(if (trazo) "SE TRAZA · LÍNEA AZUL" else "SE SOSTIENE QUIETA", 10.sp, GRAFITO, familia = PLEX_MONO)
    }
}

/** Una mano grande (palma y dedos con contorno); uñas en los dedos estirados, para ver hacia dónde apuntan. */
private fun DrawScope.dibujarManoGuia(m: FloatArray, escala: Float, p: (Float, Float) -> Offset) {
    fun q(k: Int) = p(m[2 * k], m[2 * k + 1])
    fun linea(puntos: List<Offset>) = Path().apply { moveTo(puntos[0].x, puntos[0].y); puntos.drop(1).forEach { lineTo(it.x, it.y) } }
    val dedo = maxOf(0.24f * escala, 6f)
    val contorno = linea(listOf(0, 1, 5, 9, 13, 17).map { q(it) }).apply { close() }
    for ((color, grosor) in listOf(PIEL_BORDE to dedo * 1.25f, PIEL to dedo)) {
        drawPath(contorno, color)
        drawPath(contorno, color, style = Stroke(grosor, cap = StrokeCap.Round, join = StrokeJoin.Round))
        for (d in DEDOS) drawPath(linea(d.map { q(it) }), color, style = Stroke(grosor, cap = StrokeCap.Round, join = StrokeJoin.Round))
    }
    val palma = kotlin.math.hypot(m[18] - m[0], m[19] - m[1])
    for ((punta, nudillo) in listOf(4 to 2, 8 to 5, 12 to 9, 16 to 13, 20 to 17)) {
        if (kotlin.math.hypot(m[2 * punta] - m[2 * nudillo], m[2 * punta + 1] - m[2 * nudillo + 1]) > 0.55f * palma) {
            drawCircle(Color(0xFFF3D9C6), dedo * 0.28f, q(punta))
        }
    }
}

