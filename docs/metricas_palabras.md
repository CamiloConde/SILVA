# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el 2026-10-27T21:36:20.

- Datasets: LSC-54 (Mora-Zarate, 2025) y, si está, LSC50 (Flórez-Sierra et al., 2024).
  Vocabulario (33 señas): Apoyar, Ayudar, Baño, Bien, Bienvenido, Buenas noches, Buenas tardes, Buenos días, Chao, Con gusto, De nada, Esperar, Excelente, Gracias, Hola, Invitar, Lo siento, Mal, Muchas gracias, Muy bien, Muy mal, Más o menos, Necesitar, No, Perdón, Perfecto, Permiso, Por favor, Presentar, Sentarse, Sí, Tranquilo, ¿Cómo está?.
- Clase de rechazo «otra cosa»: señas de LSC-54 fuera del vocabulario (Colores, LSC50-otras, Numeros),
  para que la app no escriba palabras ante cualquier movimiento.
- 6649 videos de 39 firmantes; sin tramo activo detectado (descartados): 1
- Clasificador: Extra Trees (400 árboles, scikit-learn 1.9.1) sobre 5580 características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: 18.3 ms por seña

## Evaluación con firmantes no vistos (6 pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor de las 33 opciones) | 84.4% |
| …solo con las personas de LSC50 (otro entorno de grabación) | 77.4% (entre las 3 primeras: 91.4%) |
| …solo con las personas de las muestras propias (grabadas con la app) | sin muestras |
| Palabras escritas ante el reposo y manos quietas (personas no vistas) | 0.0% |
| La seña correcta está entre las 3 primeras opciones | 94.5% |
| Umbral de confianza elegido | 0.15 |
| Señas reales que la app escribe sola | 49.6% |
| Exactitud de lo que escribe | 95.1% |
| Palabras falsas ante movimientos ajenos (categoría no vista) | 3.6% |
| Señas reales que quedan como «¿Quiso decir…?» | 15.9% (la correcta está entre las 3 opciones en el 96%) |

Regla de la app:
- Si la mejor seña conocida supera el umbral **y** a «otra cosa», se escribe de forma
  provisional, y quien esté en el computador puede corregirla o descartarla.
- Si solo supera 0.12 (y al menos la mitad de «otra cosa»), se muestra «¿Quiso decir…?»
  con 3 opciones, sin escribir nada.
- En otro caso, no se muestra nada.

El umbral es el menor que logra al menos 95% de exactitud en lo escrito y a lo sumo
15% de palabras falsas.

Las palabras falsas se miden de forma honesta: con movimientos de una categoría que el modelo
**no** usó como «otra cosa» (entrenando con números se prueba con colores, y al revés), hechos por
personas no vistas. Como el modelo final aprende con ambas categorías, en uso real debería ser algo
mejor ante esos movimientos; ante gestos cotidianos (rascarse, acomodarse) no está medido.
Las falsas quedan provisionales: se pueden descartar con X antes de que se escriban.

| Umbral | Señas escritas | Exactitud de lo escrito | Palabras falsas |
|---|---|---|---|
| 0.10 | 49.8% | 94.8% | 3.6% |
| 0.15 | 49.6% | 95.1% | 3.6% |
| 0.20 | 47.9% | 96.2% | 3.2% |
| 0.25 | 45.3% | 97.8% | 2.6% |
| 0.30 | 41.4% | 98.2% | 1.6% |
| 0.35 | 36.7% | 98.7% | 1.0% |
| 0.40 | 32.1% | 99.2% | 0.6% |
| 0.45 | 26.4% | 99.5% | 0.5% |
| 0.50 | 21.4% | 99.4% | 0.2% |
| 0.55 | 17.1% | 99.6% | 0.1% |
| 0.60 | 13.0% | 99.5% | 0.1% |
| 0.65 | 9.8% | 99.3% | 0.0% |
| 0.70 | 6.6% | 99.0% | 0.0% |
| 0.75 | 4.3% | 98.4% | 0.0% |
| 0.80 | 2.2% | 100.0% | 0.0% |

<details><summary>Reporte por seña (mejor opción)</summary>

```
                precision    recall  f1-score   support

        Apoyar      0.963     1.000     0.981        26
        Ayudar      0.803     0.981     0.883        54
          Baño      0.750     0.923     0.828        26
          Bien      0.859     0.905     0.882        74
    Bienvenido      0.833     0.938     0.882        48
 Buenas noches      0.875     0.909     0.892        77
 Buenas tardes      0.821     0.853     0.837        75
   Buenos días      0.897     0.946     0.921        74
          Chao      0.782     0.782     0.782        55
     Con gusto      0.889     0.851     0.870        47
       De nada      0.806     0.982     0.885        55
       Esperar      0.960     0.889     0.923        27
     Excelente      0.955     0.778     0.857        27
       Gracias      0.660     0.674     0.667        46
          Hola      0.844     0.890     0.867        73
       Invitar      0.733     0.407     0.524        27
     Lo siento      0.962     0.893     0.926        28
           Mal      0.807     0.944     0.870        71
Muchas gracias      1.000     0.750     0.857        28
      Muy bien      0.962     0.962     0.962        26
       Muy mal      0.967     1.000     0.983        29
   Más o menos      0.769     0.625     0.690        48
     Necesitar      0.640     0.615     0.627        26
            No      0.765     0.464     0.578        28
        Perdón      0.765     0.849     0.805        73
      Perfecto      1.000     1.000     1.000        27
       Permiso      0.694     0.521     0.595        48
     Por favor      0.889     0.960     0.923        75
     Presentar      0.909     1.000     0.952        30
      Sentarse      0.966     1.000     0.982        28
            Sí      0.882     0.577     0.698        26
     Tranquilo      0.933     0.538     0.683        26
   ¿Cómo está?      0.889     0.816     0.851        49

      accuracy                          0.844      1477
     macro avg      0.855     0.825     0.832      1477
  weighted avg      0.845     0.844     0.839      1477

```
</details>
