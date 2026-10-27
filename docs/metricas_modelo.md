# Métricas del modelo de letras

Generado por `scripts/entrenar_modelo.py` el 2026-10-27T11:38:03.

- Clasificador: Random Forest (150 árboles, scikit-learn 1.9.1)
- Letras (20): A B C D E F I K L M N O P R T U V W X Y
- Muestras: 24074 (JuanPlazas (1 persona): 15810, LSC70 (70 personas): 8264)
- Aumento de datos: 3 copias rotadas ±15° con ruido gaussiano (solo en entrenamiento)
- Tiempo de inferencia: 4.27 ms por cuadro

La cifra que representa el uso real es la de **LSC70 con personas no vistas**: el dataset de
JuanPlazas es de una sola persona, así que su validación cruzada es optimista.

## Validación cruzada (5 pliegues por grupo): muestras de JuanPlazas (1 persona), grupos no vistos

| Métrica | Valor |
|---|---|
| Muestras de prueba | 15810 |
| Exactitud (todas las predicciones) | 99.8% |
| F1 macro | 0.998 |
| Cobertura con confianza ≥ 0.60 (lo que la app escribe) | 99.7% |
| Exactitud de las predicciones con confianza ≥ 0.60 | 100.0% |

<details><summary>Reporte por letra</summary>

```
              precision    recall  f1-score   support

           A      0.985     1.000     0.993       930
           B      0.974     1.000     0.987       930
           C      1.000     1.000     1.000       930
           D      1.000     1.000     1.000       930
           E      1.000     0.985     0.992       930
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
           Y      1.000     1.000     1.000       930

    accuracy                          0.998     15810
   macro avg      0.998     0.998     0.998     15810
weighted avg      0.998     0.998     0.998     15810

```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
        A    B    C    D    E    F    I    K    L    M    N    O    P    R    T    U    V    W    X    Y
   A  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   B    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   C    0    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   D    0    0    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   E   14    0    0    0  916    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   F    0    0    0    0    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   I    0    0    0    0    0    0  930    0    0    0    0    0    0    0    0    0    0    0    0    0
   K    0    0    0    0    0    0    0  930    0    0    0    0    0    0    0    0    0    0    0    0
   L    0    0    0    0    0    0    0    0  930    0    0    0    0    0    0    0    0    0    0    0
   M    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   N    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   O    0    0    0    0    0    0    0    0    0    0    0  930    0    0    0    0    0    0    0    0
   P    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0
   R    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0    0    0    0    0    0
   T    0   25    0    0    0    0    0    0    0    0    0    0    0    0  905    0    0    0    0    0
   U    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0    0    0    0
   V    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0    0    0
   W    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0    0
   X    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930    0
   Y    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0    0  930
```
</details>

## Validación cruzada (5 pliegues por grupo): muestras de LSC70 (70 personas), personas no vistas

| Métrica | Valor |
|---|---|
| Muestras de prueba | 8264 |
| Exactitud (todas las predicciones) | 88.2% |
| F1 macro | 0.882 |
| Cobertura con confianza ≥ 0.60 (lo que la app escribe) | 84.8% |
| Exactitud de las predicciones con confianza ≥ 0.60 | 96.1% |

<details><summary>Reporte por letra</summary>

```
              precision    recall  f1-score   support

           A      0.927     0.949     0.938       415
           B      0.941     0.937     0.939       394
           C      0.813     0.833     0.823       413
           D      0.915     0.882     0.898       400
           E      0.778     0.731     0.754       398
           F      0.860     0.840     0.850       418
           I      0.831     0.876     0.853       420
           K      0.919     0.950     0.934       417
           L      0.870     0.860     0.865       420
           M      0.875     0.930     0.901       413
           N      0.908     0.910     0.909       413
           O      0.829     0.920     0.872       410
           P      0.795     0.818     0.806       402
           R      0.870     0.862     0.866       419
           T      0.944     0.930     0.937       414
           U      0.923     0.912     0.917       420
           V      0.946     0.919     0.932       420
           W      0.958     0.916     0.937       419
           X      0.873     0.855     0.864       420
           Y      0.881     0.814     0.846       419

    accuracy                          0.882      8264
   macro avg      0.883     0.882     0.882      8264
weighted avg      0.883     0.882     0.882      8264

```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
        A    B    C    D    E    F    I    K    L    M    N    O    P    R    T    U    V    W    X    Y
   A  394    0    1    0    4    0    2    0    0    1    0    0    5    1    0    0    0    0    0    7
   B    3  369    3    0    1    0    0    0    0    6    0    1    8    1    2    0    0    0    0    0
   C    0    2  344    1   58    0    0    0    0    0    0    7    1    0    0    0    0    0    0    0
   D    0    0    3  353    1    4   11    0    4    0    0   11    1    0    1    3    0    0    8    0
   E    0    0   57    1  291    0    3    1    0    3    0   39    1    0    2    0    0    0    0    0
   F    2    0    0    1    0  351    0    0   46    0    0    0    4    2    0    0    0    0   12    0
   I    0    2    1    0    0    0  368    0    0    0    0    2    5    1    0    2    0    0    1   38
   K    0    0    0    1    0    2    0  396    0    0    0    3    1    4    0    0    0    6    4    0
   L    0    1    1    1    0   33    1    0  361    1    0    0    5    5    0    0    1    1    9    0
   M    0    0    0    0    0    0    4    0    0  384   15    0    8    1    0    0    0    0    1    0
   N    0    2    0    0    0    0    0    0    0   19  376    0   15    0    1    0    0    0    0    0
   O    0    0   11    1   16    0    1    0    0    0    0  377    3    0    0    0    0    0    1    0
   P    0    1    0    1    1    0    4   11    0   18   18   13  329    1    0    0    0    1    4    0
   R    0    7    0    1    0   11    2    0    2    6    1    1    2  361    0    3   15    2    5    0
   T    4    6    1    0    0    0    1    0    0    0    2    0    5    4  385    1    2    1    2    0
   U    0    0    1    0    0    1   20    0    1    0    1    1    2    2    2  383    0    0    5    1
   V    0    0    0    0    0    2    2    0    0    0    0    0    3   21    0    0  386    6    0    0
   W    1    2    0    0    2    2    1    1    0    0    0    0    7    8    7    0    4  384    0    0
   X    0    0    0   25    0    2    0   22    1    0    0    0    5    2    1    3    0    0  359    0
   Y   21    0    0    0    0    0   23    0    0    1    1    0    4    1    7   20    0    0    0  341
```
</details>

## Generalización: modelo SIN LSC70 (70 personas), probado con LSC70 (70 personas)

| Métrica | Valor |
|---|---|
| Muestras de prueba | 8264 |
| Exactitud (todas las predicciones) | 34.6% |
| F1 macro | 0.315 |
| Cobertura con confianza ≥ 0.60 (lo que la app escribe) | 54.8% |
| Exactitud de las predicciones con confianza ≥ 0.60 | 44.9% |

<details><summary>Reporte por letra</summary>

```
              precision    recall  f1-score   support

           A      0.776     0.918     0.841       415
           B      0.941     0.850     0.893       394
           C      0.693     0.804     0.744       413
           D      0.364     0.922     0.522       400
           E      0.730     0.495     0.590       398
           F      0.747     0.600     0.666       418
           I      0.914     0.833     0.872       420
           K      0.170     0.667     0.270       417
           L      0.759     0.729     0.744       420
           M      0.000     0.000     0.000       413
           N      0.000     0.000     0.000       413
           O      0.000     0.000     0.000       410
           P      0.000     0.000     0.000       402
           R      0.140     0.129     0.134       419
           T      0.005     0.005     0.005       414
           U      0.022     0.007     0.011       420
           V      0.000     0.000     0.000       420
           W      0.000     0.000     0.000       419
           X      0.000     0.000     0.000       420
           Y      0.000     0.000     0.000       419

    accuracy                          0.346      8264
   macro avg      0.313     0.348     0.315      8264
weighted avg      0.311     0.346     0.313      8264

```
</details>

<details><summary>Matriz de confusión (filas = real, columnas = predicha)</summary>

```
        A    B    C    D    E    F    I    K    L    M    N    O    P    R    T    U    V    W    X    Y
   A  381    0    1    0   19    0    0    9    0    0    0    0    0    0    0    5    0    0    0    0
   B    3  335    2    1    1    0    0   14    0    1    0   36    0    0    1    0    0    0    0    0
   C    0    3  332   25   27    0    0    1    0   19    0    6    0    0    0    0    0    0    0    0
   D    0    0    6  369    1    0    8    4    0    9    0    0    3    0    0    0    0    0    0    0
   E    0    0   96   39  197    0    0   10    0   56    0    0    0    0    0    0    0    0    0    0
   F    2    0    0   68    0  251    0    4   86    0    1    0    0    0    0    6    0    0    0    0
   I    3    4    0    0    1    0  350   18    0    3    0    0    1    0    0    1   39    0    0    0
   K    0    0    0  119    0   17    0  278    0    3    0    0    0    0    0    0    0    0    0    0
   L    0    2    0   61    8   29    0    7  306    0    2    0    0    4    1    0    0    0    0    0
   M    0    0    0    0    0    0    0  413    0    0    0    0    0    0    0    0    0    0    0    0
   N    0    2    0    0    0    0    0  411    0    0    0    0    0    0    0    0    0    0    0    0
   O    0    0   33    6    5    0    2    6    0  358    0    0    0    0    0    0    0    0    0    0
   P    0    0    8    0    0    0    0  391    0    3    0    0    0    0    0    0    0    0    0    0
   R    1    4    0   39    1    8    0   12    0    0  283    9    0   54    0    8    0    0    0    0
   T    5    5    0    4    0    9    0   12    0    0   14  360    0    2    2    1    0    0    0    0
   U    0    0    1    8    2    3    9    7    5    0    0    1  380    1    0    3    0    0    0    0
   V    0    0    0    1    0    3    0    5    0    0   87    0    0  314    6    4    0    0    0    0
   W    0    0    0    2    2    1    0    8    0    2   12    8    0   10  372    2    0    0    0    0
   X    0    0    0  273    0   13    0   23    0    7    0    0    0    0    0  104    0    0    0    0
   Y   96    1    0    0    6    2   14    7    6    1    0    4   18    0    0    2  262    0    0    0
```
</details>
