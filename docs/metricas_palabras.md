# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el 2026-10-26T16:27:19.

- Datasets: LSC-54 (Mora-Zarate, 2025) y, si está, LSC50 (Flórez-Sierra et al., 2024).
  Vocabulario (33 señas): Apoyar, Ayudar, Baño, Bien, Bienvenido, Buenas noches, Buenas tardes, Buenos días, Chao, Con gusto, De nada, Esperar, Excelente, Gracias, Hola, Invitar, Lo siento, Mal, Muchas gracias, Muy bien, Muy mal, Más o menos, Necesitar, No, Perdón, Perfecto, Permiso, Por favor, Presentar, Sentarse, Sí, Tranquilo, ¿Cómo está?.
- Clase de rechazo «otra cosa»: señas de LSC-54 fuera del vocabulario (Colores, LSC50-otras, Numeros),
  para que la app no escriba palabras ante cualquier movimiento.
- 3880 videos de 39 firmantes; sin tramo activo detectado (descartados): 22
- Clasificador: Extra Trees (400 árboles, scikit-learn 1.9.1) sobre 5580 características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: 12.0 ms por seña

## Evaluación con firmantes no vistos (6 pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor de las 33 opciones) | 85.2% |
| …solo con las personas de LSC50 (otro entorno de grabación) | 77.1% (entre las 3 primeras: 91.8%) |
| La seña correcta está entre las 3 primeras opciones | 95.5% |
| Umbral de confianza elegido | 0.25 |
| Señas reales que la app escribe sola | 53.4% |
| Exactitud de lo que escribe | 96.3% |
| Palabras falsas ante movimientos ajenos (categoría no vista) | 9.1% |
| Señas reales que quedan como «¿Quiso decir…?» | 20.4% (la correcta está entre las 3 opciones en el 97%) |

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
| 0.10 | 61.2% | 92.7% | 25.7% |
| 0.15 | 60.6% | 93.1% | 21.5% |
| 0.20 | 57.8% | 94.7% | 14.6% |
| 0.25 | 53.4% | 96.3% | 9.1% |
| 0.30 | 47.7% | 97.2% | 5.9% |
| 0.35 | 41.2% | 98.2% | 3.9% |
| 0.40 | 35.7% | 98.1% | 2.7% |
| 0.45 | 29.3% | 98.4% | 2.4% |
| 0.50 | 23.7% | 99.1% | 1.9% |
| 0.55 | 19.2% | 98.9% | 1.6% |
| 0.60 | 15.0% | 99.1% | 1.5% |
| 0.65 | 12.1% | 99.4% | 0.8% |
| 0.70 | 8.9% | 99.2% | 0.3% |
| 0.75 | 5.7% | 98.8% | 0.2% |
| 0.80 | 4.0% | 98.3% | 0.0% |

<details><summary>Reporte por seña (mejor opción)</summary>

```
                precision    recall  f1-score   support

        Apoyar      1.000     0.962     0.980        26
        Ayudar      0.831     0.907     0.867        54
          Baño      0.719     0.885     0.793        26
          Bien      0.859     0.905     0.882        74
    Bienvenido      0.915     0.896     0.905        48
 Buenas noches      0.933     0.909     0.921        77
 Buenas tardes      0.848     0.893     0.870        75
   Buenos días      0.899     0.959     0.928        74
          Chao      0.825     0.855     0.839        55
     Con gusto      0.864     0.809     0.835        47
       De nada      0.855     0.964     0.906        55
       Esperar      1.000     0.889     0.941        27
     Excelente      1.000     0.852     0.920        27
       Gracias      0.653     0.696     0.674        46
          Hola      0.865     0.877     0.871        73
       Invitar      0.833     0.556     0.667        27
     Lo siento      0.897     0.929     0.912        28
           Mal      0.790     0.901     0.842        71
Muchas gracias      1.000     0.821     0.902        28
      Muy bien      0.926     0.962     0.943        26
       Muy mal      0.900     0.931     0.915        29
   Más o menos      0.838     0.646     0.729        48
     Necesitar      0.714     0.577     0.638        26
            No      0.750     0.536     0.625        28
        Perdón      0.733     0.904     0.810        73
      Perfecto      0.964     1.000     0.982        27
       Permiso      0.711     0.562     0.628        48
     Por favor      0.820     0.973     0.890        75
     Presentar      0.938     1.000     0.968        30
      Sentarse      0.966     1.000     0.982        28
            Sí      0.762     0.615     0.681        26
     Tranquilo      0.917     0.423     0.579        26
   ¿Cómo está?      0.956     0.878     0.915        49

      accuracy                          0.852      1477
     macro avg      0.863     0.832     0.841      1477
  weighted avg      0.854     0.852     0.848      1477

```
</details>
