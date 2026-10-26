# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el 2026-10-26T14:36:53.

- Dataset: LSC-54 (Mora-Zarate, 2025). Vocabulario: las 33 expresiones de cortesía
  (Apoyar, Ayudar, Baño, Bien, Bienvenido, Buenas noches, Buenas tardes, Buenos días, Chao, ¿Cómo está?, Con gusto, De nada, Esperar, Excelente, Gracias, Hola, Invitar, Lo siento, Mal, Más o menos, Muchas gracias, Muy bien, Muy mal, Necesitar, No, Perdón, Perfecto, Permiso, Por favor, Presentar, Sentarse, Sí, Tranquilo).
- Clase de rechazo «otra cosa»: señas de LSC-54 fuera del vocabulario (Colores, Numeros),
  para que la app no escriba palabras ante cualquier movimiento.
- 2880 videos de 34 firmantes; sin tramo activo detectado (descartados): 19
- Clasificador: Extra Trees (400 árboles, scikit-learn 1.9.1) sobre 5580 características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: 12.2 ms por seña

## Evaluación con firmantes no vistos (6 pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor de las 33 opciones) | 85.1% |
| La seña correcta está entre las 3 primeras opciones | 95.5% |
| Umbral de confianza elegido | 0.25 |
| Señas reales que la app escribe sola | 66.5% |
| Exactitud de lo que escribe | 96.0% |
| Palabras falsas ante movimientos ajenos (categoría no vista) | 11.5% |
| Señas reales que quedan como «¿Quiso decir…?» | 20.5% (la correcta está entre las 3 opciones en el 93%) |

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
| 0.10 | 80.5% | 90.9% | 17.8% |
| 0.15 | 78.5% | 91.8% | 17.2% |
| 0.20 | 73.1% | 93.9% | 15.6% |
| 0.25 | 66.5% | 96.0% | 11.5% |
| 0.30 | 60.4% | 97.1% | 7.9% |
| 0.35 | 53.9% | 98.0% | 4.6% |
| 0.40 | 47.2% | 98.8% | 2.8% |
| 0.45 | 40.9% | 99.2% | 1.7% |
| 0.50 | 33.1% | 99.2% | 0.8% |
| 0.55 | 27.6% | 99.1% | 0.5% |
| 0.60 | 22.9% | 99.3% | 0.1% |
| 0.65 | 17.8% | 99.5% | 0.0% |
| 0.70 | 13.4% | 99.4% | 0.0% |
| 0.75 | 8.8% | 99.1% | 0.0% |
| 0.80 | 6.2% | 98.6% | 0.0% |

<details><summary>Reporte por seña (mejor de las 33 opciones)</summary>

```
                precision    recall  f1-score   support

        Apoyar      0.962     0.962     0.962        26
        Ayudar      0.746     0.981     0.848        54
          Baño      0.786     0.846     0.815        26
          Bien      0.880     0.815     0.846        54
    Bienvenido      0.933     1.000     0.966        28
 Buenas noches      0.929     0.912     0.920        57
 Buenas tardes      0.980     0.909     0.943        55
   Buenos días      0.855     0.981     0.914        54
          Chao      0.758     0.855     0.803        55
     Con gusto      0.871     0.964     0.915        28
       De nada      0.857     0.982     0.915        55
       Esperar      1.000     0.926     0.962        27
     Excelente      0.950     0.704     0.809        27
       Gracias      1.000     0.346     0.514        26
          Hola      0.803     0.925     0.860        53
       Invitar      0.889     0.593     0.711        27
     Lo siento      0.964     0.964     0.964        28
           Mal      0.758     0.922     0.832        51
Muchas gracias      0.875     0.750     0.808        28
      Muy bien      0.929     1.000     0.963        26
       Muy mal      1.000     0.828     0.906        29
   Más o menos      0.824     0.500     0.622        28
     Necesitar      0.609     0.538     0.571        26
            No      0.769     0.357     0.488        28
        Perdón      0.746     0.887     0.810        53
      Perfecto      1.000     0.963     0.981        27
       Permiso      0.639     0.821     0.719        28
     Por favor      0.831     0.982     0.900        55
     Presentar      0.938     1.000     0.968        30
      Sentarse      0.966     1.000     0.982        28
            Sí      0.696     0.615     0.653        26
     Tranquilo      0.867     0.500     0.634        26
   ¿Cómo está?      0.963     0.897     0.929        29

      accuracy                          0.851      1198
     macro avg      0.866     0.825     0.831      1198
  weighted avg      0.858     0.851     0.843      1198

```
</details>
