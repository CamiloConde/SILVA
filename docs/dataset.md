# Dataset y alcance de letras

## Fuente externa

El modelo se entrena con el dataset público de landmarks de la Lengua de Señas Colombiana (LSC) publicado por JuanPlazas (2026):

> JuanPlazas. (2026). *deteccion_letras_senas: Detección de letras en Lengua de Señas Colombiana (LSC)* [Repositorio de software y dataset]. GitHub. https://github.com/JuanPlazas/deteccion_letras_senas

El autor declara en `CERTIFICATE.md` que lo publica como código abierto y permite su uso, copia y modificación con fines educativos, académicos, de investigación o de desarrollo, **siempre que se cite la autoría**. El repositorio no tiene un archivo de licencia formal (MIT, Apache, etc.); si el proyecto se distribuye fuera del ámbito académico, conviene confirmar con el autor.

**Formato original:** 27 letras (A–Z + Ñ), 31 secuencias por letra (32 en la Ñ), cada secuencia de 30 cuadros × 42 valores (21 landmarks × x, y), normalizados con la muñeca como origen, el eje x espejado para la mano izquierda y escalados por la distancia muñeca–nudillo medio. SILVA usa **exactamente la misma normalización** (`silva.detector_manos.normalizar_landmarks`), verificado en `tests/test_detector_manos.py`.

**Conversión:** `scripts/preparar_dataset.py` toma cada cuadro de cada secuencia de las letras estáticas como una muestra independiente → 15 810 muestras de 17 letras (527 secuencias), guardadas en `data/landmarks/externo_juanplazas.npz`.

## Por qué al principio solo 17 letras (hasta la versión 1.2)

> Desde la versión 1.3 SILVA reconoce las 27 letras: ver [Versión 1.3](#versión-13-las-27-letras-seguimiento-y-teléfono) al final.

En LSC varias letras del alfabeto dactilológico se hacen con movimiento. Se midió el desplazamiento medio de los landmarks entre cuadros consecutivos de cada letra en el dataset:

| Grupo | Letras | Movimiento medio por cuadro |
|---|---|---|
| Estáticas (incluidas en el MVP) | A B C D E F I K L O R T U V W X Y | 0,11 – 0,29 |
| Dinámicas (fuera de alcance) | G H J M N Ñ P Q S Z | 1,12 – 4,40 |

La separación es clara (un orden de magnitud), y coincide con lo declarado fuera de alcance en el planteamiento ("reconocimiento de señas dinámicas"). Un clasificador cuadro a cuadro como Random Forest no puede distinguir letras que dependen de la trayectoria; reconocerlas requiere un modelo que vea la secuencia, que es lo que agregó la versión 1.3.

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
   - El umbral se elige para que lo escrito solo acierte ≥ 95 % y escriba a lo sumo un 15 % de señas ajenas; hoy es 0,20.
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


---

# Versión 1.3: las 27 letras, seguimiento y teléfono

## Letras M, N y P: al modelo de letras quietas

En LSC70 la mano de la M, la N y la P casi no se mueve entre las 6 imágenes de cada seña (a diferencia de lo medido en el dataset de JuanPlazas). Por eso se agregaron al modelo cuadro a cuadro, que pasó de 17 a 20 letras. Con personas no vistas de LSC70 acierta el 88,2 % (con 17 letras: 88,5 %).

## Letras G, H, J, Ñ, Q, S y Z: modelo de trazo

`scripts/preparar_lsc70_secuencias.py` guarda, para cada seña de LSC70, los puntos de la mano en sus 6 imágenes, más la posición y el tamaño de la mano en la imagen: 1 851 señas de 70 personas (`data/landmarks/lsc70_secuencias.npz`).

1. **Segmentación en vivo** (`silva.letras_movimiento`): el trazo empieza cuando la muñeca se mueve más de 0,08 tamaños de mano por cuadro y termina tras 4 cuadros quieta (menos de 0,04). Si llega a 75 cuadros se cierra ahí; los de menos de 6 cuadros se descartan.
2. **Vector fijo:** el trazo se remuestrea a 6 cuadros, como en LSC70: la forma de la mano en cada cuadro, la trayectoria de la muñeca respecto al inicio, y el recorrido total y el desplazamiento neto: 264 valores.
3. **Clasificación:** Extra Trees de 200 árboles con las 27 letras como clases, aumentado con rotación, escala, recorte temporal y ruido. Solo se escriben G, H, J, Ñ, Q, S o Z; si gana una letra quieta, el trazo se ignora.
4. **Regla del recorrido:** la muñeca debe recorrer al menos 0,4 tamaños de mano. Lo cumple el 90 % de las letras con trazo de LSC70; la mediana de las letras quietas está entre 0,1 y 0,35.
5. **Umbral 0,4:** escribe el 58 % de las letras con trazo, con 96 % de acierto. Para medir letras falsas se armaron 2 800 pasos de una letra quieta a otra con imágenes de LSC70: en el 9 % sale una letra con trazo que nadie hizo.

Si una letra con trazo empieza con la forma de una quieta (la J empieza como la I), la quieta puede alcanzar a escribirse; el trazo la reemplaza si llega dentro de 0,6 s.

**Límite:** LSC70 no trae video, así que la segmentación en vivo (cuándo empieza y termina el trazo) no se pudo medir con datos; se ajusta con la cámara.

Detalle: [metricas_letras_movimiento.md](metricas_letras_movimiento.md).

## Umbral de las letras quietas: de 0,80 a 0,60

Con personas no vistas de LSC70, la regla de 0,80 solo escribía el 70 % de las señas. Con manos que el modelo no conoce, como las de quien prueba la app por primera vez, muchas letras no llegaban nunca. Con 0,60 (y los mismos 5 cuadros estables):

| Umbral | Señas que escribe | Acierto de lo escrito |
|---|---|---|
| 0,80 | 70,2 % | 98,5 % |
| **0,60** | **84,8 %** | **96,1 %** |

## Seguimiento de la mano y fluidez en modo Palabras

- **Recuperación de la mano perdida:** cuando MediaPipe no encuentra una mano que no está en reposo, se busca de nuevo en un recorte cuadrado de 1,8 anchos de hombro alrededor de la muñeca de la pose, ampliado a 256 px. Se descarta si queda lejos de esa muñeca o si es la otra mano otra vez. En 40 videos de LSC-54, la mano que hace la seña pasa de detectarse en el **70 % al 81 %** de los cuadros.
- **Fluidez:** la cámara a 1280×720 solo entregaba 10 cuadros por segundo. Ahora pide 640×360, la misma vista a 30 cuadros por segundo, y la pose y las manos se calculan en paralelo: 19 ms por cuadro en vez de 29.
- **Modelo reentrenado:** LSC-54 se volvió a extraer con la recuperación, para que entrenamiento y uso vean lo mismo. Con personas no vistas acierta el 85,3 % y escribe solo el 56 % de las señas con 95,7 % de acierto (v1.2: 53 % con 96,3 %). Ver [metricas_palabras.md](metricas_palabras.md).

## La app de Android

El teléfono usa los mismos clasificadores. `scripts/exportar_movil.py` los convierte a un formato binario propio (cabecera `SILVAARB` y los árboles en arreglos planos) que la app recorre en Kotlin, y genera casos de prueba con las características y probabilidades que calcula Python. Las 12 pruebas de Kotlin comprueban que el teléfono da los mismos números.

**El teléfono en vertical:** el modelo de letras depende de la proporción de la imagen (se entrenó con imágenes 4:3 horizontales), así que en vertical las coordenadas de la mano se corrigen para que el modelo vea la misma geometría; una prueba comprueba que la misma mano da los mismos valores en ambos sentidos. En Palabras, los brazos tienen que caber a lo ancho, así que la guía de encuadre usa rangos propios: los hombros deben ocupar entre el 22 % y el 40 % del ancho.

**Prueba con videos conocidos:** se pasaron 12 videos de LSC-54 por la app en el emulador, por el mismo camino que la cámara (MediaPipe para Android, conversión de imagen, detección y clasificación):

| Prueba | Resultado |
|---|---|
| Palabras, imagen horizontal | 8 escritas, 1 como «¿Quisiste decir?», 3 rechazadas: igual que la app de PC |
| Palabras, recorte vertical | 6 escritas, 4 como «¿Quisiste decir?» |
| Deletreo, 42 letras (umbral 0,80 → 0,60) | De 24 a 31 escritas, con 1 error |

En vertical la persona se ve más pequeña. En una prueba en Python con videos de LSC-54, la app escribió el 80 % de las señas con la imagen completa, el 68 % con el recorte vertical y el 77 % con el recorte vertical y la persona más lejos. Por eso se recomienda apoyar el teléfono a 1,5–2 m.

## El segmentador de Palabras mide en segundos

El segmentador decidía cuándo empieza y termina una seña contando cuadros, con valores calibrados en el video a 30 cuadros/s de LSC-54. En el teléfono la app procesa 10-20 cuadros/s, así que una seña tenía que durar el doble para contar y la pausa final también se alargaba al doble. Ahora mide en segundos: a 30 cuadros/s corta igual que antes (13 de 2 880 videos se corren un cuadro) y a menos cuadros/s ya no pierde señas.

`scripts/evaluar_fps.py` simula la cámara en vivo con los videos de 18 personas de LSC-54 que el modelo no vio (3 pliegues; cada modelo se entrena sin 6 personas, por eso las cifras absolutas son menores que en `metricas_palabras.md`):

| Cuadros/s | Segmentador | Escrita bien | Escrita mal | «¿Quisiste decir?» | No detectada | Palabras falsas (señas ajenas) |
|---|---|---|---|---|---|---|
| 30 | por cuadros (1.3.0) | 43,6 % | 1,3 % | 18,2 % | 36,9 % | 0,1 % |
| 30 | por segundos | 43,6 % | 1,3 % | 18,2 % | 36,9 % | 0,1 % |
| 15 | por cuadros (1.3.0) | 36,6 % | 0,6 % | 20,1 % | 42,7 % | 0,0 % |
| 15 | por segundos | **43,8 %** | 1,3 % | 18,8 % | 36,1 % | 0,3 % |
| 10 | por cuadros (1.3.0) | 28,6 % | 0,7 % | 16,9 % | 53,8 % | 0,0 % |
| 10 | por segundos | **40,7 %** | 1,8 % | 18,7 % | 38,7 % | 0,1 % |
| 7,5 | por cuadros (1.3.0) | 17,5 % | 0,3 % | 12,4 % | 69,7 % | 0,0 % |
| 7,5 | por segundos | **37,8 %** | 1,4 % | 19,6 % | 41,2 % | 0,3 % |

1 198 videos del vocabulario y 792 de señas ajenas (colores y números). A 15 cuadros/s, la velocidad de un teléfono como el Galaxy A35, la app ahora escribe tantas señas como a 30.
