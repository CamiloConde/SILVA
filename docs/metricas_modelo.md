# Métricas del modelo de señas

Generado por `scripts/entrenar_modelo.py` el 2026-10-08T16:55:16.

- Clasificador: Random Forest (150 árboles, scikit-learn 1.9.1)
- Letras (17): A B C D E F I K L O R T U V W X Y
- Muestras originales: 15810 (externo: 15810)
- Aumento de datos: 3 copias rotadas ±15° con ruido gaussiano (solo en entrenamiento)
- Tiempo de inferencia: 4.49 ms por cuadro

## Evaluación 80/20 separando secuencias completas

| Métrica | Valor |
|---|---|
| Muestras de prueba | 3180 |
| Exactitud (todas las predicciones) | 99.9% |
| F1 macro | 0.999 |
| Cobertura con confianza ≥ 0.80 | 99.0% |
| Exactitud de las predicciones con confianza ≥ 0.80 | 100.0% |

<details><summary>Reporte por letra</summary>

```
              precision    recall  f1-score   support

           A      1.000     1.000     1.000       300
           B      1.000     1.000     1.000       120
           C      1.000     1.000     1.000       420
           D      1.000     1.000     1.000       120
           E      1.000     0.983     0.992       180
           F      1.000     1.000     1.000       210
           I      1.000     1.000     1.000       150
           K      1.000     1.000     1.000       150
           L      1.000     1.000     1.000        90
           O      1.000     1.000     1.000       180
           R      1.000     1.000     1.000       270
           T      1.000     1.000     1.000       150
           U      1.000     1.000     1.000        90
           V      1.000     1.000     1.000        60
           W      1.000     1.000     1.000       180
           X      0.980     1.000     0.990       150
           Y      1.000     1.000     1.000       360

    accuracy                          0.999      3180
   macro avg      0.999     0.999     0.999      3180
weighted avg      0.999     0.999     0.999      3180

```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
        A    B    C    D    E    F    I    K    L    O    R    T    U    V    W    X    Y
   A  300    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   B    0  120    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   C    0    0  420    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   D    0    0    0  120    0    0    0    0    0    0    0    0    0    0    0    0    0
   E    0    0    0    0  177    0    0    0    0    0    0    0    0    0    0    3    0
   F    0    0    0    0    0  210    0    0    0    0    0    0    0    0    0    0    0
   I    0    0    0    0    0    0  150    0    0    0    0    0    0    0    0    0    0
   K    0    0    0    0    0    0    0  150    0    0    0    0    0    0    0    0    0
   L    0    0    0    0    0    0    0    0   90    0    0    0    0    0    0    0    0
   O    0    0    0    0    0    0    0    0    0  180    0    0    0    0    0    0    0
   R    0    0    0    0    0    0    0    0    0    0  270    0    0    0    0    0    0
   T    0    0    0    0    0    0    0    0    0    0    0  150    0    0    0    0    0
   U    0    0    0    0    0    0    0    0    0    0    0    0   90    0    0    0    0
   V    0    0    0    0    0    0    0    0    0    0    0    0    0   60    0    0    0
   W    0    0    0    0    0    0    0    0    0    0    0    0    0    0  180    0    0
   X    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  150    0
   Y    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  360
```
</details>
