# Métricas del modelo de palabras (LSC-54)

Generado por `scripts/entrenar_palabras.py` el 2026-10-24T11:11:43.

- Dataset: LSC-54 (Mora-Zarate, 2025), categorías: Cordialidad
- 1198 videos de 18 firmantes, 33 señas: Apoyar, Ayudar, Baño, Bien, Bienvenido, Buenas noches, Buenas tardes, Buenos días, Chao, ¿Cómo está?, Con gusto, De nada, Esperar, Excelente, Gracias, Hola, Invitar, Lo siento, Mal, Más o menos, Muchas gracias, Muy bien, Muy mal, Necesitar, No, Perdón, Perfecto, Permiso, Por favor, Presentar, Sentarse, Sí, Tranquilo
- Videos sin tramo activo detectado (descartados): 0
- Clasificador: Extra Trees (400 árboles, scikit-learn 1.9.1) sobre 5580 características
  (20 cuadros remuestreados de pose + ambas manos, sus velocidades y la forma de cada mano);
  aumento con espejo izquierda/derecha
- Tiempo de clasificación: 13.9 ms por seña

## Evaluación con firmantes no vistos (6 pliegues, agrupados por firmante)

| Métrica | Valor |
|---|---|
| Exactitud (mejor opción del modelo) | 85.6% |
| F1 macro | 0.840 |
| Umbral de confianza elegido | 0.20 |
| Señas que la app escribe (confianza ≥ umbral) | 88.0% |
| Exactitud de las señas que escribe | 91.1% |

Las señas por debajo del umbral no se escriben: la app pide repetirlas. El umbral es el menor
que logra al menos 90% de exactitud en lo que se escribe.

| Umbral | Señas escritas | Exactitud de lo escrito |
|---|---|---|
| 0.10 | 99.7% | 85.9% |
| 0.15 | 95.4% | 88.5% |
| 0.20 | 88.0% | 91.1% |
| 0.25 | 78.4% | 93.1% |
| 0.30 | 69.1% | 95.0% |
| 0.35 | 61.0% | 96.7% |
| 0.40 | 53.8% | 98.3% |
| 0.45 | 45.4% | 98.5% |
| 0.50 | 38.9% | 98.9% |
| 0.55 | 33.4% | 99.2% |
| 0.60 | 27.4% | 99.4% |
| 0.65 | 21.1% | 99.6% |
| 0.70 | 15.8% | 99.5% |
| 0.75 | 11.9% | 99.3% |
| 0.80 | 7.4% | 100.0% |

<details><summary>Reporte por seña</summary>

```
                precision    recall  f1-score   support

        Apoyar      0.962     0.962     0.962        26
        Ayudar      0.794     0.926     0.855        54
          Baño      0.750     0.808     0.778        26
          Bien      0.797     0.870     0.832        54
    Bienvenido      0.933     1.000     0.966        28
 Buenas noches      0.914     0.930     0.922        57
 Buenas tardes      0.980     0.873     0.923        55
   Buenos días      0.883     0.981     0.930        54
          Chao      0.742     0.891     0.810        55
     Con gusto      0.964     0.964     0.964        28
       De nada      0.900     0.982     0.939        55
       Esperar      0.960     0.889     0.923        27
     Excelente      1.000     0.778     0.875        27
       Gracias      0.800     0.462     0.585        26
          Hola      0.800     0.906     0.850        53
       Invitar      0.850     0.630     0.723        27
     Lo siento      0.903     1.000     0.949        28
           Mal      0.852     0.902     0.876        51
Muchas gracias      0.905     0.679     0.776        28
      Muy bien      1.000     0.962     0.980        26
       Muy mal      0.960     0.828     0.889        29
   Más o menos      0.929     0.464     0.619        28
     Necesitar      0.692     0.692     0.692        26
            No      0.824     0.500     0.622        28
        Perdón      0.742     0.925     0.824        53
      Perfecto      1.000     0.926     0.962        27
       Permiso      0.667     0.786     0.721        28
     Por favor      0.885     0.982     0.931        55
     Presentar      0.784     0.967     0.866        30
      Sentarse      0.966     1.000     0.982        28
            Sí      0.762     0.615     0.681        26
     Tranquilo      0.875     0.538     0.667        26
   ¿Cómo está?      0.862     0.862     0.862        29

      accuracy                          0.856      1198
     macro avg      0.868     0.833     0.840      1198
  weighted avg      0.863     0.856     0.851      1198

```
</details>
