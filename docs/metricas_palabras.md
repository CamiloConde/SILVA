# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el 2026-10-31T14:29:31.

- Datasets: LSC-54 (Mora-Zarate, 2025) y, si está, LSC50 (Flórez-Sierra et al., 2024).
  Vocabulario (33 señas): Apoyar, Ayudar, Baño, Bien, Bienvenido, Buenas noches, Buenas tardes, Buenos días, Chao, Con gusto, De nada, Esperar, Excelente, Gracias, Hola, Invitar, Lo siento, Mal, Muchas gracias, Muy bien, Muy mal, Más o menos, Necesitar, No, Perdón, Perfecto, Permiso, Por favor, Presentar, Sentarse, Sí, Tranquilo, ¿Cómo está?.
- Clase de rechazo «otra cosa»: señas de LSC-54 fuera del vocabulario (Colores, LSC50-otras, Numeros),
  para que la app no escriba palabras ante cualquier movimiento.
- 6672 videos de 40 firmantes; sin tramo activo detectado (descartados): 1
- Clasificador: Extra Trees (400 árboles, scikit-learn 1.9.1) sobre 5580 características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: 19.9 ms por seña

## Evaluación con firmantes no vistos (6 pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor de las 33 opciones) | 83.8% |
| …solo con las personas de LSC50 (otro entorno de grabación) | 78.1% (entre las 3 primeras: 92.1%) |
| …solo con las personas de las muestras propias (grabadas con la app) | 27.8% |
| Palabras escritas ante el reposo y manos quietas (personas no vistas) | 0.1% |
| La seña correcta está entre las 3 primeras opciones | 94.7% |
| Umbral de confianza elegido | 0.15 |
| Señas reales que la app escribe sola | 63.3% |
| Exactitud de lo que escribe | 93.7% |
| Palabras falsas ante movimientos ajenos (categoría no vista) | 14.9% |
| Señas reales que quedan como «¿Quiso decir…?» | 12.6% (la correcta está entre las 3 opciones en el 92%) |

Regla de la app:
- Si la mejor seña conocida supera el umbral **y** tiene al menos 50% de la probabilidad
  de «otra cosa», se escribe de forma provisional, y quien esté en el computador puede corregirla o descartarla.
- Si solo supera 0.1 (y al menos 30% de «otra cosa»), se muestra
  «¿Quiso decir…?» con 3 opciones, sin escribir nada.
- En otro caso, no se muestra nada.

El umbral es el menor que logra al menos 93% de exactitud en lo escrito y a lo sumo
15% de palabras falsas.

Las palabras falsas se miden de forma honesta: con movimientos de una categoría que el modelo
**no** usó como «otra cosa» (entrenando con números se prueba con colores, y al revés), hechos por
personas no vistas. Como el modelo final aprende con ambas categorías, en uso real debería ser algo
mejor ante esos movimientos; ante gestos cotidianos (rascarse, acomodarse) no está medido.
Las falsas quedan provisionales: se pueden descartar con X antes de que se escriban.

| Umbral | Señas escritas | Exactitud de lo escrito | Palabras falsas |
|---|---|---|---|
| 0.10 | 65.2% | 92.3% | 16.5% |
| 0.15 | 63.3% | 93.7% | 14.9% |
| 0.20 | 58.4% | 95.3% | 10.3% |
| 0.25 | 51.7% | 97.7% | 5.5% |
| 0.30 | 44.2% | 98.5% | 2.7% |
| 0.35 | 37.5% | 99.3% | 1.4% |
| 0.40 | 31.7% | 99.4% | 0.7% |
| 0.45 | 25.6% | 99.7% | 0.5% |
| 0.50 | 21.1% | 99.7% | 0.3% |
| 0.55 | 16.4% | 99.6% | 0.2% |
| 0.60 | 12.5% | 99.5% | 0.1% |
| 0.65 | 9.0% | 99.3% | 0.0% |
| 0.70 | 6.5% | 99.0% | 0.0% |
| 0.75 | 3.9% | 100.0% | 0.0% |
| 0.80 | 2.1% | 100.0% | 0.0% |

<details><summary>Reporte por seña (mejor opción)</summary>

```
                precision    recall  f1-score   support

        Apoyar      0.893     0.962     0.926        26
        Ayudar      0.754     0.963     0.846        54
          Baño      0.767     0.885     0.821        26
          Bien      0.829     0.919     0.872        74
    Bienvenido      0.857     0.875     0.866        48
 Buenas noches      0.897     0.909     0.903        77
 Buenas tardes      0.842     0.853     0.848        75
   Buenos días      0.897     0.946     0.921        74
          Chao      0.830     0.800     0.815        55
     Con gusto      0.891     0.872     0.882        47
       De nada      0.818     0.982     0.893        55
       Esperar      0.923     0.889     0.906        27
     Excelente      0.955     0.778     0.857        27
       Gracias      0.674     0.630     0.652        46
          Hola      0.855     0.890     0.872        73
       Invitar      0.824     0.519     0.636        27
     Lo siento      0.962     0.893     0.926        28
           Mal      0.815     0.930     0.868        71
Muchas gracias      1.000     0.750     0.857        28
      Muy bien      0.968     0.714     0.822        42
       Muy mal      1.000     1.000     1.000        29
   Más o menos      0.757     0.583     0.659        48
     Necesitar      0.682     0.577     0.625        26
            No      0.750     0.536     0.625        28
        Perdón      0.747     0.890     0.812        73
      Perfecto      0.964     1.000     0.982        27
       Permiso      0.692     0.562     0.621        48
     Por favor      0.859     0.973     0.912        75
     Presentar      0.938     1.000     0.968        30
      Sentarse      0.933     1.000     0.966        28
            Sí      0.696     0.571     0.627        28
     Tranquilo      0.846     0.423     0.564        26
   ¿Cómo está?      0.788     0.837     0.812        49

      accuracy                          0.838      1495
     macro avg      0.846     0.816     0.823      1495
  weighted avg      0.839     0.838     0.833      1495

```
</details>
