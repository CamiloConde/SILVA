package co.edu.utb.silva

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.view.View
import co.edu.utb.silva.nucleo.CONEXIONES_MANO
import co.edu.utb.silva.nucleo.Config
import co.edu.utb.silva.nucleo.MANO_POSE_DER
import co.edu.utb.silva.nucleo.MANO_POSE_IZQ
import co.edu.utb.silva.nucleo.POSE_CONEXIONES
import co.edu.utb.silva.nucleo.Punto

/**
 * Video sobre fondo tinta con el esqueleto discreto (líneas claras, puntos blancos) y, según el modo,
 * el recuadro donde va la mano (Deletreo) o la silueta de encuadre (Palabras), como en la identidad v2.
 */
class VistaCamara(context: Context) : View(context) {
    private var fotograma: Fotograma? = null
    var espejo = false
    var guia: String? = null  // "ok" | "ajustar" | null
    var recuadro = false
    var rellenar = false  // Deletreo: la imagen llena el recuadro (solo importa la mano); Palabras: se ve completa

    private val densidad = resources.displayMetrics.density
    private val lineaMano = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(200, 203, 205); strokeWidth = 2f * densidad }
    private val lineaPose = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(145, 148, 150); strokeWidth = 2f * densidad }
    private val punto = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(245, 245, 245) }
    private val aproximada = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE; strokeWidth = 1.5f * densidad; color = Color.rgb(160, 160, 160)
    }
    private val marco = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE; strokeWidth = 1.5f * densidad; color = Color.argb(110, 255, 255, 255)
    }
    private val silueta = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE; strokeWidth = 2.2f * densidad
        pathEffect = DashPathEffect(floatArrayOf(10f * densidad, 7f * densidad), 0f)
    }
    private val imagen = Paint(Paint.FILTER_BITMAP_FLAG)
    private val destino = RectF()

    fun mostrar(f: Fotograma) {
        fotograma = f
        invalidate()
    }

    fun limpiar() {
        fotograma = null
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        canvas.clipRect(0, 0, width, height)  // nada se sale de la vista (la imagen ampliada de Deletreo)
        canvas.drawColor(Color.rgb(0x16, 0x18, 0x1D))
        val f = fotograma ?: return
        val img = f.imagen
        val escala = if (rellenar) maxOf(width.toFloat() / img.width, height.toFloat() / img.height)
            else minOf(width.toFloat() / img.width, height.toFloat() / img.height)
        val w = img.width * escala
        val h = img.height * escala
        destino.set((width - w) / 2, (height - h) / 2, (width + w) / 2, (height + h) / 2)
        canvas.save()
        canvas.clipRect(destino)  // el esqueleto no se dibuja fuera de la imagen
        if (espejo) canvas.scale(-1f, 1f, width / 2f, height / 2f)
        canvas.drawBitmap(img, null, destino, imagen)
        fun px(p: Punto) = destino.left + p.x * w
        fun py(p: Punto) = destino.top + p.y * h

        f.resultado.mano?.let { dibujarMano(canvas, it.puntos, ::px, ::py) }
        f.resultado.cuerpo?.let { c ->
            c.pose?.let { pose ->
                for ((a, b) in POSE_CONEXIONES) canvas.drawLine(px(pose[a]), py(pose[a]), px(pose[b]), py(pose[b]), lineaPose)
            }
            for ((mano, puntosPose) in listOf(c.manoIzquierda to MANO_POSE_IZQ, c.manoDerecha to MANO_POSE_DER)) {
                if (mano != null) dibujarMano(canvas, mano, ::px, ::py)
                else c.pose?.let { pose ->
                    // mano perdida: posición aproximada que da el esqueleto (círculos huecos)
                    val q = puntosPose.map { pose[it] }
                    for (k in 1..3) canvas.drawLine(px(q[0]), py(q[0]), px(q[k]), py(q[k]), aproximada)
                    for (p in q) canvas.drawCircle(px(p), py(p), 4f * densidad, aproximada)
                }
            }
        }
        if (recuadro) {  // sobre la parte visible de la imagen (en Deletreo la imagen llena la vista y se sale)
            val vis = RectF(maxOf(destino.left, 0f), maxOf(destino.top, 0f), minOf(destino.right, width.toFloat()),
                minOf(destino.bottom, height.toFloat()))
            val ancho = vis.width() * 0.72f
            val alto = minOf(ancho / 0.88f, vis.height() * 0.8f)
            canvas.drawRect(vis.centerX() - ancho / 2, vis.centerY() - alto / 2, vis.centerX() + ancho / 2,
                vis.centerY() + alto / 2, marco)
        }
        guia?.let { dibujarGuia(canvas, it == "ok") }
        canvas.restore()
    }

    private fun dibujarMano(canvas: Canvas, mano: List<Punto>, px: (Punto) -> Float, py: (Punto) -> Float) {
        for ((a, b) in CONEXIONES_MANO) canvas.drawLine(px(mano[a]), py(mano[a]), px(mano[b]), py(mano[b]), lineaMano)
        for (p in mano) canvas.drawCircle(px(p), py(p), 2.6f * densidad, punto)
    }

    /** Silueta en la posición en que se grabaron los datos de entrenamiento (config.ENCUADRE_*). */
    private fun dibujarGuia(canvas: Canvas, ok: Boolean) {
        silueta.color = if (ok) Color.argb(170, 0x1F, 0x4F, 0xD8) else Color.argb(220, 0xE8, 0xA3, 0x17)
        val d = destino
        val rango = if (d.width() < d.height()) Config.ENCUADRE_HOMBROS_VERTICAL else Config.ENCUADRE_HOMBROS
        val anchoH = d.width() * (rango[0] + rango[1]).toFloat() / 2 * 0.95f
        val cx = d.centerX()
        val yH = d.top + 0.50f * d.height()
        val yN = d.top + 0.31f * d.height()
        val radio = anchoH * 0.32f
        canvas.drawOval(RectF(cx - radio, yN - radio * 1.15f, cx + radio, yN + radio * 1.15f), silueta)
        val torso = Path().apply {
            moveTo(cx - anchoH / 2 - 10, d.bottom)
            lineTo(cx - anchoH / 2, yH)
            quadTo(cx, yH - radio * 0.6f, cx + anchoH / 2, yH)
            lineTo(cx + anchoH / 2 + 10, d.bottom)
        }
        canvas.drawPath(torso, silueta)
    }
}
