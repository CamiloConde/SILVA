# Métricas del modelo de letras con movimiento

Generado por `scripts/entrenar_letras_movimiento.py` el 2026-10-26T21:17:40.

- Clasificador: Extra Trees (200 árboles, scikit-learn 1.9.1)
- Datos: LSC70 (Muñoz Galindez et al., 2024), 1851 señas de 70 personas, 6 cuadros por seña
- Clases: las 27 letras. Escribe solo G H J Ñ Q S Z; M, N y P casi no se mueven en LSC70 y las reconoce el modelo de letras estáticas
- Regla de recorrido: la muñeca debe recorrer al menos 0.4 tamaños de mano (en LSC70 lo supera el 90 % de las letras con movimiento; la mediana de las estáticas es 0,1-0,35)
- Aumento: 4 copias con rotación ±12°, escala, recorte temporal y ruido (solo en entrenamiento)
- Evaluación: validación cruzada de 5 pliegues por **persona** (personas no vistas)

| Métrica | Valor |
|---|---|
| Exactitud en las 27 letras | 86.3% |
| Exactitud en las letras con movimiento | 79.3% |

## Umbral de confianza

Una letra con movimiento se escribe si es la más probable, su probabilidad alcanza el umbral y la muñeca
recorrió lo suficiente. La app usa 0.4. Las transiciones son 2800 pasos de una letra estática
a otra armados con señas de LSC70 (no se usaron para entrenar); cada una se clasifica con el modelo que no vio a esa persona.

| Umbral | Letras con movimiento escritas | Acierto de lo escrito | Letra falsa en transiciones | Letra falsa con letras estáticas |
|---|---|---|---|---|
| 0.3 | 72.7% | 93.0% | 18.4% | 0.8% |
| 0.4 | 57.7% | 96.3% | 9.3% | 0.5% |
| 0.5 | 43.6% | 98.5% | 3.8% | 0.1% |
| 0.6 | 30.9% | 100.0% | 0.8% | 0.0% |
| 0.7 | 21.8% | 100.0% | 0.1% | 0.0% |

<details><summary>Reporte por letra (letras con movimiento, sin umbral)</summary>

```
              precision    recall  f1-score   support

           G      0.969     0.886     0.925        70
           H      0.818     0.692     0.750        65
           J      0.871     0.783     0.824        69
           Ñ      0.902     0.833     0.866        66
           Q      0.939     0.899     0.919        69
           S      0.726     0.662     0.692        68
           Z      0.743     0.788     0.765        66

   micro avg      0.852     0.793     0.821       473
   macro avg      0.853     0.792     0.820       473
weighted avg      0.854     0.793     0.821       473

```
</details>

**Límite:** LSC70 trae 6 imágenes por seña, no el video, así que no se pudo medir aquí la segmentación
en vivo (cuándo empieza y termina el movimiento). Eso se prueba con la cámara.
