# Métricas del modelo de letras

Generado por `scripts/entrenar_modelo.py` el 2026-10-26T15:50:47.

- Clasificador: Random Forest (150 árboles, scikit-learn 1.9.1)
- Letras (17): A B C D E F I K L O R T U V W X Y
- Muestras: 22846 (JuanPlazas (1 persona): 15810, LSC70 (70 personas): 7036)
- Aumento de datos: 3 copias rotadas ±15° con ruido gaussiano (solo en entrenamiento)
- Tiempo de inferencia: 13.97 ms por cuadro

La cifra que representa el uso real es la de **LSC70 con personas no vistas**: el dataset de
JuanPlazas es de una sola persona, así que su validación cruzada es optimista.

## Validación cruzada (5 pliegues por grupo): muestras de JuanPlazas (1 persona), grupos no vistos

| Métrica | Valor |
|---|---|
| Muestras de prueba | 15810 |
| Exactitud (todas las predicciones) | 99.7% |
| F1 macro | 0.997 |
| Cobertura con confianza ≥ 0.80 (lo que la app escribe) | 99.5% |
| Exactitud de las predicciones con confianza ≥ 0.80 | 100.0% |

<details><summary>Reporte por letra</summary>

```
              precision    recall  f1-score   support

           A      0.978     1.000     0.989       930
           B      0.974     1.000     0.987       930
           C      1.000     1.000     1.000       930
           D      1.000     1.000     1.000       930
           E      1.000     0.974     0.987       930
           F      1.000     1.000     1.000       930
           I      1.000     1.000     1.000       930
           K      1.000     1.000     1.000       930
           L      1.000     1.000     1.000       930
           O      1.000     1.000     1.000       930
           R      1.000     1.000     1.000       930
           T      1.000     0.973     0.986       930
           U      1.000     1.000     1.000       930
           V      1.000     1.000     1.000       930
           W      1.000     1.000     1.000       930
           X      1.000     1.000     1.000       930
           Y      0.997     1.000     0.998       930

    accuracy                          0.997     15810
   macro avg      0.997     0.997     0.997     15810
weighted avg      0.997     0.997     0.997     15810

```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
        A    B    C    D    E    F    I    K    L    O    R    T    U    V    W    X    Y
   A  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   B    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   C    0    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   D    0    0    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0
   E   21    0    0    0  906    0    0    0    0    0    0    0    0    0    0    0    3
   F    0    0    0    0    0  930    0    0    0    0    0    0    0    0    0    0    0
   I    0    0    0    0    0    0  930    0    0    0    0    0    0    0    0    0    0
   K    0    0    0    0    0    0    0  930    0    0    0    0    0    0    0    0    0
   L    0    0    0    0    0    0    0    0  930    0    0    0    0    0    0    0    0
   O    0    0    0    0    0    0    0    0    0  930    0    0    0    0    0    0    0
   R    0    0    0    0    0    0    0    0    0    0  930    0    0    0    0    0    0
   T    0   25    0    0    0    0    0    0    0    0    0  905    0    0    0    0    0
   U    0    0    0    0    0    0    0    0    0    0    0    0  930    0    0    0    0
   V    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0    0    0
   W    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0    0
   X    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0
   Y    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930
```
</details>

## Validación cruzada (5 pliegues por grupo): muestras de LSC70 (70 personas), personas no vistas

| Métrica | Valor |
|---|---|
| Muestras de prueba | 7036 |
| Exactitud (todas las predicciones) | 88.5% |
| F1 macro | 0.886 |
| Cobertura con confianza ≥ 0.80 (lo que la app escribe) | 69.3% |
| Exactitud de las predicciones con confianza ≥ 0.80 | 98.4% |

<details><summary>Reporte por letra</summary>

```
              precision    recall  f1-score   support

           A      0.922     0.940     0.931       415
           B      0.929     0.934     0.932       394
           C      0.818     0.828     0.823       413
           D      0.936     0.880     0.907       400
           E      0.800     0.744     0.771       398
           F      0.867     0.842     0.854       418
           I      0.760     0.890     0.820       420
           K      0.926     0.933     0.930       417
           L      0.881     0.864     0.873       420
           O      0.861     0.937     0.897       410
           R      0.864     0.862     0.863       419
           T      0.926     0.935     0.930       414
           U      0.915     0.900     0.908       420
           V      0.951     0.926     0.938       420
           W      0.972     0.916     0.943       419
           X      0.878     0.888     0.883       420
           Y      0.872     0.831     0.851       419

    accuracy                          0.885      7036
   macro avg      0.887     0.885     0.886      7036
weighted avg      0.887     0.885     0.886      7036

```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
        A    B    C    D    E    F    I    K    L    O    R    T    U    V    W    X    Y
   A  390    0    1    0    3    0    7    0    0    0    0    1    0    0    0    0   13
   B    3  368    3    0    1    0   10    0    0    1    1    7    0    0    0    0    0
   C    0    2  342    1   54    0    1    0    0   13    0    0    0    0    0    0    0
   D    0    4    3  352    2    5   11    0    3    9    3    0    3    0    0    5    0
   E    0    0   58    1  296    0    5    1    0   33    0    2    2    0    0    0    0
   F    2    0    0    1    0  352    4    0   44    0    2    0    0    0    0   13    0
   I    0    4    0    0    0    0  374    2    0    2    0    0    6    0    0    1   31
   K    0    0    0    2    0    2    0  389    0    2   10    0    0    0    0   12    0
   L    0    1    1    1    0   31    7    0  363    0    5    0    0    1    1    9    0
   O    0    0   10    1   12    0    1    0    0  384    0    0    0    0    0    1    1
   R    5    7    0    0    0   11    8    5    1    0  361    0    1   13    1    5    1
   T    4    6    0    0    0    0    5    0    0    0    5  387    1    2    3    1    0
   U    0    2    0    0    0    1   24    0    1    1    2    1  378    0    0    5    5
   V    0    0    0    0    0    2    5    0    0    0   18    0    0  389    6    0    0
   W    2    2    0    0    2    2    5    0    0    0   10    8    0    4  384    0    0
   X    0    0    0   17    0    0    0   23    0    0    1    6    0    0    0  373    0
   Y   17    0    0    0    0    0   25    0    0    1    0    6   22    0    0    0  348
```
</details>

## Generalización: modelo SIN LSC70 (70 personas), probado con LSC70 (70 personas)

| Métrica | Valor |
|---|---|
| Muestras de prueba | 7036 |
| Exactitud (todas las predicciones) | 74.3% |
| F1 macro | 0.743 |
| Cobertura con confianza ≥ 0.80 (lo que la app escribe) | 34.2% |
| Exactitud de las predicciones con confianza ≥ 0.80 | 95.4% |

<details><summary>Reporte por letra</summary>

```
              precision    recall  f1-score   support

           A      0.777     0.913     0.839       415
           B      0.951     0.840     0.892       394
           C      0.706     0.772     0.738       413
           D      0.374     0.920     0.532       400
           E      0.729     0.520     0.607       398
           F      0.686     0.591     0.635       418
           I      0.902     0.852     0.876       420
           K      0.657     0.667     0.662       417
           L      0.729     0.724     0.726       420
           O      0.779     0.861     0.818       410
           R      0.709     0.675     0.692       419
           T      0.848     0.877     0.862       414
           U      0.945     0.895     0.919       420
           V      0.815     0.776     0.795       420
           W      0.953     0.866     0.907       419
           X      0.824     0.257     0.392       420
           Y      0.894     0.625     0.736       419

    accuracy                          0.743      7036
   macro avg      0.781     0.743     0.743      7036
weighted avg      0.782     0.743     0.743      7036

```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
        A    B    C    D    E    F    I    K    L    O    R    T    U    V    W    X    Y
   A  379    0    1    0   22    0    0    8    0    0    0    0    0    0    0    5    0
   B    3  331    0    0    2    0    0   14    0    1    0   30    0    0   13    0    0
   C    0    9  319   27   33    0    0    1    0   23    0    1    0    0    0    0    0
   D    0    0    6  368    1    1    8    4    0    9    0    0    3    0    0    0    0
   E    0    0   86   42  207    0    0   10    0   53    0    0    0    0    0    0    0
   F    2    0    0   66    0  247    0    4   92    0    1    0    0    0    0    6    0
   I    5    4    0    0    1    0  358   18    0    2    0    0    1    0    0    0   31
   K    0    0    0   85    0   51    0  278    0    3    0    0    0    0    0    0    0
   L    0    1    0   68    4   28    0    7  304    0    5    0    0    2    1    0    0
   O    0    0   40    6    7    0    1    3    0  353    0    0    0    0    0    0    0
   R    1    0    0   39    1    7    0   12    3    0  283   13    0   58    0    2    0
   T    5    3    0    3    0    6    0   14    0    1   17  363    0    2    0    0    0
   U    0    0    0   10    1    1   11    7   12    0    0    1  376    1    0    0    0
   V    0    0    0    1    0    1    0    5    0    0   74    4    0  326    4    5    0
   W    1    0    0    2    2    1    0    8    0    0   19   10    0   11  363    2    0
   X    0    0    0  267    0   15    0   23    0    7    0    0    0    0    0  108    0
   Y   92    0    0    0    3    2   19    7    6    1    0    6   18    0    0    3  262
```
</details>
