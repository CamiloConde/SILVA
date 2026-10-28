# Plan y registro de pruebas (sección 10.3 de la plantilla)

## Pruebas automáticas

Se ejecutan con `python -m pytest -v`. Resultado de la última ejecución (27/10/2026, Windows 11, Python 3.12.10): **91 de 91 aprobadas**, más 12 de 12 de la app de Android (`movil\gradlew.bat -p movil testDebugUnitTest`).

Las tablas registran cada prueba en la versión en que se agregó. En la versión 1.3 el umbral de letras bajó de 0,80 a 0,60 (PR-02 ahora usa 0,59) y el modelo de letras quietas pasó de 17 a 20 letras (PR-08).

| ID | Tipo | Requerimiento | Escenario | Resultado esperado | Resultado obtenido | Estado | Prueba |
|---|---|---|---|---|---|---|---|
| PR-01 | Unitaria | RF-04 | 5 cuadros consecutivos de "A" con confianza 0,90 | "A" se confirma en el 5.º cuadro | Confirmada en el 5.º | Aprobada | `test_buffer_texto.py::test_confirma_al_quinto_cuadro_estable` |
| PR-02 | Unitaria | RF-04 | 20 cuadros con confianza 0,79 | No se agrega ninguna letra | Texto vacío | Aprobada | `test_no_confirma_con_confianza_baja` |
| PR-03 | Unitaria | RF-04 | Predicción alterna A/B antes de 5 cuadros | No se confirma | Texto vacío | Aprobada | `test_prediccion_inestable_reinicia_la_racha` |
| PR-04 | Unitaria | RF-04 | Mantener la misma seña 30 cuadros | Se agrega una sola vez | "L" | Aprobada | `test_mantener_la_sena_no_repite_la_letra` |
| PR-05 | Unitaria | RF-03 | Mano desplazada y a otra distancia | Mismo vector normalizado | Iguales (tolerancia 1e-6) | Aprobada | `test_detector_manos.py::test_invariante_a_posicion_y_distancia` |
| PR-06 | Integración | RF-03 | Formato del dataset vs. normalización de la app | Muñeca en el origen, escala 1 | Coinciden | Aprobada | `test_formato_coincide_con_dataset_de_entrenamiento` |
| PR-07 | Integración | RF-02 | Cuadro sin mano en MediaPipe real | `None` (sin mano) | `None` | Aprobada | `test_cuadro_sin_mano_devuelve_none` |
| PR-08 | Integración | RF-03 | Una muestra por letra al modelo entrenado | Predice la letra correcta | 17/17 | Aprobada | `test_clasificador.py::test_acierta_una_muestra_por_letra` |
| PR-09 | Unitaria | RF-07 | Guardar sesión, cerrar y reabrir la base | El texto persiste | "HI" recuperado | Aprobada | `test_repositorio_historial.py` |
| PR-10 | Integración | RF-07 / CU-05 | Detener la aplicación | Guardar texto **antes** de liberar la cámara | abrir → guardar → liberar | Aprobada | `test_controlador.py::test_detener_guarda_antes_de_liberar_la_camara` |
| PR-11 | Integración | CU-01 (alt) | Cámara no disponible | Error controlado, no se crea sesión | Excepción, 0 sesiones | Aprobada | `test_camara_no_disponible` |
| PR-12 | No funcional | RNF-01/02 | Pipeline completo con la red bloqueada | Ningún intento de conexión | 0 conexiones | Aprobada | `test_no_funcionales.py::test_pipeline_completo_sin_red` |
| PR-13 | Rendimiento | RNF-03 | Detección + clasificación por cuadro 640×480 | < 66,7 ms (≥ 15 FPS) | 13,9 ms (~72 FPS) en el equipo de desarrollo | Aprobada | `test_tiempo_por_cuadro_permite_15_fps` |

## Pruebas manuales (pendientes, las ejecuta el equipo con la cámara)

| ID | Tipo | Requerimiento | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|---|
| PR-14 | Funcional | RF-01 | Presionar «Iniciar» con la cámara conectada | Video visible en < 3 s | | Pendiente |
| PR-15 | Funcional | RF-06 | Retirar la mano del cuadro | Aparece «No se detecta la mano» | | Pendiente |
| PR-16 | Funcional | RF-03/05 | Deletrear "CABLE" (solo letras estáticas) | Aparece "CABLE" en el texto de la sesión | | Pendiente |
| PR-17 | Funcional | RF-08 | Confirmar una letra | Se muestra su porcentaje de confianza | | Pendiente |
| PR-18 | Funcional | RF-07 | «Detener» y abrir «Historial» | La sesión aparece con su texto | | Pendiente |
| PR-19 | No funcional | RNF-02 | Repetir PR-16 con el adaptador de red desactivado | Funciona igual | | Pendiente |
| PR-20 | No funcional | RNF-03 | Observar el contador de FPS durante PR-16 | ≥ 15 FPS | | Pendiente |
| PR-21 | No funcional | RNF-04 | Ejecutar en un portátil de 8 GB sin GPU dedicada | Funciona con ≥ 15 FPS | | Pendiente |
| PR-22 | Usabilidad | RNF-05 | Persona que no conoce la app completa CU-01 a CU-03 sin ayuda | Lo logra | | Pendiente |
| PR-23 | Precisión | Obj. esp. 5 | Cada integrante hace 10 veces cada letra con luz buena / luz tenue | Registrar aciertos por letra y condición | | Pendiente |
| PR-24 | Precisión | Obj. esp. 5 | Generalización a personas nuevas (`entrenar_modelo.py` con capturas propias) | Registrar exactitud de la sección «Generalización» de `metricas_modelo.md` | | Pendiente |

## Modo Palabras

### Automáticas (`tests/test_palabras.py`)

| ID | Tipo | Escenario | Resultado esperado | Estado |
|---|---|---|---|---|
| PR-25a | Unitaria | Vector de cuadro con pose y mano | Origen entre los hombros, escala = ancho de hombros | Aprobada |
| PR-25b | Unitaria | La misma persona desplazada en la imagen | Mismo vector | Aprobada |
| PR-25c | Unitaria | Asignación de manos por cercanía a las muñecas de la pose | Izquierda/derecha correctas | Aprobada |
| PR-25d | Unitaria | Reposo, seña y reposo | El segmentador entrega exactamente una seña | Aprobada |
| PR-25e | Unitaria | Gesto de menos de 6 cuadros activos | Se ignora | Aprobada |
| PR-25f | Integración | Una seña con confianza baja | No se escribe; se pide repetir | Aprobada |
| PR-25g | Integración | La misma palabra dos veces en menos de 20 cuadros | Se escribe una vez (seña partida) | Aprobada |
| PR-25h | Integración | La misma palabra repetida con pausa | Se escribe dos veces | Aprobada |

### Prueba de punta a punta con personas no vistas (PR-26)

Se entrenó un modelo **sin** las personas 29 y 33. Luego se armaron 8 videos continuos, cada uno con 5 señas de esas personas separadas por reposo, y se pasaron por el mismo camino que la cámara en vivo: `ControladorSILVA` → `DetectorCuerpo` → `SegmentadorSenas` → `ClasificadorPalabras`.

| Métrica | Resultado |
|---|---|
| Señas en los videos | 40 |
| Señas segmentadas (una por seña, sin duplicados ni pérdidas) | 40 / 40 |
| Escritas correctamente | 33 (82,5 %) |
| Escritas mal (Buenas noches→Buenos días ×2, Chao→Hola ×2, Mal→Sí) | 5 |
| No escritas, la app pidió repetir | 2 |
| Velocidad del flujo completo | ~41 FPS |

### Manuales pendientes

| ID | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|
| PR-27 | Con la cámara del portátil, hacer *Hola*, *Gracias*, *Por favor* y *Buenos días*, bajando las manos entre señas | Se escriben las 4 palabras | | Pendiente |
| PR-28 | Mantener las manos abajo 10 segundos | No se escribe nada | | Pendiente |
| PR-29 | Persona sentada con solo el torso visible | Aparece el aviso o funciona; registrar cuál | | Pendiente |

## Verificación de red con MediaPipe nativo (PR-30)

PR-12 bloquea los sockets de Python, pero **no detecta conexiones que haga el código nativo (C++) de MediaPipe**. Al probar con la cámara real usando MediaPipe 1.1.0 apareció este aviso: `Network error: 503 for url: https://play.googleapis.com/log`. Es la telemetría ("Clearcut") que Google incluye en sus versiones publicadas desde la 0.10.22, sin forma de desactivarla ([issue #6291](https://github.com/google-ai-edge/mediapipe/issues/6291)).

**Acción:** se fijó `mediapipe==0.10.21`, la última versión sin esa telemetría.

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-30 | No funcional (RNF-01) | 20 s con la cámara real (10 s por modo), revisando cada segundo con `netstat -ano` las conexiones del proceso | Ninguna conexión | Ninguna conexión, y sin aviso de `play.googleapis.com` (29–30 FPS) | Aprobada |
| PR-31 | Regresión | Repetir PR-26 (personas no vistas) con MediaPipe 0.10.21 | Mismo resultado | 33/40 correctas, 2 pedidas de repetir: idéntico | Aprobada |
| PR-32 | Funcional (CU-01/CU-05) | Iniciar → Detener → Iniciar, 6 ciclos con la cámara real en ambos modos | Cada inicio enciende la cámara | 6/6 y 0 errores (antes fallaba el 2.º inicio: `image "pyimageN" doesn't exist`) | Aprobada |

## Interfaz PySide6 (Qt)

La interfaz pasó de Tkinter a PySide6 y el procesamiento de video a un hilo aparte.

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-33 | Integración (`test_interfaz.py`) | 3 ciclos Iniciar/Detener con el hilo de video y cámara simulada | Cada ciclo inicia y detiene; 3 sesiones guardadas | Correcto. Encontró un error real: SQLite rechazaba escrituras desde el hilo de video; se corrigió | Aprobada |
| PR-34 | Integración | Letra confirmada en el hilo de video | Aparece en el texto y en «Última confirmada» | Correcto | Aprobada |
| PR-35 | Integración | Cámara no disponible | Mensaje de error; se puede reintentar | Correcto | Aprobada |
| PR-36 | Integración | Cambio de modo, edición del texto, historial | Paneles, botones y tabla correctos | Correcto | Aprobada |
| PR-37 | Funcional | Cámara real: 4 ciclos Iniciar/Detener en ambos modos, con `netstat` | Sin errores ni conexiones de red | 30–31 FPS, 0 errores, ninguna conexión | Aprobada |

## Versión 1.0.0: Responder (RF-09) y ejecutable

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-38 | Integración (`test_interfaz.py`) | Responder: texto vacío, luego una frase, luego clic sobre el video | Lo vacío no se muestra; la frase se ve en grande y se guarda; el clic la cierra | Correcto | Aprobada |
| PR-39 | Unitaria (`test_repositorio_historial.py`) | Respuestas con y sin sesión activa | Se guardan y se listan, la más reciente primero | Correcto | Aprobada |
| PR-40 | Despliegue | `SILVA.exe --verificar --camara`, descomprimido **fuera** del proyecto y sin Python del proyecto | Carga los 4 modelos, abre el historial y lee la cámara | Todo correcto; cámara 15/15 cuadros | Aprobada |
| PR-41 | Despliegue / RNF-01 | Abrir `SILVA.exe`, observar 15 s con `Get-NetTCPConnection` y cerrar la ventana | Ventana abierta, sin conexiones de red, cierre limpio | Título «SILVA 1.0.0», ninguna conexión, cierre correcto; ~745 MB de RAM | Aprobada |
| PR-42 | Despliegue | El historial del ejecutable se guarda fuera de la carpeta del programa | `%LOCALAPPDATA%\SILVA\historial.db` | Correcto (informe de PR-40) | Aprobada |

## Versión 1.1: rechazo, corrección y cámara (prueba con usuarios del 26/10/2026)

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-43 | Precisión | 1 671 señas de LSC-54 ajenas al vocabulario con el modelo 1.0.0 | — (diagnóstico) | **81 %** terminaban escritas como una palabra | Defecto confirmado |
| PR-44 | Integración (`test_palabras.py`) | Seña segura, seña dudosa, movimiento ajeno, corregir, descartar, empezar otra seña, detener | Provisional que se escribe sola; sugerencia que solo se escribe si se elige; ajeno ignorado | Correcto (8 pruebas con reloj simulado) | Aprobada |
| PR-45 | Interfaz (`test_interfaz.py`) | Panel de corrección: elegir la opción 2, descartar una sugerencia, Espacio confirma | Texto correcto y panel oculto | Correcto | Aprobada |
| PR-46 | Interfaz | La ventana no crece al aparecer el panel de corrección | Mismo tamaño | Mínimo 766 px de alto (antes 931); la ventana se queda en 820 | Aprobada |
| PR-47 | Funcional | Cambio de resolución en vivo con la cámara real (Deletreo ↔ Palabras) | 640×480 ↔ 1280×720 | Correcto (procesado en 640×360). La imagen salió negra: no se pudo medir el campo de visión | Parcial |
| PR-48 | Precisión, punta a punta | 40 señas del vocabulario + 30 ajenas, personas 29 y 33 no vistas, reloj de 30 cuadros/s | Pocas palabras falsas | Ajenas escritas: 3 %. Vocabulario: 60 % solas y bien, 20 % recuperables con «¿Quiso decir?», 5 % mal (corregibles), 15 % ignoradas | Aprobada |
| PR-49 | Usabilidad (manual) | Repetir la prueba del 26/10 con la versión 1.1 | Sin palabras «de la nada»; corrección entendible | | Pendiente |

## Versión 1.2: más personas y seguimiento (26/10/2026)

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-50 | Precisión (letras) | Modelo v1.1 (1 persona) con las 70 personas de LSC70 | — (diagnóstico) | 74,3 %; escribe solo el 34 % | Defecto confirmado |
| PR-51 | Precisión (letras) | Modelo v1.2 (+LSC70), validación cruzada por persona | Mejor que PR-50 | 88,5 %; escribe el 69 % con 98,4 % de acierto | Aprobada |
| PR-52 | Precisión (palabras) | Modelo v1.1 con las 5 personas de LSC50 (otro entorno) | — (diagnóstico) | 32 % en las 14 señas comunes | Defecto confirmado |
| PR-53 | Precisión (palabras) | Modelo v1.2 (+LSC50), personas de LSC50 no vistas | Mejor que PR-52 | 77,1 % (entre las 3 primeras: 91,8 %) | Aprobada |
| PR-54 | Seguimiento | Detección de la mano en 4 512 cuadros de seña, umbral 0,6 vs 0,4 y media resolución | — | 84,9 % → 87,2 %; la resolución no influye | Medido |
| PR-55 | Interfaz | Aviso de poca luz y mano aproximada (`test_interfaz.py`, `test_palabras.py`) | Aviso con imagen oscura; trazos de la mano perdida | Correcto | Aprobada |

## Versión 1.3: 27 letras, seguimiento, diseño nuevo y app de Android (27/10/2026)

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-56 | Precisión (letras) | Modelo de 20 letras quietas (+M, N, P), personas no vistas de LSC70 | Igual que la v1.2 | 88,2 % (v1.2 con 17 letras: 88,5 %) | Aprobada |
| PR-57 | Precisión (letras con trazo) | G H J Ñ Q S Z, validación cruzada por persona en LSC70, umbral 0,4 | Lo escrito acierta ≥ 95 % | Escribe el 58 % con 96,3 % de acierto; 9 % de letras falsas al pasar de una letra quieta a otra | Aprobada |
| PR-58 | Unitaria (`test_letras_movimiento.py`) | Mano quieta, trazo completo, temblor corto, mano perdida, J que empieza como I, trazo que no es letra | Solo el trazo completo escribe; la J reemplaza a la I | Correcto (9 pruebas) | Aprobada |
| PR-59 | Precisión (letras) | Umbral 0,80 → 0,60, personas no vistas de LSC70 | Escribir más sin bajar mucho el acierto | Escribe 70,2 % → 84,8 %; acierto 98,5 % → 96,1 % | Aprobada |
| PR-60 | Seguimiento | Recuperación de la mano en un recorte alrededor de la muñeca, 40 videos de LSC-54 | Más cuadros con la mano detectada | 70 % → 81 % de los cuadros | Aprobada |
| PR-61 | Rendimiento | Modo Palabras: cámara a 640×360 y pose y manos en paralelo | ≥ 15 FPS | La cámara pasa de 10 a 30 cuadros por segundo; 19 ms por cuadro (antes 29) | Aprobada |
| PR-62 | Precisión (palabras) | Modelo reentrenado con LSC-54 extraído con la recuperación, personas no vistas | Igual o mejor que la v1.2 | 85,3 %; escribe solo el 56,4 % con 95,7 % de acierto (v1.2: 53 % con 96,3 %) | Aprobada |
| PR-63 | Integración (`test_palabras.py`, `test_interfaz.py`) | Palabra escrita al instante; cambiarla con 1–3 o borrarla con X durante 3 s | Se escribe enseguida y se puede corregir | Correcto | Aprobada |
| PR-64 | Integración (`test_interfaz.py`, `test_buffer_texto.py`) | «¿Quisiste decir?» al deletrear «HOLA MUN» | Sugiere MUNDO y lo completa con un clic | Correcto | Aprobada |
| PR-65 | Integración (`test_animacion.py`) | Una animación por palabra; buscar las señas de una frase | 33 animaciones; «Muchas gracias» se toma como una sola seña | Correcto | Aprobada |
| PR-66 | Despliegue | `SILVA.exe --verificar` de la v1.3.0 | Carga todos los modelos, incluido el de letras con trazo | Todo correcto | Aprobada |
| PR-67 | Unitaria (Kotlin, `IgualQuePythonTest.kt`) | Características, probabilidades de los tres modelos, constantes, búsqueda de señas, sugerencias y corrección vertical, contra casos de Python | Mismos valores | 12 de 12 | Aprobada |
| PR-68 | Funcional (emulador Android) | 12 videos de LSC-54 por la app del teléfono, por el mismo camino que la cámara | Igual que la app de PC | 8 escritas, 1 como «¿Quisiste decir?», 3 rechazadas: idéntico. Con recorte vertical: 6 escritas y 4 sugeridas | Aprobada |
| PR-69 | Funcional (emulador Android) | 42 letras de LSC70 por la app del teléfono, umbral 0,80 y 0,60 | Escribir más letras con 0,60 | 24 → 31 escritas, con 1 error | Aprobada |
| PR-70 | No funcional (RNF-01) | Permisos del APK | Sin permiso de internet | Solo cámara y micrófono (este último solo para «Hablar») | Aprobada |
| PR-71 | Funcional (teléfono real) | Señas a texto en Palabras y Deletreo con buena luz, teléfono apoyado a 1,5–2 m | Reconoce como en el emulador; registrar los FPS | | Pendiente |
| PR-72 | Funcional (teléfono real) | «Hablar», «Escuchar» y «Leer en voz alta» con audio real | Funcionan sin internet | | Pendiente |
| PR-73 | Rendimiento (Galaxy A35, Android 16) | Modo Palabras con la cámara frontal: MediaPipe en CPU, en GPU, y manos en GPU con pose en CPU | Más cuadros/s sin perder precisión | CPU 7-10 · GPU 13 · manos en GPU y pose en CPU 15-17 cuadros/s (Deletreo: 15 → 19). Con los 24 videos de prueba: 16 palabras bien (CPU 17), ninguna mal | Aprobada |
| PR-74 | Precisión en vivo (`scripts/evaluar_fps.py`) | Segmentador por cuadros contra por segundos a 30, 15, 10 y 7,5 cuadros/s, personas no vistas | Igual a 30; mejor a menos cuadros/s | A 30 idéntico; a 15, escrita bien 36,6 % → 43,8 %; a 10, 28,6 % → 40,7 % | Aprobada |
| PR-75 | Unitaria (`test_palabras.py`) | La misma seña de 0,4 s a 30 y a 15 cuadros/s | Se detecta en ambos casos | Correcto (antes se descartaba a 15 cuadros/s) | Aprobada |

## Versión 1.4.0: entrenar con muestras propias (27/10/2026)

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-76 | Unitaria (`test_muestras_propias.py`) | Archivo de muestras del teléfono y del PC: palabras, letras quietas y trazos; el mismo archivo dos veces; un archivo que no es de SILVA | Se separan por modelo, sin duplicados; se rechaza el ajeno | Correcto (4 pruebas) | Aprobada |
| PR-77 | Integración (`test_palabras.py`, `test_interfaz.py`) | Ventana Entrenar: grabar una letra quieta; controlador entrenando en Palabras | Guarda la muestra, no escribe en el texto ni guarda una sesión | Correcto | Aprobada |
| PR-78 | Funcional (app de PC, cámara real) | Grabar «Muy bien» y «Sí» sentado frente al PC | Muestras utilizables | 34 muestras; 12 llegaron al límite de 4 s porque el reposo sentado (manos a 0,3-0,7 anchos de hombro bajo los hombros) no se reconoce como reposo. Ahora se descartan y la app avisa | Parcial |
| PR-79 | Despliegue (`SILVA.exe --entrenar`, carpeta de usuario temporal) | Reentrenar dentro del ejecutable con esas muestras | Modelo nuevo y paquete para el teléfono | 1 min 14 s; palabras escritas bien con sus tomas no vistas: antes 0 %, después 36 %; el ejecutable abre con el modelo nuevo. La prueba encontró una carpeta que no se creaba (corregido) | Aprobada |
| PR-80 | Despliegue | `SILVA.exe --verificar` de la v1.4.0 | Modelos y datos para entrenar | Todo correcto, con los 5 datasets | Aprobada |
| PR-81 | Funcional (teléfono) | Sección Entrenar en el Galaxy A35 | Se ve completa | Correcto; grabar y exportar desde el teléfono queda por probar con personas | Parcial |

## Versión 1.4.1: señas animadas completas y guía del Deletreo (27/10/2026)

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-82 | Datos (`generar_animaciones.py`) | Manos de las 33 señas animadas | Ninguna mano desaparece | Antes: las 33 perdían alguna mano (hasta el 100 % en señas de una mano) y «Bienvenido» tenía una mano detectada a 5 anchos de hombro. Ahora: 0 de 33 (manos lejanas descartadas, huecos completados, cuadros sin pose quitados) | Aprobada |
| PR-83 | Unitaria (`test_animacion.py`) | Encuadre de cada seña | La figura cabe entera en su recuadro | Correcto en las 33 | Aprobada |
| PR-84 | Unitaria (`test_animacion.py`) | Guías de las letras | Una por letra; trazo solo en G H J Ñ Q S Z; se dibujan | Correcto (27) | Aprobada |
| PR-85 | Datos | Elección de la guía de cada letra en LSC70 | Mano visible en las 6 imágenes, clara para los modelos, vista de frente y sin saltos | 27 guías; se descartaron grabaciones con saltos de la muñeca de hasta 7 palmas (H, S) | Aprobada |
| PR-86 | Funcional (Galaxy A35) | Abecedario → J; Vocabulario → Bienvenido | La guía y la figura se ven completas | Correcto | Aprobada |
| PR-87 | Usabilidad | Que una persona que sabe LSC revise las 27 guías | Cada guía muestra la letra correcta | | Pendiente |

## Reposo sentado (27/10/2026)

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-88 | Unitaria (Python y Kotlin) | Persona sentada con las manos sobre la mesa (0,5 anchos de hombro bajo los hombros) hace una seña | La seña termina al volver las manos a la mesa, sin un tramo falso al empezar | Sin reposo aprendido: cortada a los 4 s. Con él: una seña de menos de 1,5 s | Aprobada |
| PR-89 | Precisión (`evaluar_reposo.py --completo`) | LSC-54 de pie, personas no vistas, 30 y 15 cuadros/s | No empeora | 51,0 → 51,2 % y 51,5 → 51,8 % escritas bien; palabras falsas 0,6-0,8 % | Aprobada |
| PR-90 | Precisión | Muestras propias grabadas sentado | Menos señas cortadas a los 4 s | 50 → 56 % cortadas a tiempo (las muestras miden mal el cambio) | Parcial |
| PR-91 | Funcional (manual) | Usar SILVA sentado con las manos sobre la mesa entre señas, en el PC y en el teléfono | Cada palabra se escribe al bajar las manos, sin esperar 4 s | | Pendiente |


## Versión 1.5.0: correcciones de la prueba con usuarios del 27/10/2026

| ID | Tipo | Escenario | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| PR-92 | Precisión (`entrenar_palabras.py`) | Manos en reposo o quietas (sentado, sobre la mesa), personas no vistas | El modelo no escribe palabras («Por favor» salía sola) | El modelo nunca había visto tramos sin seña: 13,5 % de palabras falsas. Entrenado con el reposo de cada video y posturas quietas con las manos bajas como «otra cosa»: 0,0 %. Exactitud 84,4 % (antes 85,3 %); escribe sola el 50 % de las señas (antes 56 %) con 95,1 % de acierto; palabras falsas ante movimientos ajenos 3,6 % (antes 12,5 %) | Aprobada |
| PR-93 | Unitaria (`test_palabras.py`) | Corregir una palabra (elegir otra opción) o borrar una que se escribió sola | Se guarda como muestra para entrenar: con la palabra elegida, o como «otra cosa» | Correcto; plazo para corregir 8 s (antes 3 s) y para elegir una sugerencia 10 s (antes 6 s), en el PC y el teléfono | Aprobada |
| PR-94 | Funcional (emulador, 360 dp, navegación con 3 botones, letra 1,3×) | Barra de abajo del teléfono | Visible y sin cortar palabras | Antes se ocultaba en teléfonos que informan el teclado como abierto. Ahora se ve siempre; con letra grande del sistema, la barra la limita a 1,15× y «Conversar» ya no se parte | Aprobada |
| PR-95 | Funcional (teléfono) | Corregir una palabra en el celular | Botones táctiles | La tarjeta muestra las opciones como botones grandes y «Borrar» / «No era ninguna» | Aprobada |
| PR-96 | Funcional (PC) | Elegir cámara | Lista desplegable con las cámaras conectadas por su nombre | «Brio 300», «Camera (NVIDIA Broadcast)», «OBS Virtual Camera» (DirectShow, mismo orden que OpenCV); la lista se actualiza al abrirla y cambiar con la cámara encendida la reinicia | Aprobada |
| PR-97 | Unitaria (Python y Kotlin) | Trazo de una letra con la mano perdida ~0,1 s a mitad del movimiento | Un solo trazo completo | Antes se partía en dos. Ahora se toleran 0,3 s sin mano; el trazo de las letras se mide en segundos (el teléfono va a ~19 cuadros/s) | Aprobada |
| PR-98 | Configuración | Mano rápida | MediaPipe la pierde menos | Seguimiento 0,6 → 0,4 en Deletreo; se piden 30 cuadros/s a la cámara (PC y teléfono) para que no baje a 15 con poca luz y la mano no salga borrosa | Parcial (falta medir con cámara real) |
| PR-99 | Datos (`generar_animaciones.py`) | Guías de las letras con trazo | Movimiento claro y fluido | Se elige un recorrido amplio con la mano de tamaño parejo; se suaviza el temblor; la Z se dibuja con su forma (LSC70 no muestra sus esquinas); interpolación Catmull-Rom; todas las guías en vista de espejo, como la cámara de la app (la J y la Z se veían al revés) | Aprobada |
| PR-100 | Funcional (manual) | Repetir la prueba con usuarios en el PC y en el teléfono | «Por favor» no aparece sola; Z, H, J y Ñ se escriben | | Pendiente |
