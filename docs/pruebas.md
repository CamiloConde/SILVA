# Plan y registro de pruebas (sección 10.3 de la plantilla)

## Pruebas automáticas

Se ejecutan con `python -m pytest -v`. Resultado de la última ejecución (8/10/2026, Windows 11, Python 3.12.10): **30 de 30 aprobadas**.

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
