# Dataset y alcance de letras

## Fuente externa

El modelo se entrena con el dataset público de landmarks de la Lengua de Señas Colombiana (LSC) publicado por JuanPlazas (2026):

> JuanPlazas. (2026). *deteccion_letras_senas: Detección de letras en Lengua de Señas Colombiana (LSC)* [Repositorio de software y dataset]. GitHub. https://github.com/JuanPlazas/deteccion_letras_senas

El autor declara en `CERTIFICATE.md` que lo publica como código abierto y permite su uso, copia y modificación con fines educativos, académicos, de investigación o de desarrollo, **siempre que se cite la autoría**. El repositorio no tiene un archivo de licencia formal (MIT, Apache, etc.); si el proyecto se distribuye fuera del ámbito académico, conviene confirmar con el autor.

**Formato original:** 27 letras (A–Z + Ñ), 31 secuencias por letra (32 en la Ñ), cada secuencia de 30 cuadros × 42 valores (21 landmarks × x, y), normalizados con la muñeca como origen, el eje x espejado para la mano izquierda y escalados por la distancia muñeca–nudillo medio. SILVA usa **exactamente la misma normalización** (`silva.detector_manos.normalizar_landmarks`), verificado en `tests/test_detector_manos.py`.

**Conversión:** `scripts/preparar_dataset.py` toma cada cuadro de cada secuencia de las letras estáticas como una muestra independiente → 15 810 muestras de 17 letras (527 secuencias), guardadas en `data/landmarks/externo_juanplazas.npz`.

## Por qué solo 17 letras

En LSC varias letras del alfabeto dactilológico se hacen con movimiento. Se midió el desplazamiento medio de los landmarks entre cuadros consecutivos de cada letra en el dataset:

| Grupo | Letras | Movimiento medio por cuadro |
|---|---|---|
| Estáticas (incluidas en el MVP) | A B C D E F I K L O R T U V W X Y | 0,11 – 0,29 |
| Dinámicas (fuera de alcance) | G H J M N Ñ P Q S Z | 1,12 – 4,40 |

La separación es clara (un orden de magnitud), y coincide con lo declarado fuera de alcance en el planteamiento ("reconocimiento de señas dinámicas"). Un clasificador cuadro a cuadro como Random Forest no puede distinguir letras que dependen de la trayectoria; reconocerlas requeriría un modelo de secuencias (por ejemplo LSTM, como hace el proyecto de origen).

## Limitación conocida y cómo atenderla

Todas las secuencias externas parecen provenir de una sola persona y una sola cámara. La exactitud de 99,9 % en `docs/metricas_modelo.md` mide la generalización a **secuencias nuevas de la misma persona**, no a personas nuevas, así que es optimista.

Para medir y mejorar la generalización (objetivo específico 5), cada integrante debe grabar muestras propias:

```bash
python scripts/capturar_dataset.py --persona camilo
python scripts/entrenar_modelo.py
```

Con datos propios, `entrenar_modelo.py` agrega automáticamente una sección "Generalización" al reporte: entrena sin los datos de esa persona y los usa como prueba. Esa cifra es la que debe reportarse como precisión esperada con usuarios nuevos.

---

# Modo Palabras: dataset LSC-54

> Mora-Zarate, J. E. (2025). *A dataset representing the movements that a person must perform to produce a sign* (V4) [Conjunto de datos]. Science Data Bank. https://doi.org/10.57760/sciencedb.25639
>
> Artículo que lo describe: Mora-Zarate, J. E., Garzón-Castro, C. L. y Castellanos-Rivillas, J. A. *LSC-54: A landmark-based dataset for Colombian sign language*. https://pmc.ncbi.nlm.nih.gov/articles/PMC12557509/ (completar revista y año al citar en APA).

**Licencia:** CC BY-NC 4.0. Se puede usar con atribución y sin fines comerciales, lo cual es compatible con un proyecto académico. Si SILVA se distribuyera comercialmente, habría que reemplazar este dataset o pedir permiso.

**Contenido:** 54 señas de la lengua de señas colombiana (33 de cortesía, 11 colores y los números del 1 al 10), grabadas por 34 personas. Los videos son de 640×360 a 30 fps y las caras están difuminadas.

**Por qué se usaron los videos y no el JSON del dataset:** el `datos.json` pesa 51 GB porque cada video aparece 45 veces, desplazado en horizontal como aumento de datos. En su lugar se descargaron los tres zips de videos originales (970 MB, verificados con el MD5 publicado) y se les sacaron los puntos con **el mismo detector que usa la app en vivo** (`scripts/extraer_lsc54.py`). Así el modelo ve exactamente lo mismo al entrenar y al usarse. El resultado es `data/landmarks/lsc54_secuencias.npz`: 2 880 secuencias, una por video.

## Qué categorías se usan

| Categoría | Videos | Resultado | Decisión |
|---|---|---|---|
| Cortesía (33 señas, 18 personas) | 1 198 | 85,6 % con personas no vistas | **Incluida** |
| Cortesía + números | 1 770 | 77,3 %, y solo escribe el 69 % de las señas | No incluida |
| Colores | 1 110 | MediaPipe casi no detecta la mano: muchas señas se hacen junto a la cara | No incluida |

Los números del 1 al 10 son configuraciones de mano casi estáticas que se confunden entre sí cuando se mezclan con señas de movimiento.

## Características por cuadro (100 valores)

- **Pose (14):** nariz, hombros, codos y muñecas, en un sistema centrado entre los hombros y escalado por el ancho de hombros. No importa dónde esté la persona en la imagen ni a qué distancia.
- **Cada mano (43 × 2):** 21 puntos en ese mismo sistema, más un indicador de si la mano está presente. Las manos se asignan a izquierda o derecha por cercanía a las muñecas de la pose, no por la etiqueta de MediaPipe, que cambia si la imagen está espejada.

## De la secuencia a la predicción

1. **Segmentación:** una seña empieza cuando alguna muñeca sube por encima del nivel de reposo o se mueve, y termina tras 8 cuadros seguidos en reposo.
   - El nivel de reposo se calibró con el dataset: en reposo las muñecas están a unos 1,36 anchos de hombro por debajo de los hombros (percentil 5: 0,86), y durante la seña a unos 0,03. El corte está en 0,8.
   - Se usan también las muñecas de la pose porque MediaPipe a veces pierde la mano cerca de la cara, y sin ellas la seña se partía en dos.
2. **Relleno:** los cuadros donde la mano se perdió entre dos detecciones se interpolan.
3. **Vector fijo:** la seña se remuestrea a 20 cuadros, para que no importe si se hizo rápido o lento. Se toman las posiciones, las velocidades y la **forma de cada mano** respecto a su muñeca, en total 5 580 valores.
4. **Clasificación:** Extra Trees de 400 árboles. El entrenamiento se aumenta con versiones espejadas, que simulan a personas zurdas.
5. **Rechazo y umbral (versión 1.1):**
   - El modelo tiene una clase extra, **«otra cosa»**, aprendida con las señas de colores y números de LSC-54.
   - Una seña se escribe (provisional) si su probabilidad supera el umbral **y** a «otra cosa».
   - Si es dudosa, se ofrece como «¿Quiso decir…?».
   - El umbral se elige para que lo escrito solo acierte ≥ 95 % y escriba a lo sumo un 15 % de señas ajenas; hoy es 0,25.
   - Ver [metricas_palabras.md](metricas_palabras.md).

## Rechazo de movimientos ajenos (versión 1.1)

El modelo 1.0.0 solo conocía las 33 señas y siempre elegía una: con las 1 671 señas ajenas de LSC-54 escribía una palabra en el **81 %** de los casos («Chao», «Bien», «No», «Hola»…).

Para que la evaluación sea honesta, se entrena con una categoría como «otra cosa» y se mide con la otra, nunca vista. Resultados con umbral 0,20:

| «Otra cosa» de entrenamiento | Se prueba con | Palabras falsas | Señas reales escritas (acierto) |
|---|---|---|---|
| Números | Colores | 23 % | 72 % (94 %) |
| Colores | Números | 4 % | 68 % (94 %) |

El modelo final aprende con ambas categorías. Ante gestos cotidianos (rascarse, acomodarse el pelo) no hay datos para medirlo; grabar algunos y agregarlos como «otra cosa» es la mejora más directa.

## Por qué Extra Trees

Se compararon cuatro clasificadores y tres conjuntos de características, siempre evaluando con personas no vistas (GroupKFold de 6 pliegues por persona):

| Características | Extra Trees | Regresión logística | SVM | Perceptrón multicapa |
|---|---|---|---|---|
| Posición + velocidad | 70,4 % | 61,8 % | 61,3 % | 60,0 % |
| + forma de las manos | 82,9 % | 69,7 % | 70,3 % | 70,6 % |
| + relleno de huecos | **84,3 %** | 71,4 % | 71,6 % | 71,2 % |

## Limitaciones

- Reconoce señas sueltas de un vocabulario cerrado de 33 expresiones, no frases libres con la gramática de la LSC.
- Las confusiones más frecuentes son entre señas parecidas, como *Buenas noches* y *Buenos días*, o *Chao* y *Hola*.
- Las personas del dataset estaban de pie, de frente y con fondo claro. Con una cámara de portátil y la persona sentada, deben verse los hombros y las manos; eso hay que probarlo con la cámara real (PR-27).


---

# Versión 1.2: más personas (LSC70 y LSC50)

## Letras: LSC70 (70 personas)

> Muñoz Galindez, J. A., Villota Coral, L. V. y Vargas-Cañas, R. (2024). *Speak in Colombian Sign Language: A Dynamic LSC70 Database* (V2) [Conjunto de datos]. Mendeley Data. https://doi.org/10.17632/9ssyn8tff5.2 — CC BY 4.0. Artículo: *Data in Brief, 58*, 111213.

LSC70 trae 6 imágenes de 640×480 por seña, grabadas con celular, con luz y ropa variables, para 70 personas. `scripts/preparar_lsc70.py` toma las 17 letras estáticas y detecta la mano con el mismo modelo y la misma normalización de la app. Resultado: 7 036 muestras (104 imágenes sin mano detectada).

| Modelo de letras | Exactitud con personas nuevas (LSC70) | Escribe (confianza ≥ 0,80) | Acierto de lo escrito |
|---|---|---|---|
| v1.1: solo JuanPlazas (1 persona) | 74,3 % | 34 % | 95 % |
| **v1.2: + LSC70** (validación cruzada por persona) | **88,5 %** | **69 %** | **98,4 %** |

Las letras más afectadas en la v1.1 eran X (25 %), E (50 %) e Y (57 %). El 99,9 % reportado antes medía secuencias nuevas de la misma única persona.

## Palabras: LSC50 (5 personas, otro entorno)

> Flórez-Sierra et al. (2024). LSC50: Colombian Sign Language Video and Inertial Measurement dataset. *Scientific Data, 11*, 1347. Datos: figshare, CC BY 4.0.

LSC50 tiene 50 señas × 5 personas × 4 repeticiones, en video de cuerpo entero a 1920×1080, con puntos de MediaPipe Holistic ya extraídos. `scripts/preparar_lsc50.py` los convierte con la misma función de características de la app. 14 de sus señas coinciden con el vocabulario de SILVA.

**Hallazgo:** con las personas de LSC50, el modelo de la v1.1 acertaba solo el **32 %** de esas 14 señas. Con personas de LSC-54 acertaba el 85 %. El modelo estaba sobreajustado al entorno de grabación de LSC-54. Algunas señas (*Permiso*, *Con gusto*) parecen hacerse distinto en LSC50, ya sea por variantes regionales o de estilo.

| Variante | Señas | Exactitud con personas nuevas | Con personas de LSC50 | Escribe sola (acierto) |
|---|---|---|---|---|
| Sin LSC50 | 33 | 86,1 % | ~32 % | 69 % (96 %) |
| **33 + LSC50 (elegida)** | 33 | 85,2 % | **77,1 %** (entre 3: 91,8 %) | 53 % (96,3 %) |
| Ampliado con las 36 señas nuevas de LSC50 | 69 | 74,5 % | 61,5 % | 44 % (95,9 %) |

Se eligió **33 + LSC50**. Las otras 36 señas de LSC50 se usan como «otra cosa» (rechazo). El vocabulario ampliado se descartó por ahora: con solo 5 personas por seña nueva, la exactitud general cae 11 puntos.

## Seguimiento de la mano

En 4 512 cuadros de seña de LSC-54, MediaPipe detecta la mano:
- en el 84,9 % de los cuadros con un umbral de 0,6;
- en el 87,2 % con un umbral de 0,4;
- en una proporción casi igual con la imagen a la mitad de resolución, así que la resolución no es la causa.

El 12–15 % restante se pierde por desenfoque, por la mano frente a la cara o por las manos cruzadas. En la v1.2:
- **Umbral:** se usa 0,4 en modo Palabras, también al extraer LSC-54 para entrenar.
- **Mano aproximada:** se dibuja la mano que estima el esqueleto cuando la detección se pierde.
- **Aviso de poca luz:** con poca luz la cámara alarga la exposición y los movimientos salen borrosos.
