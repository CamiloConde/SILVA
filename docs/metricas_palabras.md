# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el 2026-10-26T22:20:57.

- Datasets: LSC-54 (Mora-Zarate, 2025) y, si está, LSC50 (Flórez-Sierra et al., 2024).
  Vocabulario (33 señas): Apoyar, Ayudar, Baño, Bien, Bienvenido, Buenas noches, Buenas tardes, Buenos días, Chao, Con gusto, De nada, Esperar, Excelente, Gracias, Hola, Invitar, Lo siento, Mal, Muchas gracias, Muy bien, Muy mal, Más o menos, Necesitar, No, Perdón, Perfecto, Permiso, Por favor, Presentar, Sentarse, Sí, Tranquilo, ¿Cómo está?.
- Clase de rechazo «otra cosa»: señas de LSC-54 fuera del vocabulario (Colores, LSC50-otras, Numeros),
  para que la app no escriba palabras ante cualquier movimiento.
- 3880 videos de 39 firmantes; sin tramo activo detectado (descartados): 17
- Clasificador: Extra Trees (400 árboles, scikit-learn 1.9.1) sobre 5580 características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: 13.4 ms por seña

## Evaluación con firmantes no vistos (6 pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor de las 33 opciones) | 85.3% |
| …solo con las personas de LSC50 (otro entorno de grabación) | 76.7% (entre las 3 primeras: 91.8%) |
| La seña correcta está entre las 3 primeras opciones | 95.7% |
| Umbral de confianza elegido | 0.20 |
| Señas reales que la app escribe sola | 56.4% |
| Exactitud de lo que escribe | 95.7% |
| Palabras falsas ante movimientos ajenos (categoría no vista) | 12.5% |
| Señas reales que quedan como «¿Quiso decir…?» | 16.7% (la correcta está entre las 3 opciones en el 96%) |

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
| 0.10 | 59.5% | 94.3% | 22.8% |
| 0.15 | 58.9% | 94.6% | 18.6% |
| 0.20 | 56.4% | 95.7% | 12.5% |
| 0.25 | 51.5% | 97.0% | 7.4% |
| 0.30 | 46.6% | 97.7% | 4.1% |
| 0.35 | 41.0% | 98.7% | 2.3% |
| 0.40 | 36.2% | 98.9% | 1.3% |
| 0.45 | 30.4% | 99.1% | 0.7% |
| 0.50 | 24.4% | 99.7% | 0.4% |
| 0.55 | 19.6% | 99.7% | 0.2% |
| 0.60 | 15.5% | 99.6% | 0.2% |
| 0.65 | 12.4% | 99.5% | 0.1% |
| 0.70 | 9.1% | 99.3% | 0.0% |
| 0.75 | 6.3% | 98.9% | 0.0% |
| 0.80 | 3.9% | 100.0% | 0.0% |

<details><summary>Reporte por seña (mejor opción)</summary>

```
                precision    recall  f1-score   support

        Apoyar      0.929     1.000     0.963        26
        Ayudar      0.839     0.963     0.897        54
          Baño      0.733     0.846     0.786        26
          Bien      0.890     0.878     0.884        74
    Bienvenido      0.860     0.896     0.878        48
 Buenas noches      0.920     0.896     0.908        77
 Buenas tardes      0.823     0.867     0.844        75
   Buenos días      0.887     0.959     0.922        74
          Chao      0.814     0.873     0.842        55
     Con gusto      0.870     0.851     0.860        47
       De nada      0.871     0.982     0.923        55
       Esperar      0.962     0.926     0.943        27
     Excelente      0.958     0.852     0.902        27
       Gracias      0.638     0.652     0.645        46
          Hola      0.855     0.890     0.872        73
       Invitar      0.842     0.593     0.696        27
     Lo siento      0.963     0.929     0.945        28
           Mal      0.851     0.887     0.869        71
Muchas gracias      0.957     0.786     0.863        28
      Muy bien      1.000     0.962     0.980        26
       Muy mal      0.935     1.000     0.967        29
   Más o menos      0.800     0.667     0.727        48
     Necesitar      0.640     0.615     0.627        26
            No      0.700     0.500     0.583        28
        Perdón      0.767     0.904     0.830        73
      Perfecto      1.000     1.000     1.000        27
       Permiso      0.763     0.604     0.674        48
     Por favor      0.857     0.960     0.906        75
     Presentar      0.882     1.000     0.938        30
      Sentarse      0.964     0.964     0.964        28
            Sí      0.667     0.538     0.596        26
     Tranquilo      0.882     0.577     0.698        26
   ¿Cómo está?      0.951     0.796     0.867        49

      accuracy                          0.853      1477
     macro avg      0.857     0.837     0.842      1477
  weighted avg      0.853     0.853     0.850      1477

```
</details>
