# R86 — Contrato de dirección artística y experiencia de usuario: aventuras VGA clásicas

**Decisión P0 de producto:** el aspecto visual percibido, la expresividad de los personajes y la sensación al interactuar preceden a la ampliación de contenido y a la aceptación funcional de una aventura. Una escena que ejecuta todos sus tests lógicos pero no consigue el lenguaje visual exigido queda en estado VISUAL_REVIEW_REQUIRED, nunca ACCEPTED_GAME.

**Referencias artísticas (estudio, no recursos reutilizables):**
- Monkey Island 2: LeChuck's Revenge (1991), versión clásica VGA original.
- Indiana Jones and the Fate of Atlantis (1992), versión clásica VGA original.
- La referencia es la técnica, las proporciones y la sensación de juego, NO copiar sus personajes, retratos, fondos, diálogos, sprites, logotipos ni música. El reparto y la historia son originales; incluir el personaje original del anciano de barba blanca solicitado por el usuario.

## 1. Pantalla objetivo
- Modo canónico de referencia: lienzo lógico **320 x 200**, arte orientado al color VGA, proyectado con corrección de aspecto histórica a una presentación **4:3**; no confundir 320x200 con una presentación 16:10. Permitir 4:3 con bandas laterales en monitores modernos; 16:9 solo como rediseño explícito con nueva aprobación artística, sin recortes.
- Sin suavizado bilineal en sprites pixelados; rasterización nearest-neighbor con coordenadas cuantizadas. Los efectos que no son pixel art deben tratarse de manera independiente.
- Reservar una banda inferior para verbos, línea de acción e inventario, proporcional y con tipografía pixelada legible; áreas de clic mayores que el texto aparente.
- El juego nunca se declara visualmente aprobado basándose únicamente en el número de polígonos, resoluciones, sprites o capturas.

## 2. Personajes: estándar de fabricación
- Personajes originales dibujados pixel a pixel con diseño estilizado y humano, proporciones coherentes, piernas/manos/rostros legibles y una silueta distinta para cada personaje.
- El alto del sprite depende de la escala de escena y perspectiva. Como orientación de revisión, un adulto común a profundidad central puede rondar **35–55 px** dentro de la escena clásica, pero NO usar esa cifra como fórmula universal. El criterio real es conservar gestos, proporciones y lectura en pantalla.
- Contrato por personaje: hoja de modelo canónica (frente, 3/4, perfil, espalda), paleta fija, proporciones de cabeza/torso/extremidades, puntos pivote, escala por plano, zonas de iluminación, id de atuendos y accesorios, hoja de expresiones y animaciones.
- Expresiones mínimas: neutral, alegría, enfado, sorpresa, duda, miedo y conversación. No intercambiar ojos o boca con simples stickers flotantes ajenos a la estética.
- Animaciones base: idle con respiración/parpadeo, caminar lateral y diagonal/frontal o trasera según cámara, girar, hablar, examinar, coger, utilizar, entregar, reaccionar, aparecer/desaparecer. Una acción debe conectar con una postura creíble, sin teletransporte ni deslizarse.
- Los NPC mantienen escala, sombra de contacto, orden de profundidad y dirección de mirada con respecto al ambiente.
- El anciano de barba blanca tiene ID propio y diseños originales, no es clon de personaje ajeno: barba legible a tamaño nativo, posturas, habla y expresión coherentes entre escenas.
- Guardar cada personaje en recursos EDITABLES por separado (archivo maestro con capas, spritesheets derivados, máscaras, pivotes y versionado); no incrustarlo en el bitmap del escenario.

## 3. Escenarios
- Fondos originales con composición teatral, perspectiva deliberada, siluetas claras, paletas limitadas y contrastes cálidos/fríos o claros/oscuros dirigidos. Sombreado con píxeles pintados, dithering intencionado y detalles narrativos útiles; evitar collage de imágenes con filtrado fotográfico, perspectiva inconsistente o objetos dibujados como iconos UI.
- Capas editables: fondo, decoración posterior, caminables, objetos interactivos, personajes, primer plano/oclusores, luz/FX, interfaz. En cada hotspot documentar máscara, punto de aproximación, acción y feedback.
- La escala y el orden Y de cada personaje se determinan mediante reglas propias de la escena; no por el orden en que se cargaron archivos.
- No regenerar escenas completas para modificar un objeto individual. Conservar originales por capas y manifiestos de procedencia.

## 4. Experiencia de jugador
- Una escena y la interfaz deben resultar comprensibles sin leer manual técnico. El cursor indica el objetivo; la acción verbal actual se comunica sin ambigüedad.
- Al hacer clic: feedback inmediato del cursor, acercamiento natural cuando es necesario, orientación del personaje, animación contextual y después consecuencia coherente. Nunca mover al personaje de forma instantánea salvo transición narrativa señalada.
- No se permite doble activación por clic repetido, acciones que queden pendientes indefinidamente, cambios de escena que rompan el estado o inventarios que pierdan el objeto seleccionado.
- El jugador puede inspeccionar, recoger, hablar, usar/combinaciones y desplazarse según disponibilidad real; fallar en una combinación da una respuesta escrita con personalidad y no una pantalla vacía.
- Tipografía de píxel legible con contraste, escalado correcto, subtítulos y controles accesibles. Las respuestas deben caber en la pantalla; permitir adaptar velocidad y saltar líneas.
- Transiciones, música y sonidos ligados al estado del juego, nunca una interfaz que parezca software administrativo.

## 5. Prueba de aprobación P0: una sola escena completamente acabada
ANTES de programar 20 escenas o una novela completa, producir un VERTICAL SLICE con:
- Escenario pintado original con al menos tres planos de profundidad y tres hotspots.
- Protagonista original con animaciones de caminar, estar quieto, mirar, hablar, recoger y reacción.
- Anciano original de barba blanca con su modelo fijo, retrato/expresión y conversación.
- Interfaz de verbos e inventario integrada con la resolución histórica.
- Un objeto recogible, una combinación válida y una incorrecta; una transición de escena; guardar y cargar.
- Capturas de estado inicial, medio y final, y fotogramas de animaciones; registradas con hashes y versión de código/assets.

**Gates automáticos:** assets no faltantes, manifests SHA, sprites y máscaras alineados, hotspot alcanzable, navegación sin teleport, z-order y sombras, inventario coherente, UI completa, snapshots de regresión en entorno fijo, ejecución real de una ruta E2E.

**Gate de calidad humana:** a tamaño final se debe percibir como una aventura VGA original de principios de los noventa y los personajes deben resultar expresivos e integrados. Sin esa aprobación, el resultado es CANDIDATE_VISUAL_NOT_ACCEPTED aunque todos los tests automatizados pasen. No simular evaluación estética con un recuento de capturas.

## 6. Contrato AUTOFABRICADOR
- Director y agentes INTERNOS crean recursos por unidades versionadas, prueban sin sobrescribir source editable, fijan IDs y SHA, y entregan archivos maestro y exportaciones.
- IA generativa puede crear bocetos y sprites; control de paleta, revisión de coherencia y retoque pixel art final son etapas explícitas. No presentar un collage sintético como un fondo o sprite listo.
- Probar renderizador web primero por el material de AUTOFABRICADOR ya disponible; datos del juego independientes del motor; un adaptador Godot futuro no implica duplicar toda la aventura.
- No reactivar supervisores STOP, instalar servicios, tocar MMC7 ni marcar producto ACTIVE por este documento. No modificar un juego que se esté construyendo en otra conversación sin reconciliar su journal/lease.
- NEXT_ACTION: obtener del trabajo de juego actual sus capturas y assets; compararlos con este contrato. Si fallan, corregir la cadena de arte/animación/UX antes de ampliar el guion.
