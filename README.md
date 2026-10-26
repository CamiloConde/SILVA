# SILVA

**Sistema Inteligente de Lenguaje Visual Aumentado** · versión 1.2.0

SILVA es una aplicación de escritorio que traduce a texto, en tiempo real, señas de la Lengua de Señas Colombiana (LSC) captadas con una cámara web. También permite que la persona oyente responda por escrito. Todo se procesa en el equipo: no necesita internet ni envía video a ningún servidor.

Equipo 3, Ingeniería de Software (grupo 1206), Universidad Tecnológica de Bolívar: Miguel Alejandro Jácome Yánez, Camilo Andrés Conde Corrales y Juan Diego Rosales Guillén. Docente: Aisner José Marrugo Juliao.

![SILVA en modo Palabras](docs/capturas/figura_4_palabras.png)

## Descargar y usar (sin instalar nada)

1. En [Releases](https://github.com/CamiloConde/SILVA/releases) descargue `SILVA-v1.2.0-windows.zip` (unos 280 MB).
2. Descomprímalo completo y abra `SILVA\SILVA.exe`.
   - Si Windows muestra «Windows protegió su PC», elija *Más información → Ejecutar de todas formas*. Aparece porque el ejecutable no está firmado digitalmente.
3. Presione **Iniciar** (o Enter).

Requisitos: Windows 10/11 de 64 bits, cámara web, 8 GB de RAM recomendados. El historial se guarda en `%LOCALAPPDATA%\SILVA\historial.db`.

Para comprobar una instalación: `SILVA.exe --verificar --camara` crea un informe en `%LOCALAPPDATA%\SILVA\verificacion.txt`.

## Qué hace

| Modo | Qué reconoce | Cómo se usa |
|---|---|---|
| **Deletreo** | 17 letras estáticas del alfabeto dactilológico: A B C D E F I K L O R T U V W X Y | Sostenga la seña hasta que se llene la barra de estabilidad (confianza ≥ 0,80 durante 5 cuadros) |
| **Palabras** | 33 expresiones de cortesía con movimiento: Apoyar, Ayudar, Baño, Bien, Bienvenido, Buenas noches, Buenas tardes, Buenos días, Chao, ¿Cómo está?, Con gusto, De nada, Esperar, Excelente, Gracias, Hola, Invitar, Lo siento, Mal, Más o menos, Muchas gracias, Muy bien, Muy mal, Necesitar, No, Perdón, Perfecto, Permiso, Por favor, Presentar, Sentarse, Sí, Tranquilo | Deben verse los hombros y las manos. Empiece con las manos abajo, haga la seña y vuelva a bajarlas |
| **Responder** (Ctrl+R) | — | La persona oyente escribe su respuesta y se muestra en grande sobre el video para que la persona sorda la lea |

Además:
- Muestra la confianza de cada predicción.
- Avisa cuando no detecta la mano o a la persona, y cuando hay **poca luz** (con poca luz los movimientos salen borrosos y se pierde la mano).
- Si MediaPipe pierde una mano a mitad de la seña, la dibuja en su posición aproximada (círculos huecos) usando el esqueleto del cuerpo.
- En modo Palabras, la palabra reconocida aparece primero como **provisional** (2,5 s) con sus 3 opciones más probables. Se puede confirmar (Espacio), cambiar (1, 2, 3) o descartar (X); si nadie hace nada, se escribe sola.
- Si la seña es dudosa, muestra **«¿Quiso decir…?»** con 3 opciones y no escribe nada salvo que alguien elija. Los movimientos que no son una de las 33 señas se ignoran.
- Guarda cada sesión y cada respuesta en un historial local.

**Precisión:**
- **Letras:** **88,5 % con personas que el modelo nunca vio** (70 personas de LSC70); con confianza ≥ 0,80 escribe el 69 % de las señas y acierta el 98,4 %. El modelo de la versión 1.1, entrenado con una sola persona, daba 74 % con personas nuevas.
- **Palabras:** 85,2 % con personas que el modelo nunca vio, y **77,1 % con personas grabadas en otro entorno** (LSC50; la versión 1.1 daba 32 %).
  - La app escribe sola el 53 % de las señas, con 96 % de acierto, y otro 20 % lo ofrece como «¿Quiso decir…?» (la correcta está entre las 3 opciones el 97 % de las veces).
  - Ante señas que no son del vocabulario escribe una palabra el 9 % de las veces (versión 1.0.0: 81 %), y queda provisional.

El detalle está en [docs/metricas_modelo.md](docs/metricas_modelo.md) y [docs/metricas_palabras.md](docs/metricas_palabras.md).

**Límites:**
- Reconoce señas sueltas de un vocabulario cerrado, no frases libres con la gramática de la LSC.
- Las letras con movimiento (G, H, J, M, N, Ñ, P, Q, S, Z) no están incluidas.

## Controles

| Control | Acción |
|---|---|
| **Iniciar / Detener** · Enter | Enciende o apaga la cámara. Al detener, la sesión se guarda en el historial |
| **Deletreo / Palabras** | Cambia de modo |
| **Espacio** · barra espaciadora | Separa palabras (modo Deletreo) |
| **Borrar** · Retroceso | Borra la última letra o palabra |
| **Limpiar** · Supr | Borra todo el texto |
| **1 · 2 · 3** (modo Palabras) | Cambiar la palabra provisional por esa opción, o elegirla en «¿Quiso decir…?» |
| **Espacio** (modo Palabras) / **X** | Confirmar ya la palabra provisional / descartarla |
| **Cámara 1–4** (encabezado) | Elegir la cámara, por ejemplo el celular como cámara web (con Enlace Móvil de Windows 11 o apps como DroidCam o Iriun) |
| **Responder** · Ctrl+R | Escribir una respuesta y mostrarla en grande. Para cerrarla: clic sobre el video o Esc |
| **Historial** | Sesiones traducidas y respuestas guardadas |

Para escribir la misma letra dos veces seguidas (por ejemplo "LL"), retire la mano del cuadro entre una y otra.

## Ejecutar desde el código fuente

Requiere **Python 3.10, 3.11 o 3.12** (MediaPipe no soporta versiones más nuevas).

```bash
git clone https://github.com/CamiloConde/SILVA
cd SILVA
python -m venv .venv
```

Active el entorno con `.venv\Scripts\activate` en Windows o `source .venv/bin/activate` en macOS/Linux, y luego:

```bash
pip install -r requirements.txt
pip install -e .
python -m silva
```

Los modelos ya vienen en `modelos/`, así que después de instalar la app funciona sin internet.

> **No actualice MediaPipe.** Está fijo en la versión 0.10.21 porque las versiones que publica Google desde la 0.10.22 envían estadísticas de uso a Google (`play.googleapis.com`) sin forma de desactivarlo ([issue #6291](https://github.com/google-ai-edge/mediapipe/issues/6291)). Eso incumpliría el requisito RNF-01. Con 0.10.21 se verificó con `netstat` que la app no abre ninguna conexión.

## Pruebas

```bash
python -m pytest -v
```

Son 63 pruebas automáticas:
- Regla de confirmación de letras y normalización de puntos.
- Detectores reales de MediaPipe y los dos clasificadores.
- Segmentación de señas con movimiento.
- Historial y respuestas.
- Controlador en ambos modos.
- Interfaz: ciclos Iniciar/Detener con el hilo de video, modos, edición, Responder e historial.
- Ejecución sin red y tiempo por cuadro.

El plan completo, con las pruebas manuales, está en [docs/pruebas.md](docs/pruebas.md).

## Construir el ejecutable

```bash
pip install pyinstaller
python scripts/construir_ejecutable.py
```

El script hace tres cosas:
1. Empaqueta con PyInstaller ([empaquetado/silva.spec](empaquetado/silva.spec)).
2. Verifica que el ejecutable cargue todos los modelos por sí solo.
3. Genera `dist/SILVA-v1.2.0-windows.zip`, que es el archivo que se sube a *Releases*.

Pasos para publicar:
1. En GitHub, entre a **Releases** y luego a **Draft a new release**.
2. Cree la etiqueta `v1.2.0`.
3. Adjunte el `.zip`.
4. Publique con **Publish release**.

## Reentrenar los modelos

**Letras:**

```bash
python scripts/preparar_dataset.py
python scripts/preparar_lsc70.py
python scripts/capturar_dataset.py --persona camilo
python scripts/entrenar_modelo.py
```

`preparar_dataset.py` descarga el dataset de una persona de JuanPlazas. `preparar_lsc70.py` extrae las letras de LSC70 (70 personas; requiere `LSC70.zip` de [Mendeley Data](https://doi.org/10.17632/9ssyn8tff5.2) en `data/externo/lsc70/`). `capturar_dataset.py` es opcional: sirve para grabar muestras propias.

**Palabras:** `data/landmarks/lsc54_secuencias.npz` y `lsc50_secuencias.npz` ya traen los puntos extraídos, así que basta con:

```bash
python scripts/entrenar_palabras.py
```

Para extraerlos de nuevo desde los videos:
1. Descargue los tres zips de `RawVideos` de [LSC-54](https://doi.org/10.57760/sciencedb.25639) (unos 970 MB) en `data/externo/lsc54/`.
2. Ejecute `python scripts/extraer_lsc54.py`. En un equipo de 16 núcleos tarda unos 30 minutos.

## Arquitectura

```
Cámara ─► CapturaVideo ─► DetectorManos / DetectorCuerpo (MediaPipe) ─► Clasificador / ClasificadorPalabras
                                    │                                           │
                          (hilo de video: TrabajadorVideo)            BufferTexto / SegmentadorSenas
                                    │                                           │
                          VentanaPrincipal (PySide6) ◄──── ControladorSILVA ────► RepositorioHistorial (SQLite)
```

- La ventana usa **PySide6 (Qt)**. La cámara y MediaPipe corren en un hilo aparte, así la ventana nunca se congela; es el paralelismo de la Figura 6 del modelado UML.
- Los accesos al controlador desde los dos hilos se ordenan con un candado.
- Los diagramas actualizados están en [Planteamiento/SILVA_entrega_corte3.md](Planteamiento/SILVA_entrega_corte3.md).

```
SILVA/
├── Planteamiento/          # Entregas de los cortes 1, 2 y 3
├── src/silva/              # Código de la aplicación
│   ├── interfaz.py             VentanaPrincipal, TrabajadorVideo, DialogoRespuesta (PySide6)
│   ├── controlador.py          ControladorSILVA (modos Deletreo y Palabras)
│   ├── captura_video.py        CapturaVideo (OpenCV)
│   ├── detector_manos.py       DetectorManos (MediaPipe) + normalización de la mano
│   ├── cuerpo.py               DetectorCuerpo (pose + 2 manos) y características por cuadro
│   ├── palabras.py             SegmentadorSenas y ClasificadorPalabras
│   ├── clasificador.py         Clasificador / ClasificadorPreentrenado (letras)
│   ├── buffer_texto.py         BufferTexto (regla de 0,80 y 5 cuadros)
│   ├── repositorio_historial.py RepositorioHistorial (SQLite: sesiones, letras, respuestas)
│   ├── config.py               Rutas y constantes (también dentro del ejecutable)
│   └── modelo.py               Landmark, Mano, Prediccion
├── scripts/                # Preparar datos, extraer LSC-54, entrenar, construir el ejecutable
├── tests/                  # 51 pruebas con pytest
├── data/landmarks/         # Puntos extraídos de los datasets (.npz)
├── modelos/                # MediaPipe (manos, pose) y clasificadores (letras, palabras)
├── empaquetado/            # PyInstaller: especificación, lanzador y LEEME del ejecutable
├── recursos/               # Ícono
└── docs/                   # Datasets, métricas, plan de pruebas y capturas
```

## Créditos y licencias

- **Datos:** JuanPlazas (2026), letras de LSC (uso académico citando la autoría); Muñoz Galindez et al. (2024), LSC70 (CC BY 4.0); Mora-Zarate (2025), LSC-54 (**CC BY-NC 4.0**); y Flórez-Sierra et al. (2024), LSC50 (CC BY 4.0). Como el modelo de palabras se deriva de LSC-54, **SILVA no puede usarse con fines comerciales**.
- **Software:** MediaPipe (Apache 2.0), PySide6/Qt (LGPL v3), OpenCV (Apache 2.0), scikit-learn y NumPy (BSD).
- El detalle está en [TERCEROS.md](TERCEROS.md).
- El equipo aún no ha definido la licencia de su propio código.
