# AUTOFABRICADOR

## R92B — Corrección del arte, acciones temporales, mapa y pixel art 16:9

**Prioridad AUTOFABRICADOR.** El videojuego original *La Luz de Bruma* R92B es un **candidato portable jugable, NO `ACTIVE`**. Conserva intactas las versiones anteriores y MMC7 sigue suspendido.

**Problemas reales tratados:** rayas geométricas del generador R91 eliminadas mediante reconstrucción de capas, personajes completamente redibujados a 48×96 píxeles por fotograma, 14 fotogramas por personaje, **69 capas OpenRaster editables** en 11 recursos. Estado de acciones reparado para vaciar verbo, cola, destino, ruta, diálogo e inventario seleccionado cuando termina una interacción; los objetos recogidos dejan de activarse y las operaciones repetidas son idempotentes. Fondos ocupan **145/180** del alto lógico (antes 130/180), HUD compacto ocupa 35/180; tecla M abre mapa ampliado, F11 alterna pantalla completa. El lienzo sigue **640×360 (16:9)** con ventana **1280×720 y escala entera 2×** para evitar rayas visuales de grosor desigual; filtro NEAREST.

**Aceptación original comprobada:** 35 controles jugables, 207 controles de walkboxes/navegación con 1.709 pasos simulados, 49 casos nuevos sobre acciones/menús, 136 regresiones existentes y 24 unitarias del validador reutilizable (**451 comprobaciones diferentes**). ZIP extraído y probado desde su raíz con 291 Godot PASS y 22 archivos artísticos SHA idénticos reconstruidos dos veces. Se descargaron 26 fuentes públicas desde GitHub, se reconstruyó la cadena R90→R91→R92 y se volvieron a ejecutar **291 casos Godot PASS**. Cinco capturas proceden de Godot OpenGL real, no son bocetos. **GitHub Actions configurado, sin ejecución remota aún certificada.**

**ZIP local:** `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R92B-ARTE-ACCIONES-16x9-PORTABLE-CANDIDATE.zip` (80.590.949 bytes), SHA-256 `a64eef2d9947fdcf60ada43fed92fbff756d55b6d0d5f7f2f33eade39343f36b`; copia idéntica en D. Está extraído y abierto con acceso directo **JUGAR - La Luz de Bruma R92B** en Escritorio. Godot 4.6.3 oficial incluido, sin instalación de Windows ni servicios.

- [Revisión, decisiones, pruebas, límites y recuperación R92B](design/R92B-QUALITY-STATE-ART-PORTABLE-CLOSEOUT.md)
- [Código original del juego R92B](examples/adventure-godot-r92b/LEEME-PRIMERO.md)
- [Motor de estados y renderizado](examples/adventure-godot-r92b/game.gd)
- [Generador artístico editable R92](examples/adventure-godot-r92b/art/r92_polish.py)
- [Auditoría reusable del AUTOFABRICADOR](development/autofab/adventure_quality_r92.py)
- [Workflow Windows para arte y 291 pruebas Godot](.github/workflows/r92b-godot-quality-169.yml)

**Límites:** estética aún sin aprobación humana, no probado en otro ordenador, faltan aceptación general de fábrica autónoma por IA local y la eventual exportación automática Pixelorama/arquitectura de salas Popochiu. El oráculo técnico no debe confundirse con calidad final comercial.

## R91B — Aventura Godot HD 16:9 y navegación segura (candidato jugable)

AUTOFABRICADOR, no MMC7. *La Luz de Bruma* R91B es una **aventura original, portable y jugable**, con tres habitaciones, el guardafaro de barba blanca, puzles, inventario, guardado/carga, 11 recursos PNG y **11 OpenRaster editables con 6+ capas**.

**Corrección del problema observado por el usuario:** el protagonista ahora camina con **AStarGrid2D sobre zonas válidas**, evita el anciano y obstáculos, conserva los pies dentro del suelo, no entra en mar/paredes al hacer clic, se escala según distancia y se ordena delante/detrás del NPC. El formato es 16:9 nativo **640×360, visualización 1280×720**, con más detalle de píxeles. F1 ayuda; F5 guardar; F9 cargar. Las pruebas tienen guardados aislados de la partida personal.

**Evidencia local y restaurada:** 35/35 pruebas jugables + 207/207 comprobaciones de movimiento (1.709 pasos) + 24 unitarias del módulo de navegación reutilizable + 136 regresiones anteriores; regeneración doble de 22 PNG/ORA byte a byte; ZIP extraído y probado; **22 fuentes públicas descargadas de GitHub** que reconstruyen el juego con otras 35 + 207 pruebas Godot. Godot oficial 4.6.3 incluido y SHA verificado. El flujo de GitHub Actions está configurado, **no ejecutado/aceptado remotamente**.

**ZIP portable verificado:** `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R91B-AVENTURA-HD-NAV-16x9-PORTABLE-CANDIDATE.zip`, SHA-256 `14b7ea48325cb41ff713cba27bc83ece5ae6fcd544b3327497cb8c1a2468e331`. En el PC está extraído y abierto con acceso directo **JUGAR - La Luz de Bruma R91B** en el Escritorio. La versión anterior R90C continúa intacta.

- [Detalles y límites de aceptación R91B](design/R91B-HD-NAV-PORTABLE-RELEASE.md)
- [Fuente R91B y documentación jugable](examples/adventure-godot-r91b/LEEME-PRIMERO.md)
- [Motor AStar y colisiones](examples/adventure-godot-r91b/adventure_nav_r91.gd)
- [Generador HD reproducible](examples/adventure-godot-r91b/art/r91_hd_art.py)
- [Auditoría reusable integrada en AUTOFABRICADOR](development/autofab/adventure_navigation_r91.py)
- [GitHub Actions de prueba manual](.github/workflows/r91b-godot-hd-nav.yml)

**Candidato, NO `ACTIVE`.** Falta aceptación visual humana del nivel artístico, prueba independiente en otro PC, Pixelorama export fiable, integración plena de salas Popochiu y demostrar la fabricación autónoma de una nueva aplicación completa por IA local; la narrativa de IA usada antes no cuenta como creación completa del juego.

## R90C — Resultados visuales reales, Godot 16:9, arte editable y ZIP portable

**Estado: CANDIDATE, NO ACTIVE.** La aventura original *La Luz de Bruma* se ejecuta en Godot 4.6.3 con resolución lógica **320 × 180 y salida 640 × 360 (16:9)**. Incluye tres habitaciones jugables, inventario, puzles y conversación; un protagonista y guardafaro de barba blanca con hojas de 14 fotogramas. Los **11 activos PNG con 4–5 capas OpenRaster editables** son originales y se han regenerado dos veces con hashes idénticos. La interfaz muestra los verbos **IR, MIRAR, COGER, USAR, HABLAR**, y admite F5/F9 para guardar y recuperar.

**Verificado:** 35/35 controles originales de Godot, tres contratos visuales técnicos (no aprobación artística humana), 22 PNG/ORA reconstruidos por SHA desde un ZIP extraído en carpeta aislada y 17 fuentes públicas descargadas de GitHub regeneradas y probadas con otras 35 condiciones. Las **cuatro capturas publicadas al usuario** son del motor Godot OpenGL 3.3 real en RTX 3060, no composiciones conceptuales. El resultado sigue siendo un pixel art técnico y **no alcanza todavía el acabado visual de una aventura comercial clásica**.

**ZIP local en el PC:** `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R90C-GODOT-16x9-VISUAL-PORTABLE-CANDIDATE.zip` (**80.349.755 bytes**), SHA-256 `0518ecc18b8c670e124d3366aecf751dbc3786dfe2b7b1a17bb2b2cfc2318529`. Contiene ejecutable Godot oficial, licencia, fuentes gráficas y **los lanzadores correctos en la raíz**: `INICIAR-JUEGO.cmd`, `ABRIR-EDITOR.cmd`, `PROBAR-PORTABILIDAD.cmd`. Copia de rescate SHA-idéntica en `D:\AUTOFABRICADOR-RESCATE\R90-VISUAL-FACTORY-20261108`. No requiere red, instalador, privilegios elevados ni autoinicio.

**Repositorios y pruebas:**
- [Fuente R90C, escenas, IA local acotada y generador determinista](examples/adventure-godot-r90c/LEEME-PRIMERO.md)
- [Arte 4–5 capas reeditable para once recursos](examples/adventure-godot-r90c/art/r90_illustrate.py)
- [Oráculo independiente de reconstrucción SHA](examples/adventure-godot-r90c/ci_verify_art.py)
- [Pruebas originales de 35 condiciones jugables Godot](examples/adventure-godot-r90c/qa/owner_test_r90.gd)
- [Workflow manual de GitHub Actions en Windows](.github/workflows/r90c-godot-art-169.yml) (configurado; ejecución remota en Actions aún sin recibo).

**Límites:** la IA GPU 7B anterior generó una parte narrativa original que funciona dentro del observatorio, **no todo el juego**; la fábrica general autónoma no ha superado aceptación de aplicaciones arbitrarias; falta aprobación visual humana, exportación automatizada desde Pixelorama y prueba independiente en otro equipo. MMC7 sigue suspendido. Ningún juego ajeno ni release protegido se ha promovido.

## R89E — Juego Godot portable, arte reconstruible y prueba local GPU

La prioridad es **AUTOFABRICADOR**; MMC7 continúa suspendido. La aventura original **La Luz de Bruma** usa formato **16:9 nativo** (320×180 de arte → 640×360 en pantalla), tres escenarios y un anciano original de barba blanca. El candidato R89E se ha probado desde un ZIP restaurado con el Godot oficial 4.6.3 y **30 casos jugables originales PASS**. Su código, diálogos y recursos se separan por identificador, con 11 PNG y 11 OpenRaster de dos capas. **Dos reconstrucciones limpias** produjeron los mismos SHA-256 para los 22 archivos artísticos. La IA local GPU 7B produjo y se verificó un fragmento narrativo original; **no** generó autónomamente el juego completo.

**Estado: CANDIDATE, NO ACTIVE.** La calidad artística sigue sin aprobación humana y los recursos continúan siendo una demostración procedimental. Godot y Popochiu 2.1.1 se validaron juntos en el editor de desarrollo, pero la distribución portable R89E utiliza el adaptador propio Godot y no incorpora el plugin ni sus fuentes tipográficas. Pixelorama 1.2.2 se ejecutó en entorno portable; su exportación automática aún no se verificó. Falta la aceptación independiente en otro ordenador.

- [Código original reproducible y juego Godot](examples/adventure-godot-r89e/LEEME-PRIMERO.md)
- [Motor jugable Godot 16:9](examples/adventure-godot-r89e/game.gd)
- [Generadores pixel art por capas](examples/adventure-godot-r89e/art/generate_assets.py) y [cuatro capas nuevas](examples/adventure-godot-r89e/art/generate_new_art.py)
- [Validador de reproducción artística con SHA](examples/adventure-godot-r89e/ci_verify_art.py)
- [Prueba independiente de 30 acciones](examples/adventure-godot-r89e/qa/standalone_owner_test.gd)
- [GitHub Actions manual para reconstruir y verificar Godot](.github/workflows/r89e-godot-repro-169.yml)

## Contrato vigente: aventuras 16:9 (R88B)

**Cambio explícito de formato:** los videojuegos nuevos usan **16:9 nativo**, no 4:3. Arte lógico 320×180 y presentación 640×360 con escalado pixelado, sin deformación. Las especificaciones 4:3 de R86/R87 solo sirven como documentación histórica.

Se ha construido una aventura original de dos escenas, «La Luz de Bruma», empaquetada y restaurada con **25 comprobaciones reales de Chrome** tanto en el proyecto como desde el ZIP extraído. Los sprites y fondos tienen fuentes OpenRaster editables; el CLI `adventure-visual-audit` aplica por defecto el contrato 16:9 y `adventure-visual-audit-r87` conserva la compatibilidad histórica. La calidad artística sigue pendiente de aprobación y este resultado **no demuestra fabricación autónoma completa por IA local**.

- [Especificación y límites 16:9](design/R88-WIDESCREEN-169-ACCEPTANCE.md)
- [Ejemplo original y generador por fuentes](examples/adventure-169-r88b/LEEME-PRIMERO.md)
- [Validador 16:9](development/autofab/adventure_visual_gate_r88.py)
- [Pruebas del validador](development/tests/test_adventure_visual_gate_r88.py)
- [Flujo de generación desde GitHub](.github/workflows/adventure-169-r88b.yml)

## Prioridad vigente: fabrica de aplicaciones y direccion artistica (R87)

AUTOFABRICADOR es el proyecto principal. MMC7 esta suspendido. Para aventuras clasicas, la calidad visual y la experiencia son una condicion independiente de la aprobacion funcional: la referencia es la estetica VGA de los noventa con personajes originales, no copias de sprites protegidos. El nuevo control **R87** audita PNG y maestros OpenRaster, hojas de animacion, interaccion y escena 320x200 con hashes, pero **NO aprueba automaticamente la calidad artistica ni implica juego completo**.

- [Contrato visual R86](design/ADVENTURE-VGA-VISUAL-UX-CONTRACT-R86.md)
- [Catalogo investigado e integracion R87](design/R87-ADVENTURE-REPOSITORIES-IMPLEMENTATION.md)
- [Modulo first-party R87](development/autofab/adventure_visual_gate.py) y [pruebas R87](development/tests/test_adventure_visual_gate_r87.py)

La integracion original en el ordenador se ha probado y restaurado; Godot, Popochiu y Pixelorama son candidatos externos aun sin instalacion comprobada. No confundir componentes aceptados con una fabrica universal ACTIVE.

Proyecto experimental de **factoría local de ingeniería de software asistida por IA**. Este repositorio es **público** para compartir código, documentación y facilitar la colaboración.

## Estado real

**R76: suite integrada de referencia, no fábrica autónoma universal.** Están demostrados un servidor local HTTP/SQLite con autenticación, una experiencia Canvas 2D, una escena WebGL2, integración puntual con Qwen 3.5 9B local y la compilación de un APK Android de depuración. La compilación del APK no prueba su funcionamiento en un dispositivo.

**R77: handoff de arquitectura.** Describe los seis motores que faltan para completar el ciclo de ingeniería: interpretar y diseñar, planificar, fabricar, verificar y reparar, entregar, mantener y evolucionar.

**R79: respaldo público del código y documentación seleccionados.** No se ha promovido ningún candidato como versión activa.

## Contenido

- `development/autofab/` y `development/tests/`: fuentes y pruebas del entorno de desarrollo.
- `portable/autofab/` y `portable/tests/`: fuentes y pruebas de la copia portable, **sin runtimes**.
- `reference/R76/`: aplicación de referencia y proyecto Android en código fuente.
- `continuity/`: documentación pública de hitos y estado verificable.
- `handoff/R77/`: arquitectura integral y relevo para otra IA.
- `PUBLIC-SNAPSHOT-SHA256.json`: manifiesto de los archivos publicados.

## Recuperación y limitaciones

Este repositorio **no es una copia integral del ordenador**. Se excluyen deliberadamente los modelos GGUF, SDK y herramientas binarias, distribuciones grandes, bases de datos, registros operativos, claves, datos privados y pruebas reservadas. La instalación de dependencias compatibles y la verificación de los entornos siguen siendo necesarias.

No ejecutar automáticamente con Windows ni ejecutar código generado por modelos con privilegios de anfitrión. Mantener la compilación, las pruebas adversariales y las instalaciones dentro de los límites y entornos autorizados.

## Colaboración y licencia

Repositorio público para que pueda estudiarse el trabajo. **Aún no se ha elegido licencia**; la visibilidad pública no concede por sí sola derechos generales de redistribución o uso comercial. Será necesario decidir una licencia antes de distribuirlo como software libre.

Si se descubre información sensible, avisar al propietario por un canal privado; no publicarla en un issue.

**Importante:** un `PASS` de un componente o una demostración no equivale a la aceptación de cualquier aplicación nueva por una IA autónoma.
