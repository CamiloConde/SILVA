package co.edu.utb.silva.nucleo

import java.text.Normalizer

/** Mayúsculas sin tildes (la Ñ se conserva), como silva.sugerencias._base. */
fun baseDeletreo(texto: String): String {
    val sb = StringBuilder()
    for (c in Normalizer.normalize(texto.uppercase(), Normalizer.Form.NFD)) {
        if (Character.getType(c) == Character.NON_SPACING_MARK.toInt()) {
            if (c == '̃' && sb.isNotEmpty() && sb[sb.length - 1] == 'N') sb.setCharAt(sb.length - 1, 'Ñ')
            continue
        }
        sb.append(c)
    }
    return sb.toString()
}

/**
 * «¿Quisiste decir?» del Deletreo (silva.sugerencias): palabras frecuentes que empiezan como la que se
 * deletrea. Lista: palabras_es.txt (FrequencyWords, CC BY-SA 4.0), ordenada por frecuencia.
 */
class Sugerencias(lineas: List<String>) {
    private val palabras: List<Pair<String, String>> = lineas
        .filter { it.isNotBlank() && !it.startsWith("#") }
        .map { baseDeletreo(it) to it.uppercase() }

    fun para(texto: String, n: Int = 3): List<String> {
        val enCurso = baseDeletreo(texto.trimEnd('▏').split(" ").lastOrNull() ?: "")
        if (enCurso.length < 2 || !enCurso.all { it.isLetter() }) return emptyList()
        val salida = mutableListOf<String>()
        for ((base, palabra) in palabras) {
            if (base.length > enCurso.length && base.startsWith(enCurso) && palabra !in salida) {
                salida.add(palabra)
                if (salida.size == n) break
            }
        }
        return salida
    }
}
