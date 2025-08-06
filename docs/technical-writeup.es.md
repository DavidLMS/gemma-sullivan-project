# Gemma Sullivan Project - The Technical Writeup

El Gemma Sullivan Project surge inspirado por la siguiente cita de Katriona O'Sullivan (autora de Poor):

> We need equity in education, not equality. If someone can’t see straight because the world is falling in around them, we need to raise them up to clearer skies.

Esta frase encapsula perfectamente el desafío educativo de nuestro tiempo: no se trata solo de proporcionar los mismos recursos a todos, sino de reconocer que cada estudiante enfrenta circunstancias únicas que pueden obstaculizar su aprendizaje. Algunos necesitan que les "elevemos hasta cielos más despejados" para poder ver con claridad.

¿Cómo podríamos utilizar Gemma 3n, capaz de ejecutarse en casi cualquier dispositivo de consumo, para asegurar el aprendizaje de los estudiantes en prácticamente cualquier circunstancia? Ya sea en emergencias temporales como una caída de la red eléctrica, en campos de refugiados por alguna guerra, en zonas rurales aisladas, o en cualquier sitio donde la cobertura de Internet sea un problema o simplemente no exista.

La respuesta tradicional ha sido esperar a que mejoren las condiciones: más conectividad, más infraestructura, más recursos. Pero ¿y si pudiéramos invertir este planteamiento? ¿Y si la educación pudiera adaptarse a las condiciones existentes, por adversas que sean?
Aquí es donde Gemma 3n representa un cambio paradigmático. Su capacidad de ejecutarse localmente en dispositivos de consumo estándar—smartphones, tablets, laptops básicos—abre posibilidades que hasta ahora eran impensables. No necesitamos conexión a la nube, no dependemos de servidores remotos, no requerimos infraestructura compleja. El conocimiento y la capacidad de generar experiencias educativas personalizadas pueden residir directamente en las manos del estudiante.

El Gemma Sullivan Project pretende ser una propuesta que permita abrir el debate sobre las mejores vías para conseguir esta democratización radical de la educación. No se trata solo de una solución técnica, sino de reimaginar cómo puede ocurrir el aprendizaje cuando eliminamos las barreras tradicionales de conectividad e infraestructura.

Hemos pensado cuál sería la mejor forma de abordar este desafío, no solo desde el punto de vista técnico, sino también pedagógico. Por eso, hemos descrito los [principios pedagógicos del proyecto](https://davidlms.github.io/gemma-sullivan-project/docs/pedagogical-foundations.es), que fundamentan cada decisión de diseño. Pero en este writeup nos centraremos específicamente en los aspectos técnicos: cómo hemos logrado crear un sistema que funciona de manera completamente offline, cómo hemos "domesticado" las generaciones de un modelo de lenguaje pequeño para crear experiencias educativas coherentes y personalizadas, y cómo hemos resuelto los desafíos únicos que surgen al construir un ecosistema educativo verdaderamente autónomo.

## Tabla de Contenidos

- [Demo en vivo](#demo-en-vivo)
- [Arquitectura del proyecto](#arquitectura-del-proyecto)
    - [La aplicación del estudiante](#la-aplicación-del-estudiante)
        - [Backend](#backend)
        - [Frontend](#frontend)
    - [La aplicación del tutor](#la-aplicación-del-tutor)
        - [Backend](#backend-1)
        - [Frontend](#frontend-1)
        - [Flujo de sincronización](#flujo-de-sincronización)
    - [Decisiones arquitectónicas clave](#decisiones-arquitectónicas-clave)
        - [Offline-First por diseño](#offline-first-por-diseño)
        - [Arquitectura híbrida de IA](#arquitectura-híbrida-de-ia)
        - [Asincronía no-bloqueante](#asincronía-no-bloqueante)
    - [Nota sobre el estado del código](#nota-sobre-el-estado-del-código)
- [Uso de Gemma 3n](#uso-de-gemma-3n)
    - [Usos de Gemma 3n en la Student App](#usos-de-gemma-3n-en-la-student-app)
        - [Generación de material de estudio](#generación-de-material-de-estudio)
        - [Generación de preguntas](#generación-de-preguntas)
        - [Retroalimentación de las preguntas](#retroalimentación-de-las-preguntas)
        - [Generación de retos](#generación-de-retos)
        - [Retroalimentación de los retos](#retroalimentación-de-los-retos)
        - [Función Discover](#función-discover)
    - [Uso de Gemma 3n en la Tutor App](#uso-de-gemma-3n-en-la-tutor-app)
        - [Generación de informes del tutor](#generación-de-informes-del-tutor)
- [Retos del desarrollo](#retos-del-desarrollo)
    - [Aprendizaje de nuevas tecnologías](#aprendizaje-de-nuevas-tecnologías)
    - [El mayor desafío: "Domesticar" Gemma 3n](#el-mayor-desafío-domesticar-gemma-3n)
        - [Nivel 1: La inferencia de Gemma 3n](#nivel-1-la-inferencia-de-gemma-3n)
        - [Nivel 2: Prompt Engineering](#nivel-2-prompt-engineering)
        - [Nivel 3: Parsing inteligente](#nivel-3-parsing-inteligente)
        - [Nivel 4: Sistema de reintentos resiliente](#nivel-4-sistema-de-reintentos-resiliente)
- [Conclusión](#conclusión)
    - [Nuestra visión](#nuestra-visión)

## Demo en vivo

Para experimentar directamente con el sistema que describiremos en este writeup, hemos desplegado ambas aplicaciones:

- Aplicación del estudiante: https://student.learningwithmachines.com
- Aplicación del tutor: https://tutor.learningwithmachines.com

Ambas aplicaciones incluyen un botón de "Reset" que permite cargar contenido educativo de ejemplo y restablecer el sistema a un estado inicial conocido. Esto facilita la exploración del proyecto sin necesidad de registro o configuración previa, cumpliendo así con los requisitos del hackathon de proporcionar demos públicamente accesibles. Cualquier persona puede acceder, experimentar con las funcionalidades, y comprender cómo funcionaría el sistema en un entorno real de aprendizaje.

## Arquitectura del proyecto

En Gemma Sullivan Project tenemos dos aplicaciones independientes: la **student app** y la **tutor app**. La segunda es totalmente opcional, en el caso de que los estudiantes puedan contar con un tutor al que acudir en momentos puntuales, lo cual es evidentemente la situación más ideal. Sin embargo, la student app puede funcionar completamente autónoma, lo que es fundamental para nuestro objetivo de democratizar la educación en cualquier circunstancia.

### La aplicación del estudiante

La **student app** es la aplicación a la que el estudiante tiene acceso, **pensada prioritariamente para visualizarse en un smartphone**, aunque es completamente funcional en tablets y ordenadores. Cada estudiante tendrá su propia instancia, que podría ejecutarse en smartphones usando Google AI Edge, un dispositivo Jetson, o cualquier PC o portátil con capacidades mínimas.

Actualmente funciona sobre la librería **Transformers** como base y sobre **MLX-VLM** de forma prioritaria en el caso de que el equipo sea compatible con Apple Silicon. La adaptación a otros motores de inferencia es muy sencilla gracias a nuestro diseño modular del `model_service.py`.

#### Backend

La arquitectura del backend se divide en varios componentes clave:

**Núcleo del sistema:**

- `api_server.py`: Servidor principal FastAPI que expone todos los endpoints REST y maneja **Server-Sent Events (SSE)** para actualizaciones en tiempo real.
- `model_service.py`: Servicio genérico para interacción con modelos de IA, soportando Transformers y MLX.
- `feedback_queue.py`: Sistema asíncrono de colas que evita bloqueos durante generaciones largas de IA.

**Servicios educativos especializados:**

- `discovery_service.py`: Implementa el modo Discovery con metodología socrática multimodal.
- `automatic_questions_service.py`: Generación inteligente de preguntas con progresión de dificultad.
- `student_profile.py`: Gestión centralizada de perfiles de estudiantes con personalización.
- `sync_client.py`: Cliente de sincronización bidireccional con la tutor app.

**Pipeline de contenido:**

En el backend **solamente es necesario añadir simples archivos `.txt`** con el contenido que el estudiante debe aprender. Estos contenidos serán la **fuente de verdad única**. El sistema procesa estos archivos siguiendo esta pipeline:

```
content/inbox/          # Archivos .txt de entrada
    ↓
content/processed/      # Archivos procesados y validados
    ↓
content/generated/      # Contenido generado por IA
├── learn/
│   ├── textbooks/     # Formato académico estructurado
│   └── stories/       # Formato narrativo atractivo
├── practice/          # Preguntas de diferentes tipos
└── experiment/        # Retos y desafíos complejos
```

A partir de estos archivos, **Gemma 3n generará los contenidos de aprendizaje personalizados** al idioma, nivel e intereses del estudiante, así como las preguntas progresivas y los retos multidisciplinares que se le ofrecen.

#### Frontend

El frontend está construido en **React + TypeScript** con una arquitectura de componentes especializados:

**Componente raíz:**

- `App.tsx`: Maneja el estado global, SSE integration, onboarding flow y navegación.

**Módulos de aprendizaje:**

- `Learn.tsx`: Visor de contenido educativo con soporte dual-format (textbook/story) y tracking de progreso granular.
- `Practice.tsx`: Sistema de práctica con 4 tipos de preguntas, filtrado inteligente y feedback inmediato.
- `Experiment.tsx`: Módulo de desafíos creativos con submissions multimodales (texto + canvas + imágenes).
- `Discover.tsx`: Exploración multimodal del entorno con metodología socrática.

**Componentes de soporte:**

- `MainMenu.tsx`: Navegación principal con diseño bento-grid y efectos 3D modernos.
- `ProfileSetup.tsx`: Configuración completa de perfil con validación.
- `QuestionInterface.tsx`: Interfaz genérica reutilizable para todos los tipos de preguntas.

La comunicación con el backend se realiza mediante **REST API + Server-Sent Events**, permitiendo actualizaciones en tiempo real sin bloquear la interfaz durante las generaciones de IA.

### La aplicación del tutor

La **aplicación del tutor** permite que una persona supervise el aprendizaje de un conjunto de estudiantes, **pensada para visualizarse en la web** de un equipo de escritorio o portátil. Su función es triple: gestionar contenidos, asignar materiales específicos a estudiantes, y monitorizar el progreso educativo.

#### Backend

**Núcleo del sistema:**

- `api_server.py`: Servidor principal FastAPI que maneja gestión de estudiantes, contenido y sincronización.
- `sync_service.py`: Servicio robusto de sincronización bidireccional que incluye discovery automático en red local.
- `report_service_factory.py`: Factory pattern para seleccionar dinámicamente servicios de generación de reportes. De momento solo disponible el de Ollama.

**Generación de reportes con Gemma 3n:**

- `ollama_service.py`: Generación de reportes usando Ollama + Gemma 3n local.

**Gestión de datos:**
```
students/                    # Directorio de estudiantes
├── {student_id}.json       # Configuración del estudiante
└── {student_id}/           # Directorio individual
    ├── content/            # Contenido asignado
    ├── logs/               # Logs de actividad
    ├── generated/          # Contenido generado por IA
    ├── submissions/        # Envíos y experimentos
    └── discovery/          # Sesiones de exploración
reports/                    # Reportes generados por IA
```

#### Frontend

**Componente principal:**

- `App.tsx`: Aplicación principal que integra gestión de estudiantes, asignación dual-list, control WiFi y file management.

**Gestión de contenido:**

- `FileBrowser.tsx`: Navegador avanzado para explorar datos de estudiantes con preview integrado.
- `FileUpload.tsx`: Subida de archivos con drag & drop y validación client-side.
- `ContentPreview.tsx`: Vista previa modal de archivos de contenido.

#### Flujo de sincronización

Cuando una aplicación de estudiante se levanta, **se puede configurar la URL** (local o remota) en la que intentará comunicarse con la aplicación del tutor. El proceso funciona así:

1. **Discovery automático**: La tutor app puede activar un servicio de discovery UDP que permite a las student apps encontrarla automáticamente en la red local.
2. **Handshake de sincronización**: Cuando un estudiante decide sincronizar, se establece una conexión HTTP temporal.
3. **Intercambio bidireccional**: En una sola operación ocurren dos transferencias simultáneas:
   - **Upstream**: El estudiante envía todos sus registros de aprendizaje, contenido generado, submissions y sesiones de discovery.
   - **Downstream**: El tutor envía los contenidos que haya asignado específicamente a ese estudiante.
4. **Generación asíncrona de reportes**: Automáticamente, Gemma 3n a través de Ollama genera un informe que resume al tutor el desempeño del estudiante desde la última sincronización.

El tutor puede **quedarse solamente con la información del reporte** para una visión rápida, o **analizar manualmente todo** lo que ha generado la aplicación del estudiante y sus interacciones detalladas.

### Decisiones arquitectónicas clave

#### Offline-First por diseño

La arquitectura está **fundamentalmente diseñada para funcionar offline**. La sincronización es una funcionalidad añadida, no un requisito. Esto significa:

- **Student apps** pueden funcionar indefinidamente sin conectividad.
- **Contenido y estado** se persiste localmente en ambas aplicaciones.
- **Generaciones de IA** ocurren completamente en el dispositivo local.
- **Sincronización** es oportuna y eficiente, minimizando el tiempo de conexión requerido.

#### Arquitectura híbrida de IA

Para maximizar el rendimiento y las capacidades, utilizamos **diferentes motores de IA** para diferentes propósitos:

- **Student App**: Transformers/MLX-VLM para capacidades multimodales (texto + visión).
- **Tutor App**: Ollama para generación optimizada de reportes (solo texto, máximo rendimiento).

#### Asincronía no-bloqueante

**Server-Sent Events** y **task queues** aseguran que las aplicaciones permanezcan responsivas durante las generaciones de IA:

- **Generaciones rápidas** (feedback de preguntas): Bloquean temporalmente para feedback inmediato.
- **Generaciones lentas** (contenido, retos, reportes): Se procesan en background.
- **Estado consistente**: El frontend se actualiza automáticamente cuando las generaciones se completan.

### Nota sobre el estado del código

Es importante mencionar que **el código no está todo lo ordenado que debería**. Hemos podido dedicarle tiempo limitado a la organización y refactorización, lo cual **también refleja el espíritu de un hackathon**: crear una prueba de concepto funcional que demuestre la viabilidad de la idea más que un producto pulido para producción.

Si el proyecto genera interés en la comunidad, **tenemos intención de realizar una refactorización completa** que mejore la distribución del código, simplifique la configuración, añada testing comprehensivo, y optimice el rendimiento. Las bases arquitectónicas están sólidas; lo que necesita es tiempo para pulir la implementación.

Esto es especialmente cierto en áreas como:
- **Configuración unificada** entre ambas aplicaciones.
- **Error handling** más granular y user-friendly. 
- **Testing coverage** para validar todos los flujos educativos.
- **Performance optimizations** para dispositivos con recursos limitados.
- **Documentation** técnica más detallada para contributors.

La funcionalidad core está completamente desarrollada y probada, pero reconocemos que hay trabajo de ingeniería adicional necesario para convertir esta prueba de concepto en un producto robusto y escalable.

## Uso de Gemma 3n

El corazón del Gemma Sullivan Project reside en el uso inteligente del modelo Gemma 3n. A continuación enumeramos y explicamos detalladamente los diferentes usos que se hace de Gemma 3n en ambas aplicaciones.

### Usos de Gemma 3n en la Student App

#### Generación de material de estudio

La única fuente de verdad que utiliza el Gemma Sullivan Project son los archivos `.txt` de contenido. Estos son archivos que alguien prepara (un tutor, un familiar, una ONG o, en definitiva, cualquier persona) y constituyen lo que el estudiante debe aprender. 

Cuando un archivo de contenido se coloca en la carpeta `inbox` del student-app (manualmente o sincronizando con la app del tutor), automáticamente Gemma 3n comienza a generar un nuevo bloque en la zona **Learn** de la aplicación del estudiante. 

El modelo adapta el contenido al nivel, idioma e intereses del perfil del estudiante, generando una explicación de dicho contenido en **dos formatos distintos**:

- **Libro de texto**: Más formal, estructurado académicamente
- **Cuento**: En forma de narrativa, más atractivo y accesible

Esta dualidad permite que el estudiante tenga dos opciones para aprender sobre el mismo contenido, adaptándose a diferentes preferencias de aprendizaje y momentos de estudio. Algunos estudiantes prefieren la rigurosidad del formato textbook, mientras que otros se conectan mejor con el aprendizaje narrativo. También encontraremos estudiantes que quieran enfocar el estudio con ambos formatos.

#### Generación de preguntas

Una vez que el estudiante accede a algún contenido en **Learn**, se empiezan a generar automáticamente preguntas de distinto tipo sobre ese contenido en la sección **Practice**. 

El sistema implementa una **progresión adaptativa de dificultad**: se empiezan generando preguntas fáciles, pero si el estudiante contesta correctamente todas las fáciles, se generarán nuevas preguntas cada vez más difíciles. Esta escalabilidad asegura que el estudiante siempre tenga un desafío apropiado a su nivel actual.

Los tipos de preguntas generadas incluyen:

- **Multiple choice**: Preguntas de opción múltiple.
- **Fill the blank**: Completar espacios en blanco.
- **Short answer**: Respuestas cortas.
- **Free recall**: Respuestas abiertas.

Por cada contenido al que acceda el estudiante, las preguntas se van mezclando cuando el estudiante quiera practicarlas, aprovechando los beneficios científicamente probados de la **práctica intercalada** (*interleaved practice*).

#### Retroalimentación de las preguntas

Cuando el estudiante contesta una pregunta de los siguientes tipos (todas menos las de opción múltiple):

- **Fill the space**.
- **Short answer**.
- **Free recall**.

Entonces, Gemma 3n proporciona retroalimentación inmediata y personalizada. Esta es la **única generación que necesitamos que sea lo más inmediata posible** en el diseño del proyecto, ya que la retroalimentación instantánea es importante para el proceso de aprendizaje, además de bloquear durante esta generación el uso de la aplicación.

El modelo analiza la respuesta del estudiante y proporciona feedback constructivo, explicando por qué una respuesta es correcta o incorrecta, y ofreciendo orientación para mejorar la comprensión.

#### Generación de retos

De la misma forma que ocurre con las preguntas, cuando un estudiante accede a un contenido en **Learn**, se generan en segundo plano propuestas de retos (trabajos y proyectos más complejos). 

El estudiante accede a **Experiment** y puede aceptar un reto o rechazarlo para recibir otra propuesta. Si se agotan las propuestas disponibles, se vuelve a ejecutar automáticamente una nueva generación de retos.

Una característica única es que los retos pueden ser **multidisciplinares**, teniendo en cuenta todos los contenidos que el estudiante haya consultado en Learn, permitiendo conexiones creativas entre diferentes áreas de conocimiento.

#### Retroalimentación de los retos

El estudiante puede enviar como submission de un reto (dependiendo de lo que el reto demande):

- **Un texto** explicativo o ensayo.
- **Un dibujo** realizado sobre un canvas integrado.
- **Imágenes adjuntas** (fotografías de productos reales, experimentos, creaciones físicas).

Gemma 3n proporciona feedback del reto teniendo en cuenta **todos esos elementos multimodales**. Se utiliza, por lo tanto, su capacidad de visión tanto para el canvas como para las imágenes adjuntas, permitiendo una evaluación holística del trabajo del estudiante.

Como esta retroalimentación es más compleja y computacionalmente intensiva, la inferencia es más lenta, por lo que se ejecuta en el background, permitiendo al estudiante continuar con otras actividades y volver a consultar el feedback en otro momento.

A partir del feedback recibido, el estudiante puede elegir volver a mejorar el mismo reto y hacer otra entrega, o dar la submission por concluida, fomentando un proceso iterativo de mejora.

#### Función Discover

En esta función, el estudiante puede explorar y hacerse preguntas sobre cualquier elemento de su entorno inmediato. El objetivo es **conectar el aprendizaje con su realidad circundante**.

El proceso comienza con una fotografía y una pregunta sobre el objeto o situación que esté fotografiando. Gemma 3n analizará la imagen, pero no proporcionará respuestas directamente (ya que correríamos muchos riesgos de alucinaciones), sino que implementa un **enfoque socrático**:

1. El modelo "piensa" cinco posibles respuestas o enfoques.
2. Ofrece al estudiante cuatro preguntas para elegir sobre qué aspecto quiere indagar.
3. Cuando elija una pregunta, en función de la elección, Gemma 3n propone otras cuatro preguntas más específicas.
4. Este proceso continúa iterativamente.

Por defecto (configurable de forma global), el sistema propone cuatro preguntas hasta cinco iteraciones máximo. Después de la quinta elección, Gemma 3n revela al estudiante las cinco respuestas pensadas inicialmente, con una descripción detallada de cada una, animando al estudiante a elegir una.

Es importante destacar que estas respuestas **no tienen por qué ser la respuesta correcta**, pero ayudarán al estudiante a indagar y desarrollar su curiosidad científica. Si se conecta con un tutor, éste podrá revisar lo que ha hecho el estudiante en Discover, conociendo sus intereses y proporcionándole retroalimentación correcta si lo considera necesario.

### Uso de Gemma 3n en la Tutor App

#### Generación de informes del tutor

El único uso que se le da a Gemma 3n en la aplicación del tutor es la **generación automatizada de informes de rendimiento**. 

Gemma 3n, utilizando Ollama para la inferencia, trabaja de forma asíncrona en segundo plano. Después de sincronizar los datos entre estudiante y tutor, el modelo procesa los registros del estudiante (que están en formato **xAPI**, un estándar internacional para analítica de aprendizaje) y genera un informe comprehensivo con datos valiosos para el tutor.

Estos informes incluyen:

- **Resumen ejecutivo** del progreso del estudiante.
- **Análisis de patrones** de aprendizaje.
- **Identificación de fortalezas** y áreas de mejora.
- **Recomendaciones pedagógicas** personalizadas.

Además, en el futuro estas sentencias xAPI podrían integrarse en un Learning Record System (LRS) para centralizar las acciones del estudiante en otros contextos educativos, como aulas virtuales o sistemas de gestión de aprendizaje, proporcionando una visión completa del progreso educativo del estudiante a través de diferentes plataformas.

## Retos del desarrollo

Durante todo el desarrollo, los retos han sido continuos. Gracias a la asistencia de modelos de lenguaje como Gemini 2.5 Pro para programación, nos hemos atrevido con todo tipo de tecnologías desconocidas anteriormente, dado que el principal objetivo de participar en este hackathon ha sido precisamente **experimentar con nuevas opciones** y explorar los límites de lo posible con Gemma 3n.

### Aprendizaje de nuevas tecnologías

Nunca antes habíamos creado un frontend usando React y, sin embargo, pensamos que ha sido un acierto elegirlo. Se ha ajustado perfectamente a la experiencia de usuario que necesitábamos para el estudiante: una aplicación fluida, responsiva y capaz de manejar actualizaciones en tiempo real.

La validación más interesante de nuestro diseño UX vino de una fuente inesperada: una aplicación que ha podido utilizar sin problemas hasta un modelo de lenguaje con acceso a funciones de computer use. De hecho, para **verificar la accesibilidad y usabilidad** de la aplicación, la hemos sometido a estos sistemas con diferentes historias de usuario para comprobar lo intuitivo que era su uso. Si un modelo de IA puede navegar nuestra interfaz siguiendo instrucciones de usuario, consideramos que hemos logrado un diseño al menos mínimamente intuitivo.

Otro de los retos técnicos más complejos ha sido la **gestión de la asincronía**. En muchos casos, Gemma 3n está generando contenidos, preguntas, retos y feedback en segundo plano, mientras que el estudiante puede seguir utilizando la aplicación sin interrupciones.

Además, queríamos que si se completaba un proceso (por ejemplo, cuando un contenido terminaba de generarse), el estudiante no tuviera que recargar la página para comprobar su finalización, sino que apareciera disponible directamente en su interfaz. 

Para conseguir esta experiencia fluida, hemos tenido que aprender e implementar:

- **Server-Sent Events (SSE)**: Para notificaciones en tiempo real del backend al frontend.
- **Asincronía no-bloqueante**: Utilizando threading y async/await para mantener la aplicación responsiva.
- **Sistema de colas de tareas**: Para manejar múltiples generaciones de IA simultáneas.
- **Estados de aplicación consistentes**: Sincronización entre backend y frontend sin conflictos.

Lo mismo hemos aplicado al proceso de **sincronización entre estudiante y tutor**, minimizando el tiempo necesario de conexión entre ambos. La sincronización debe ser rápida y eficiente, especialmente considerando que podría ocurrir en redes con limitaciones de ancho de banda.

### El mayor desafío: "Domesticar" Gemma 3n

Sin embargo, sin ninguna duda, el mayor reto ha sido **"domesticar" las generaciones de un modelo de lenguaje pequeño** como Gemma 3n para crear experiencias educativas coherentes y predecibles.

El estudiante nunca interactúa directamente con el modelo en una interfaz tipo chatbot, sino que lo utilizamos en determinadas funciones específicas para generar aquello que un código tradicional nunca podría abarcar: contenido personalizado, feedback contextual, y experiencias de aprendizaje adaptativas.

Pero controlar la indeterminación inherente de un modelo de lenguaje no es fácil. Para un código tradicional, la **mayor virtud** de estos modelos (su creatividad y flexibilidad) es, al mismo tiempo, el **mayor inconveniente** (su impredecibilidad).

Con el objetivo de abordar este problema fundamental, lo hemos dividido en **cuatro niveles de entendimiento del modelo**, que a su vez se convierten en cuatro niveles de control del mismo. Esta aproximación sistemática nos ha permitido crear un sistema robusto y confiable.

#### Nivel 1: La inferencia de Gemma 3n

El desarrollo se ha realizado en un MacBook Pro M3 Pro de 18GB de memoria, realizándose múltiples pruebas de inferencia del modelo Gemma 3n. **Perdimos mucho tiempo** averiguando por qué el modelo se comporta de diferente forma en distintos motores de inferencia, un problema más común de lo que inicialmente pensábamos.

En nuestro dispositivo de desarrollo, la mejor inferencia (a nivel de rendimiento y rapidez) la realizaba el motor de **LMStudio**, pero no queríamos que su instalación fuera un requisito del proyecto. Además, no sabíamos si sería igual de efectiva en otros dispositivos con diferentes configuraciones de hardware.

Nos decantamos por la librería **Transformers**, que ya se ha convertido prácticamente en un estándar de fiabilidad en el ecosistema de IA. Nos hubiese gustado implementar **Google AI Edge**, pero aún no teníamos ejemplos de funcionamiento estable en dispositivos que no fueran Android.

El problema de Transformers es que ofrecía una inferencia excesivamente lenta para nuestras necesidades de desarrollo iterativo. Dado que lo estábamos ejecutando en un dispositivo con soporte MPS (Metal Performance Shaders), implementamos la opción de activar **MLX** usando la librería [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) como optimización para Apple Silicon.

Sin embargo, encontramos su uso problemático. A pesar de que la inferencia funcionaba y era notablemente más rápida, **no se ajustaba para nada a la salida** que daba con la librería Transformers. La diferencia era sutil, pero suficiente para que fuera un problema crítico: en mlx-vlm, Gemma 3n nunca se ajustaba al formato de salida propuesto, ignorando sistemáticamente nuestras instrucciones de formato XML.

Llegamos a [notificar al desarrollador](https://github.com/Blaizzy/mlx-vlm/issues/435#issuecomment-3114294923) este comportamiento inconsistente y, efectivamente, descubrimos que se trataba de un bug conocido que está en vías de solución.

**Ollama** también daba muy buen rendimiento en términos de velocidad e estabilidad. Pero presentaba un problema fundamental para nuestro caso de uso: **no tenemos acceso a la capacidad de visión**, que es imprescindible para el funcionamiento de las funciones de feedback multimodal de Experiment y el modo Discover.

La visión sí funcionaba correctamente en Transformers y mlx-vlm, creando una situación donde tuvimos que tomar decisiones arquitectónicas complejas.

Por lo tanto, actualmente la inferencia de Gemma 3n se realiza usando una **arquitectura híbrida**:

- **En la student-app**: Usando la librería Transformers como base, con la opción de activar mlx-vlm si el dispositivo es compatible con MPS (aunque para que funcione correctamente se tendrá que esperar a la nueva versión que solucione el bug).
- **En la tutor-app**: Usando Ollama, ya que está pensada para ejecutarse en un servidor o equipo de escritorio donde la visión no es necesaria y el rendimiento es prioritario.

#### Nivel 2: Prompt Engineering

El objetivo del prompt engineering que teníamos que realizar para desarrollar las funcionalidades deseadas era **doble**:

1. **Calidad del contenido**: Que Gemma 3n proporcionara el mejor contenido posible para cada funcionalidad específica.
2. **Estructura procesable**: Que el formato de salida fuese fácil de procesar programáticamente y resiliente a posibles errores.

Han sido necesarias **múltiples evaluaciones** para conseguir los resultados que buscábamos, y posiblemente este aspecto pueda seguir mejorándose en el futuro. Por eso hemos separado los prompts del código, escribiéndolos en archivos `.txt` independientes con **variables dinámicas** en su contenido, permitiendo cambiar programáticamente valores como los datos del estudiante, nivel de dificultad, o idioma.

Sin embargo, tenemos algunas **lecciones aprendidas críticas** para compartir, fruto de cientos de iteraciones:

- **Eficiencia de tokens**: Es necesario que el número de tokens de entrada sea lo menor posible para hacer la inferencia más eficiente, sobre todo cuando se necesita una respuesta en tiempo real (como en el feedback de preguntas).

- **XML como formato óptimo**: El formato de salida que nos ha resultado más fiable con Gemma 3n es el **XML simplificado**.

- **Simplicidad estructural**: La estructura del XML debe mantenerse lo más simple posible, evitando múltiples anidaciones que confunden al modelo.

- **Evitar atributos XML**: Los atributos en las etiquetas XML deben evitarse completamente. A menudo Gemma 3n "se niega" a contestar (respuesta en blanco) si debe escribir un XML con atributos en sus etiquetas.

- **Proximidad de contenido**: El contenido fuente (la "fuente de verdad" sobre la que va a generarse cualquier estructura) y las instrucciones de formato de salida deben estar lo más cerca posible del final del prompt para maximizar la atención del modelo.

#### Nivel 3: Parsing inteligente

El parsing es lo que nos permite **convertir una salida de un modelo de lenguaje** a valores que podemos almacenar en variables y usar en código estructurado tradicional. Para ello, hemos construido parsers especializados para cada una de las llamadas que procesan la salida en XML.

Hemos estudiado meticulosamente los prompts y las salidas, detectando que Gemma 3n a veces **cambia ligeramente el nombre** de las etiquetas XML que se solicitan. Es sorprendentemente creativo en este aspecto, utilizando sinónimos o variaciones que mantienen el significado pero rompen el parsing estricto.

De esta forma, hemos desarrollado **parsers más inteligentes** que aceptan como válidas etiquetas que no tienen que coincidir exactamente con las pedidas, pero que son lo suficientemente claras como para extraer su contenido. Por ejemplo, si pedimos `<progression>` pero el modelo genera `<progresion>` o `<progrression>`, nuestro parser puede identificar y extraer el contenido correctamente.

Los parsers también incluyen **validación de estructura** para detectar XML malformado, contenido faltante, o respuestas que no siguen el formato esperado, activando automáticamente el sistema de reintentos cuando es necesario.

#### Nivel 4: Sistema de reintentos resiliente

Cuando el resto de niveles falla, es necesario **controlarlo inteligentemente** para hacer un reintento. La mayoría de las generaciones sucede en segundo plano, por lo que no hay problema en volver a intentarlo hasta que la salida sea válida.

El número de reintentos es **configurable a nivel global** en ambas aplicaciones, considerando posibles limitaciones de energía, ya que los reintentos consumirán las baterías más rápidamente en dispositivos móviles. Esta flexibilidad es muy importante para despliegues en condiciones donde la energía es limitada.

En ocasiones donde es necesaria una generación más inmediata, como en la **retroalimentación de preguntas**, siempre podemos hacer una comparación exacta con la respuesta esperada. Es difícil que coincida perfectamente con lo que ha escrito el estudiante, pero le proporcionará alguna respuesta y le permitirá seguir interactuando con la aplicación sin interrupciones frustrantes.

Los reintentos que realizamos tienen **capacidad resiliente inteligente**. Por ejemplo, en la generación de preguntas, exigimos un número concreto de preguntas de cada tipo. Si el modelo no las genera todas en el primer intento, no volvemos a realizar un reintento completo hasta que estén todas (algo que hemos encontrado que es bastante infrecuente), sino que:

1. **Guardamos las válidas** del primer intento.
2. **Reintentamos buscando solo las faltantes**.
3. **Combinamos resultados** hasta completar el conjunto requerido.

Esta aproximación **conserva recursos computacionales** y mejora la eficiencia general del sistema, especialmente importante cuando se ejecuta en dispositivos con limitaciones de procesamiento.

## Conclusión

El Gemma Sullivan Project representa más que una implementación técnica; es una **prueba de concepto** de que la educación personalizada y de calidad puede existir independientemente de la infraestructura tradicional. Hemos demostrado que es posible crear un ecosistema educativo completamente autónomo que funciona en las condiciones más adversas, desde un smartphone en un campo de refugiados hasta una tablet en una zona rural sin conectividad.

A lo largo de este desarrollo, hemos conseguido varios **hitos técnicos significativos**:

- **Domesticación de un LLM pequeño**: Nuestro sistema de 4 niveles (inferencia, prompt engineering, parsing, reintentos) convierte la indeterminación de Gemma 3n en experiencias educativas predecibles y coherentes.

- **Arquitectura multimodal offline-first**: La integración de texto, visión y audio en un sistema que funciona completamente sin conexión a internet, aprovechando las capacidades únicas de Gemma 3n.

- **Personalización adaptativa**: Generación automática de contenido en múltiples formatos (textbook/story), preguntas de dificultad progresiva, y retos multidisciplinares que se adaptan al perfil individual del estudiante.

- **Sincronización inteligente**: Un sistema que permite la colaboración tutor-estudiante minimizando el tiempo de conexión necesario, crucial para entornos con limitaciones de conectividad.

Trabajar con Gemma 3n ha sido una experiencia reveladora. Es un **modelo verdaderamente increíble** que demuestra lo lejos que hemos llegado en la democratización de la inteligencia artificial. Es emocionante pensar que estamos tan cerca de llevar una inferencia más inteligente que nosotros mismos directamente en el bolsillo, **sin necesidad de conexión a Internet**.

Durante nuestras pruebas, hemos explorado las capacidades de **function calling** de Gemma 3n y los resultados son muy prometedores. Aunque aún no está al nivel de modelos más grandes, funciona considerablemente bien para tareas específicas. Estamos seguros de que este aspecto mejorará significativamente en futuras iteraciones, lo que abrirá **un nuevo campo de posibilidades educativas**.

Esta experiencia con function calling nos ha permitido vislumbrar el futuro de la educación asistida por IA. Hemos desarrollado proyectos complementarios que muestran hacia dónde podríamos dirigirnos:

- **[LearnMCP-xAPI](https://github.com/DavidLMS/learnmcp-xapi)**: Un servidor MCP que permite a los agentes de IA registrar y recuperar actividades de aprendizaje a través de Learning Record Stores compatibles con xAPI. Imaginen a Gemma 3n conectándose a este sistema para **"recordar" en cada interacción** qué sabe el estudiante, adaptando automáticamente sus explicaciones y desafíos basándose en el historial de aprendizaje completo.

- **[IPMentor](https://github.com/DavidLMS/ipmentor)**: Un servidor MCP con un conjunto de herramientas computacionales verificadas para tutorías de redes IPv4. Este proyecto demuestra cómo modelos como Gemma 3n pueden **enfocarse en su lado creativo y pedagógico**, delegando cálculos complejos y verificación matemática a herramientas especializadas que garantizan la exactitud.

Cuando Gemma 3n mejore su capacidad de function calling, podremos crear sistemas educativos donde el modelo mantenga **continuidad perfecta del aprendizaje** (via LearnMCP-xAPI), genere **ejercicios complejos verificados** (via herramientas como IPMentor), y se concentre en lo que mejor hace: **explicar, motivar, y adaptar la experiencia educativa** a cada estudiante individual.

Pero el valor real del proyecto trasciende lo técnico. Hemos creado un sistema que **invierte el paradigma educativo tradicional**: en lugar de esperar a que los estudiantes lleguen a la educación, llevamos la educación adaptativa directamente a ellos, dondequiera que estén.

Recordando las palabras de Katriona O'Sullivan que inspiraron este proyecto: *"We need equity in education, not equality. If someone can't see straight because the world is falling in around them, we need to raise them up to clearer skies."* 

El Gemma Sullivan Project es precisamente eso: una manera de **elevar a los estudiantes hasta cielos más despejados**, independientemente de las circunstancias que los rodeen. Ya no necesitan esperar a que mejoren las condiciones externas; el aprendizaje personalizado puede comenzar inmediatamente, con los recursos que tengan a mano.

### Nuestra visión

Este proyecto abre la puerta a un **nuevo modelo educativo distribuido** donde:

- **Cualquier dispositivo** puede convertirse en un tutor personal inteligente.
- **Cualquier persona** puede crear y distribuir contenido educativo de calidad.
- **Cualquier circunstancia** puede transformarse en una oportunidad de aprendizaje.
- **Cualquier comunidad** puede desarrollar su propio ecosistema educativo autónomo.

Proponemos que la comunidad educativa y tecnológica considere seriamente este enfoque. No se trata solo de una demostración técnica, sino de una **invitación a reimaginar** cómo puede ocurrir el aprendizaje en el siglo XXI.

Las herramientas están aquí. Gemma 3n y modelos similares han democratizado el acceso a la inteligencia artificial. Los dispositivos de consumo tienen la potencia necesaria. La metodología pedagógica ha sido probada. Solo necesitamos la **voluntad colectiva** de implementar soluciones que pongan la educación de calidad al alcance de todos, en todas partes, en todo momento.

El Gemma Sullivan Project es nuestro primer paso en esa dirección. La pregunta que queda es: **¿quieres formar parte en este camino hacia una educación verdaderamente universal?**

---

*El código completo, las demos en vivo, y toda la documentación técnica están disponibles para la comunidad bajo una licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.en). Porque la democratización de la educación solo es posible si democratizamos también las herramientas que la hacen posible.*
