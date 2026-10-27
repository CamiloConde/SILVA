package co.edu.utb.silva

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * «Escuchar» (texto a voz) y «Hablar» (voz a texto) del teléfono.
 *
 * La voz la pone el motor de Android (funciona sin internet con las voces instaladas). Para reconocer
 * lo que dice la persona oyente se prefiere el reconocedor del propio teléfono (Android 12+), que no
 * envía el audio; si el teléfono no tiene uno, se usa el del sistema pidiéndole que trabaje sin conexión.
 */
class Voz(private val context: Context) : AutoCloseable {
    private val espanol = Locale.forLanguageTag("es-CO")
    private var lista = false
    private val tts: TextToSpeech
    private var reconocedor: SpeechRecognizer? = null

    init {
        var motor: TextToSpeech? = null
        motor = TextToSpeech(context) { estado ->
            lista = estado == TextToSpeech.SUCCESS
            if (lista) motor?.language = espanol
        }
        tts = motor
    }

    val puedeEscuchar get() = SpeechRecognizer.isRecognitionAvailable(context)

    fun leer(texto: String) {
        if (lista && texto.isNotBlank()) tts.speak(texto.lowercase(espanol), TextToSpeech.QUEUE_FLUSH, null, "silva")
    }

    /** Empieza a escuchar; `parcial` recibe lo que va entendiendo y `final` la frase completa (o null si no entendió). */
    fun escuchar(parcial: (String) -> Unit, final: (String?) -> Unit) {
        detenerEscucha()
        val r = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && SpeechRecognizer.isOnDeviceRecognitionAvailable(context))
            SpeechRecognizer.createOnDeviceSpeechRecognizer(context) else SpeechRecognizer.createSpeechRecognizer(context)
        reconocedor = r
        r.setRecognitionListener(object : RecognitionListener {
            override fun onPartialResults(resultados: Bundle) {
                resultados.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.let(parcial)
            }

            override fun onResults(resultados: Bundle) {
                final(resultados.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull())
            }

            override fun onError(error: Int) = final(null)
            override fun onReadyForSpeech(p: Bundle?) = Unit
            override fun onBeginningOfSpeech() = Unit
            override fun onRmsChanged(rms: Float) = Unit
            override fun onBufferReceived(b: ByteArray?) = Unit
            override fun onEndOfSpeech() = Unit
            override fun onEvent(tipo: Int, datos: Bundle?) = Unit
        })
        r.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-CO")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
        })
    }

    fun detenerEscucha() {
        reconocedor?.destroy()
        reconocedor = null
    }

    override fun close() {
        detenerEscucha()
        tts.shutdown()
    }
}
