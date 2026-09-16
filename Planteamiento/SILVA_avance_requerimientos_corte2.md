# Avance de proyecto de aula — Ingeniería de requerimientos y validación del modelado

**Proyecto:** SILVA (Sistema Inteligente de Lenguaje Visual Aumentado)
**Equipo:** Equipo 3 — Miguel Alejandro Jácome Yánez, Camilo Andrés Conde Corrales, Juan Diego Rosales Guillén
**Curso:** Ingeniería de Software, grupo 1206
**Docente:** Aisner José Marrugo Juliao
**Fecha:** 16 de septiembre de 2026
**Repositorio:** https://github.com/CamiloConde/SILVA
**Documento base que se complementa:** [Silva-corte1.pdf](Silva-corte1.pdf) (secciones 1-8) y [SILVA_diagramas_UMLv2.pdf](SILVA_diagramas_UMLv2.pdf) (modelado UML previo)

Este documento complementa el modelado inicial de SILVA presentado en la entrega anterior, mediante el proceso de ingeniería de requerimientos solicitado en la guía *Avance de proyecto de aula*. Se estructura siguiendo los ocho puntos de esa guía; las tablas de requerimientos y backlog quedan redactadas con la misma nomenclatura (RF-xx, RNF-xx) del punto 9 de la plantilla del proyecto de aula, para que puedan trasladarse directamente a esa sección cuando se consolide el documento completo del segundo corte.

---

## 1. Descripción del problema

La comunicación entre personas sordas y oyentes que desconocen la lengua de señas depende hoy de intérpretes humanos, recursos escritos o aplicaciones de traducción limitadas, que no siempre están disponibles en el momento y lugar necesarios. Esta brecha se agrava por dos factores que confirmamos durante la elicitación (ver sección 3): la escasez de intérpretes certificados y la situación socioeconómica de buena parte de la población sorda, que limita su acceso a soluciones que dependan de conectividad constante, hardware especializado o servicios pagos.

A nivel mundial, la Organización Mundial de la Salud (OMS) estima que 430 millones de personas requieren en la actualidad rehabilitación por pérdida auditiva discapacitante, cifra que podría llegar a 2 500 millones de personas con algún grado de pérdida auditiva hacia 2050; cerca del 80 % de quienes tienen pérdida auditiva discapacitante vive en países de ingresos bajos y medios (Organización Mundial de la Salud [OMS], 2024). En Colombia, el DANE registró 459 784 personas sordas en 2021, un aumento del 10 % frente a 2018, y el Instituto Nacional para Sordos (INSOR) señala que solo cerca del 2 % de las entidades del país ha recibido asesoría en políticas de inclusión para esta población (Linares Munar, 2023).

SILVA responde a esta necesidad con una aplicación de escritorio que traduce a texto, en tiempo real, señas estáticas del alfabeto dactilológico, capturadas con una cámara web y procesadas localmente (sin servidor, sin nube, sin costo de conectividad). Los usuarios objetivo son personas oyentes que necesitan interpretar lengua de señas sin conocimiento previo de esta, y personas sordas que buscan comunicarse con su entorno oyente sin depender de un intérprete presencial.

## 2. Identificación de interesados

| Interesado | Relación con el proyecto | Necesidades / expectativas principales |
|---|---|---|
| Persona sorda o con discapacidad auditiva | Usuario final directo | Comunicarse por escrito con oyentes sin depender de un intérprete; que la app funcione sin conexión a internet ni hardware costoso. |
| Persona oyente sin conocimiento de LSC | Usuario final directo | Interpretar la seña en tiempo real, sin capacitación previa ni curva de aprendizaje de la interfaz. |
| Instituciones educativas y de salud | Beneficiario indirecto / posible adoptante | Mejorar la accesibilidad de su atención a personas sordas sin incurrir en el costo permanente de un intérprete. |
| INSOR y organizaciones de la comunidad sorda | Fuente de información / referente de política pública | Que la solución respete la lengua de señas como primera lengua de la comunidad sorda y no reemplace, sino complemente, la interpretación humana certificada. |
| Docente evaluador (Aisner José Marrugo Juliao) | Cliente académico del proyecto de aula | Evidencia real de elicitación, trazabilidad entre requerimientos y modelado, y un MVP viable dentro del semestre. |
| Equipo desarrollador (Grupo 3) | Responsable técnico | Construir un prototipo funcional y sustentado con el tiempo y las herramientas disponibles (Python, OpenCV, MediaPipe, scikit-learn). |

## 3. Técnicas de elicitación aplicadas

Dado que el equipo no tiene acceso directo, en esta etapa del semestre, a usuarios sordos u oyentes dispuestos a una entrevista o encuesta formal, se optó por dos técnicas que sí permiten obtener evidencia real y verificable: **revisión de documentos existentes** (fuentes institucionales, académicas y periodísticas) y **benchmarking de soluciones similares**. Ambas están contempladas explícitamente en la guía de la actividad.

| Técnica | Objetivo | Participantes | Periodo de aplicación | Herramienta | Principales hallazgos |
|---|---|---|---|---|---|
| Revisión de documentos existentes | Sustentar con datos verificables el problema, la magnitud de la población afectada y las barreras de acceso que enfrenta, para no formular el problema como "ausencia de la aplicación" | Equipo SILVA (los 3 integrantes) | 15-16 de septiembre de 2026 | Búsqueda documental en fuentes institucionales (OMS, DANE/INSOR) y académicas (Scielo) | Ver sección 4.1 |
| Benchmarking de soluciones similares | Identificar qué tan resuelto está el problema por soluciones existentes, qué enfoque técnico usan y qué vacío ocupa SILVA frente a ellas | Equipo SILVA (los 3 integrantes) | 15-16 de septiembre de 2026 | Comparación funcional y técnica de 3 soluciones (HandTalk, SignAll, proyecto open source `sign-language-detector`) | Ver sección 4.2 |

## 4. Muestras de las herramientas utilizadas

### 4.1 Fichas de la revisión documental

**Fuente 1 — Organización Mundial de la Salud (2024).** *Deafness and hearing loss* [ficha técnica]. Confirma la magnitud global del problema (430 millones de personas requieren rehabilitación por pérdida auditiva discapacitante; 80 % vive en países de ingresos bajos/medios) y su costo económico (cerca de US$ 1 billón anual por pérdida auditiva no atendida). **Uso en el proyecto:** justifica que la solución no dependa de hardware costoso ni de servicios pagos recurrentes.

**Fuente 2 — Linares Munar, L. (2023, 24 de septiembre).** *"Colombia tiene porcentaje bajo en la implementación de los derechos de las personas sordas", Insor*. Infobae. Reporta 459 784 personas sordas registradas en Colombia (DANE, 2021), un incremento del 10 % frente a 2018, y que solo ~2 % de las entidades del país ha recibido asesoría en inclusión de INSOR. **Uso en el proyecto:** confirma que la brecha de atención institucional es real y vigente, no solo una percepción del equipo.

**Fuente 3 — Instituto Nacional para Sordos [INSOR] (2019).** *Plan Estratégico Institucional 2019-2022* (citado en fuentes secundarias consultadas). Señala que un porcentaje alto de la población sorda colombiana se encuentra en condición de pobreza o vulnerabilidad económica, y que en salud las personas sordas frecuentemente deben costear su propio intérprete. **Uso en el proyecto:** motiva las decisiones ya tomadas en el diagrama de despliegue (Figura 8 del documento de modelado UML) de que SILVA opere sin conexión a internet ni infraestructura remota.

*Nota sobre la fuente 3: se identificó a través de artículos periodísticos que citan el Plan Estratégico de INSOR; no se tuvo acceso directo al documento original, por lo que se referencia como fuente secundaria. Se recomienda, para el documento final del tercer corte, intentar acceder al reporte primario en insor.gov.co.*

### 4.2 Matriz de benchmarking de soluciones similares

| Solución | Dirección de traducción | Enfoque técnico | Hardware requerido | Conectividad | Costo | Brecha frente a SILVA |
|---|---|---|---|---|---|---|
| **HandTalk** (Hand Talk, fundada en 2012) | Texto/voz → señas (avatar Hugo/Maya) | Avatar animado 3D | Smartphone | Requiere internet | Gratuita (app) | Traduce en sentido opuesto al de SILVA; no reconoce señas hechas por el usuario. |
| **SignAll 1.0** | Señas → texto (bidireccional con voz) | Visión por computador + guantes sensorizados, 2 monitores | Guantes especiales, cámaras fijas, 2 pantallas | Requiere instalación fija | Orientado a empresas/instituciones (no de uso personal) | Reconocimiento más robusto (frases), pero requiere hardware especializado y costoso, no portable. SILVA cubre el nicho de una solución liviana de un solo computador con cámara web. |
| **`sign-language-detector`** (proyecto open source, MediaPipe + Random Forest) | Señas estáticas → letra | MediaPipe Hands (21 landmarks) + Random Forest, igual enfoque que SILVA | Cámara web | No requiere internet en modo nativo | Gratuito / código abierto | Reconoce solo 15 señas y fue entrenado con datos de una sola persona, lo que —según reconocen sus propios autores— limita la generalización; confirma la pertinencia del objetivo específico 5 de SILVA (evaluar precisión con distintos usuarios y condiciones de iluminación). |

**Hallazgo transversal:** ninguna de las soluciones comparadas ofrece, a la vez, (a) traducción de seña a texto, (b) procesamiento 100 % local sin hardware especializado, y (c) retroalimentación visible de la confianza de la predicción al usuario. Este último punto —mostrar el nivel de confianza— sí aparece implícitamente resuelto en el modelo de datos de SILVA (la clase `Prediccion` ya contempla el atributo `confianza: float`, ver Figura 2 del documento UML), pero no estaba expuesto como funcionalidad visible para el usuario en los casos de uso originales. Este hallazgo se traduce en un ajuste al modelado (ver sección 7).

## 5. Requerimientos identificados

### 5.1 Requerimientos funcionales

| ID | Requerimiento | Fuente | Prioridad | Criterio de aceptación | Estado |
|---|---|---|---|---|---|
| RF-01 | El sistema debe iniciar la captura de video desde la cámara web al presionar "Iniciar". | Revisión documental (evita dependencia de intérprete presencial) + CU-01 del modelado previo | Alta | Al presionar "Iniciar" con cámara disponible, la ventana muestra el video en menos de 3 segundos. | Pendiente |
| RF-02 | El sistema debe detectar si hay una mano dentro del cuadro capturado. | Benchmarking (`sign-language-detector`, SignAll) + CU-02.1 | Alta | Con una mano visible en el cuadro, el sistema marca `manoDetectada = true`; sin mano, marca `null`. | Pendiente |
| RF-03 | El sistema debe extraer los 21 landmarks de la mano detectada y clasificar la seña estática correspondiente al alfabeto dactilológico. | Benchmarking (enfoque técnico común: MediaPipe + clasificador) + CU-02.2/CU-02.3 | Alta | Dada una mano detectada, el sistema retorna una predicción (letra, confianza) en cada cuadro procesado. | Pendiente |
| RF-04 | El sistema solo debe confirmar y agregar una letra al texto cuando la predicción tenga confianza ≥ 0,80 y se mantenga estable durante 5 cuadros consecutivos. | Regla ya validada en el diagrama de secuencia previo (Figura 4, UML) | Alta | Predicciones con confianza < 0,80 o inestables no se agregan al texto acumulado. | Pendiente |
| RF-05 | El sistema debe mostrar en pantalla, en tiempo real, la letra reconocida y el texto acumulado de la sesión. | Descripción del problema (necesidad de comunicación inmediata) + CU-03/CU-04 | Alta | Cada letra confirmada aparece en pantalla en un lapso perceptible como "tiempo real" (< 1 s). | Pendiente |
| RF-06 | El sistema debe avisar al usuario cuando no se detecta ninguna mano en el cuadro. | Benchmarking (SignAll usa doble pantalla para dar retroalimentación constante) + CU-02.4 | Media | Al no detectarse mano durante un cuadro, se muestra el mensaje "No se detecta la mano". | Pendiente |
| RF-07 | Al detener la aplicación, el sistema debe guardar el texto de la sesión en el historial local y liberar la cámara. | Diagrama de secuencia CU-05 (orden de cierre ya validado) | Media | Al presionar "Detener", el texto queda persistido en `historial.db` antes de liberar la cámara. | Pendiente |
| RF-08 *(nuevo)* | El sistema debe mostrar al usuario el nivel de confianza de cada predicción aceptada. | Hallazgo de benchmarking (sección 4.2): ninguna solución comparada expone la confianza, pero el modelo de datos de SILVA ya la contempla | Baja | Junto a cada letra confirmada se muestra el valor de confianza (por ejemplo, como porcentaje). | Pendiente |

### 5.2 Requerimientos no funcionales

| ID | Atributo | Requerimiento medible | Fuente | Evidencia / prueba |
|---|---|---|---|---|
| RNF-01 | Privacidad y procesamiento local | El video capturado no debe salir del equipo del usuario; no debe existir transmisión a servidores externos. | Revisión documental: condición socioeconómica de la población sorda (INSOR/Linares Munar, 2023) y ausencia de conectividad garantizada | Verificación de tráfico de red nulo durante la ejecución (sin llamadas salientes) |
| RNF-02 | Disponibilidad sin conexión | El sistema debe ejecutarse completamente sin conexión a internet una vez instalado. | Revisión documental (80 % de personas con pérdida auditiva discapacitante vive en países de ingresos bajos/medios, OMS, 2024) | Ejecución exitosa de la aplicación con el adaptador de red deshabilitado |
| RNF-03 | Rendimiento / tiempo real | El ciclo de captura-detección-clasificación-visualización por cuadro debe completarse en un tiempo que permita una experiencia fluida (objetivo de referencia: ≥ 15 cuadros por segundo). | Benchmarking (MediaPipe Hands está diseñado para tracking en tiempo real) | Medición de FPS durante la ejecución con cámara activa |
| RNF-04 | Compatibilidad de hardware | El sistema debe ejecutarse en un equipo de escritorio o portátil estándar (8 GB de RAM, sin GPU dedicada), sin hardware adicional al de una cámara web. | Benchmarking (SignAll requiere guantes y 2 monitores; SILVA busca ser más accesible) | Ejecución de la aplicación en un equipo con las características mínimas señaladas |
| RNF-05 | Usabilidad | La interfaz debe permitir iniciar una traducción sin necesidad de capacitación previa ni manual de usuario. | Descripción del problema (usuarios oyentes sin conocimiento previo de LSC) | Prueba de uso con una persona que no haya visto la aplicación antes, completando CU-01 a CU-03 sin ayuda |

## 6. Priorización de requerimientos

Se utilizó el método **MoSCoW**, cruzando la prioridad de cada requerimiento con su relación directa con el MVP definido en la entrega anterior (sección 10.3 de `Silva-corte1.pdf`).

- **Obligatorio (Must have):** RF-01, RF-02, RF-03, RF-04, RF-05, RF-07, RNF-01, RNF-02, RNF-03, RNF-04. Son los requerimientos sin los cuales no existe el MVP: capturar video, detectar la mano, clasificar la seña, mostrar el resultado y hacerlo de forma local, en tiempo real y sin hardware especializado.
- **Importante (Should have):** RF-06, RNF-05. Mejoran la experiencia de uso y la robustez frente a errores, pero su ausencia no impide demostrar el reconocimiento de señas.
- **Deseable (Could have):** RF-08 (mostrar nivel de confianza). Aporta valor de transparencia y confianza en el sistema, pero no es indispensable para el criterio de éxito del MVP.
- **No incluido por ahora (Won't have):** reconocimiento de señas dinámicas, traducción de frases, versión móvil o web, soporte multilenguaje de señas — ya declarados fuera de alcance en la entrega anterior y confirmados sin cambios (ver sección 7).

Para la primera versión funcional del proyecto (MVP del tercer corte) se considerarán los requerimientos marcados como **Obligatorio**; los **Importante** se incorporarán si el cronograma lo permite, y el **Deseable** (RF-08) queda como mejora de una siguiente iteración dentro del mismo corte, dado su bajo costo de implementación (el dato ya existe en el modelo).

## 7. Validación y ajuste del modelado previo

**Concepción inicial:** el modelado UML entregado previamente (`SILVA_diagramas_UMLv2.pdf`) ya había sido depurado en una primera iteración: se definió un único actor "Usuario", se excluyeron el entrenamiento de modelo y la recolección de datos del alcance, y se estableció la regla de confianza ≥ 0,80 con estabilidad de 5 cuadros.

**Hallazgo general de la elicitación:** la revisión documental y el benchmarking **confirman**, en su mayoría, las decisiones ya tomadas —no las contradicen—, y aportan una justificación externa (más allá del criterio del equipo) para mantenerlas. Se identificó un único punto de mejora: exponer al usuario un dato que el modelo de clases ya calculaba pero no mostraba.

| Elemento revisado | Concepción inicial | Hallazgo de la elicitación | Cambio realizado o justificación |
|---|---|---|---|
| Actor | Un único actor "Usuario" (persona sorda u oyente), sin distinguir roles. | El benchmarking de SignAll muestra que otras soluciones sí separan al signante del oyente con pantallas distintas, pero esto responde a su arquitectura de dos monitores, no a una necesidad funcional distinta para SILVA (un solo computador, un solo usuario frente a la cámara en cada momento). | **Sin cambios.** Se mantiene el actor único "Usuario" del diagrama de casos de uso (Figura 1). |
| Funcionalidad — Visualizar letra reconocida (CU-03) | El sistema muestra la letra reconocida y el texto acumulado, sin exponer la confianza de la predicción. | Ninguna de las soluciones comparadas en el benchmarking expone la confianza al usuario final, pero la revisión del propio modelo de clases (Figura 2, clase `Prediccion`) mostró que el atributo `confianza: float` ya existe y no se estaba usando en la interfaz. | **Cambio menor:** se agrega RF-08 (mostrar el nivel de confianza junto a la letra). No requiere modificar el diagrama de clases ni el de componentes, porque el dato ya está disponible; solo se extiende el comportamiento de `VentanaPrincipal.mostrarPrediccion()` descrito en la Figura 3/4. |
| Requisito no funcional — Procesamiento local / sin conexión | El diagrama de despliegue (Figura 8) ya representaba una ejecución 100 % local, sin servidor ni nube. | La revisión documental (OMS, 2024; INSOR, vía Linares Munar, 2023) confirma que esta decisión es también una necesidad de accesibilidad económica de la población objetivo, no solo una decisión técnica de simplicidad. | **Sin cambios en el diagrama.** Se formaliza como RNF-01 y RNF-02, documentando explícitamente la razón (antes implícita) detrás de una decisión de diseño ya tomada. |
| Proceso — Confirmación de seña (umbral de confianza + estabilidad temporal) | Definido en el diagrama de secuencia (Figura 4): confianza ≥ 0,80 y letra estable durante 5 cuadros. | El benchmarking de proyectos similares basados en MediaPipe confirma que el uso de umbrales de confianza y estabilidad temporal es una práctica habitual para reducir falsos positivos en reconocimiento de gestos en tiempo real. | **Sin cambios.** Se valida la regla ya definida; no se encontró evidencia que sugiera modificarla en esta etapa. |

**Conclusión de la validación:** el modelado previo sigue siendo válido y no requiere cambios estructurales. El único ajuste (RF-08) es aditivo, de bajo costo, y ya estaba soportado por el modelo de datos existente, lo que valida la solidez del diseño de clases entregado en el corte anterior.

## 8. Gestión del código fuente y del proyecto

**Repositorio:** el código y los documentos del proyecto se gestionan en GitHub, en https://github.com/CamiloConde/SILVA, con acceso público para revisión del docente. El historial de commits documenta la evolución de los dos entregables anteriores (plantilla del proyecto de aula y modelado UML) y de este avance.

**Herramienta de gestión de proyecto:** el equipo aún no tenía una herramienta de gestión ágil configurada. Se recomienda **Trello**, por ser gratuita, suficiente para un equipo de 3 personas y compatible con el enfoque Kanban descrito abajo. *(Pendiente: crear el tablero y enlazarlo aquí una vez configurado por el equipo — ver estructura propuesta más abajo).*

**Metodología ágil:** se mantiene **Lean Software Development**, declarada desde la entrega anterior, implementada en la práctica mediante un **tablero Kanban** en Trello. Esta combinación se ajusta al proyecto por tres razones:

1. El desarrollo tiene un fuerte componente exploratorio (ajustar umbrales de confianza, probar el clasificador con distintas condiciones de iluminación), que encaja con el principio Lean de "decidir lo más tarde posible" y aprender mediante iteración corta, en vez de planear en detalle una arquitectura que aún depende de resultados experimentales.
2. El calendario del curso está organizado en cortes, no en sprints de duración fija; un tablero Kanban de flujo continuo (sin compromisos de sprint) se adapta mejor a ese ritmo que Scrum.
3. Con 3 integrantes, el overhead de ceremonias formales de Scrum (planning, daily, review, retro) no se justifica; Kanban con límites de trabajo en progreso (WIP) y una reunión semanal de sincronización es suficiente para mantener trazabilidad.

**Estructura propuesta del tablero:**

| Columna | Propósito | Límite WIP sugerido |
|---|---|---|
| Backlog | Historias y tareas priorizadas, no iniciadas | — |
| Por hacer (próxima iteración) | Subconjunto del backlog seleccionado para trabajar pronto | 5 |
| En progreso | Tareas que un integrante está desarrollando activamente | 3 |
| En revisión | Tareas terminadas, pendientes de validación por otro integrante | 2 |
| Hecho | Tareas completadas y verificadas | — |

Cada tarjeta del backlog (sección 9.4, a completar cuando el tablero esté creado) corresponderá a una historia de usuario o a una tarea técnica derivada de los requerimientos de la sección 5. Las reuniones de seguimiento se realizarán semanalmente entre los 3 integrantes, y quedarán registradas en la tabla de seguimiento del documento consolidado del proyecto de aula.

**Historias de usuario (para incorporar al backlog del tablero):**

- **HU-01:** Como persona sorda, quiero que la aplicación reconozca mi seña estática y la muestre como letra en pantalla, para poder comunicarme por escrito sin depender de un intérprete. *(RF-01 a RF-05)*
- **HU-02:** Como persona oyente sin conocimiento de LSC, quiero ver en tiempo real la traducción de la seña, para poder interpretar lo que la persona sorda está comunicando. *(RF-05)*
- **HU-03:** Como usuario, quiero recibir un aviso cuando la cámara no detecta mi mano, para poder ajustar mi posición frente a ella. *(RF-06)*
- **HU-04:** Como usuario, quiero detener la aplicación y que mi sesión quede guardada en el historial, para poder revisar lo que traduje anteriormente. *(RF-07)*
- **HU-05 (deseable):** Como usuario, quiero ver el nivel de confianza de cada predicción, para saber si debo repetir la seña. *(RF-08)*

---

## Referencias

Linares Munar, L. (2023, 24 de septiembre). "Colombia tiene porcentaje bajo en la implementación de los derechos de las personas sordas", Insor. *Infobae*. https://www.infobae.com/colombia/2023/09/24/colombia-tiene-porcentaje-bajo-en-la-implementacion-de-los-derechos-de-las-personas-sordas-insor/

Organización Mundial de la Salud. (2024). *Deafness and hearing loss* [ficha técnica]. https://www.who.int/news-room/fact-sheets/detail/deafness-and-hearing-loss

Jefferson0511. (2025). *sign-language-detector: Real-time ASL fingerspelling recognition with MediaPipe hand landmarks and a Random Forest classifier* [repositorio de software]. GitHub. https://github.com/Jefferson0511/sign-language-detector

Hand Talk. (s.f.). *Meet the Hand Talk sign language translator app*. https://www.handtalk.me/en/blog/meet-the-hand-talk-sign-language-translator-app/

SignAll Technologies. (s.f.). *SignAll 1.0: real-time American Sign Language translation*. Citado en Gestión (2020). https://gestion.pe/fotogalerias/app-ayuda-personas-sordas-interprete-virtual-lenguaje-signos-236772-noticia/

Instituto Nacional para Sordos [INSOR]. (2019). *Plan Estratégico Institucional 2019-2022* [citado en Linares Munar, 2023].

---

## Nota sobre el planteamiento general de estructura del repositorio para la entrega del MVP

Además de este avance, se propone (para discusión con el equipo, no aplicado aún) organizar el repositorio así de cara al tercer corte:

```
SILVA/
├── Planteamiento/        # (ya existe) documentos de las entregas 1 y 2, en PDF/Markdown
├── src/                  # código fuente de la aplicación (cuando inicie la construcción)
├── tests/                # pruebas funcionales y unitarias (sección 10.3 de la plantilla)
├── data/ o modelos/       # dataset de landmarks y modelo entrenado (modelo_senas.pkl)
├── docs/                 # capturas, evidencias de pruebas, diagramas exportados como imagen
└── README.md             # instrucciones de instalación/ejecución (sección 10.5 de la plantilla)
```

Esto separa claramente el material de planteamiento/documentación (ya versionado) del código que se irá agregando a partir de ahora, y deja lista la estructura que pedirá la evidencia del tercer corte (repositorio con instrucciones de instalación, pruebas y despliegue). Quedo atento a si quieren que cree esta estructura de carpetas ya mismo o la dejamos para cuando arranque la construcción del código.
