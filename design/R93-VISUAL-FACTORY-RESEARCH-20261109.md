# R93 PROPUESTO — AUTOFABRICADOR VISUAL FACTORY: aventura pintada 2,5D con IA local

**Fecha de la investigación:** 2026-11-09. **Estado:** PROPUESTO / INVESTIGADO, **NO CONSTRUIDO, NO PROBADO, NO ACTIVE**. Este documento es un plano de implementación, no un recibo de ejecución. AUTOFABRICADOR sigue siendo el producto principal; MMC7 queda suspendido. **No modificar R90C/R91B/R92B**, ni BOOT/PROD/CURRENT/ROOT, ni otros juegos de otras conversaciones.

## 0. Motivo y decisión artística

R92B es funcional, pero las imágenes se hacen principalmente con dibujo determinista de formas y píxeles. Una prueba de 451 verificaciones puede garantizar que el juego no se atasca y que sus ficheros son reproducibles; NO certifica que sus personajes o fondos estén a la altura de una aventura ilustrada. El usuario prioriza la primera referencia de Reddit, una demostración de dirección artística trasladada a un mundo jugable, y quiere calidad gráfica antes que más parches de mecánica.

**Diseño elegido:** un **motor visual dual**, con **modo por defecto ILLUSTRATED_25D**: concepto de alta calidad → blockout geométrico original → pintura e imagen editadas por IA local con referencias consistentes → proyección/bake sobre geometría de Blender → materiales, iluminación y cámara limitada → Godot para interacción, navegación y escenas. **Modo opcional AUTHENTIC_PIXEL_2D**: pixel art planificado manualmente a una rejilla real, capas editables, dithering y color cycling, usando Pixelorama/Godot. NO aplicar filtros de pixelado a una imagen de IA y llamarlo auténtico pixel art. Por defecto **16:9**. Nunca copiar personajes, lugares o archivos protegidos de Monkey Island.

Los enlaces originales de Reddit primero/segundo no devolvieron su cuerpo directamente a web; la tercera publicación sí salió indexada con sus comentarios. Un artículo del 2026-10-16 atribuye el primero a FutureTechPilot, y el vídeo de Future Tech Pilot del 2026-10-21 comenta concepto, blockout, repaint, proyección y limitaciones de cámara. **No declarar como verificado que el autor utilizó una implementación específica que no hemos inspeccionado**. El artículo Makko del 2026-06-04 es escrito por un cofundador: conflicto de interés explícito.

Fuentes: https://www.reddit.com/r/aigamedev/comments/1x6xh4v/ ; https://www.reddit.com/r/Makkoai/comments/1txr10a/ ; https://www.reddit.com/r/PixelArt/comments/1ehr5ue/ ; https://www.aigamedevlabs.com/specimens/concept-art-to-a-playable-3d-game-one-developer-s-ai-era-art-style-pipeline ; https://zolotube.com/watch?v=6EzNO9Fi_uA ; https://blog.makko.ai/i-tested-7-ai-tools-for-2d-game-art-heres-the-honest-ranking-a-founders-perspective/

## 1. Condiciones reales del host (READ-ONLY, 2026-11-09)

RTX 3060 **12.288 MiB** (en la comprobación quedaban 9.686 MiB libres), i7-12700K, RAM física ~**16 GiB**; C: **234,3 GiB libres** y D: **336,8 GiB libres**. **No utilizar F:** (destino lento/retiro previsto). Comprobación de rutas habituales no encontró Blender/Krita/ComfyUI allí; no inferir ausencia universal o instalación completada. Ollama no estaba en PATH de ese shell (esto no demuestra que otro servidor local privado no exista). El local_cuda7b previo reportó NOT_STARTED. Nada de código/modelos ejecutados en este estudio; se necesita G0 de instalabilidad antes de iniciar R93.

Diseño del planificador VRAM: **una sola carga intensiva de GPU a la vez**, entre modelo de código y difusión/descomposición; reservar margen VRAM configurable, dar prioridad a offload/tiling, limitar resolución en prueba e interrumpir si OOM; informar bytes/picos originales sin ETA ficticia. ComfyUI y Blender son herramientas de fabricación, no dependencias del ZIP jugable.

## 2. Repositorios investigados y política de adopción

| Componente | Fuente | Decisión |
| --- | --- | --- |
| Godot 4.x, demos oficiales 2,5D | https://github.com/godotengine/godot-demo-projects | ADOPTAR núcleo runtime. Demo MIT; verificar variante GDScript y Godot 4.6.3 antes de integrar. |
| Blender bpy y scripts locales | https://github.com/blender/blender | ADOPTAR blockout, UV, material, cámara, render y export GLB; preservar .blend editable. |
| Blender MCP | https://github.com/ahujasid/blender-mcp | EVALUAR controlador solo en sandbox, con DISABLE_TELEMETRY=true; jamás Python arbitrario con privilegios del Host. |
| Proyección cámara a textura | https://github.com/smewedsmew/camera-projection-paint | EVALUAR POC MIT, escaso historial (5 commits); alternativa de producción: bpy + UV project/bake propios con tests. |
| Krita AI Diffusion | https://github.com/Acly/krita-ai-diffusion | ADOPTAR para revisión localizada, mascarillas y ControlNet con ComfyUI backend. No confiar en un solo prompt. |
| ComfyUI | https://github.com/Comfy-Org/ComfyUI | ADOPTAR motor reproducible API local; fijar versiones/sha por workflow, licencias y modelos. |
| FLUX.2 klein 4B | https://github.com/black-forest-labs/flux2 | CANDIDATO PRIMARIO: Apache 2.0 4B, edición y multi-referencia, ~8GB VRAM declarados; BENCHMARK OBLIGATORIO en RTX3060 12GB; 9B/dev tienen licencia NO comercial. |
| SDXL + IP-Adapter | https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0 ; https://github.com/tencent-ailab/IP-Adapter | FALLBACK para detalle, poses y consistencia; revisar pesos, licencias y memoria. |
| SAM2 segmentación | https://github.com/facebookresearch/sam2 | ADOPTAR condicionado a E2E; Apache2, útil para separar máscaras / objetos. |
| Depth Anything V2 Small | https://github.com/DepthAnything/Depth-Anything-V2 | EVALUAR para profundidad; pesos small Apache2, otros pesos CC-BY-NC; profundidad no implica geometría correcta. |
| Pixelorama | https://github.com/Orama-Interactive/Pixelorama | ADOPTAR en perfil pixel, CLI export sprite sheet, capas y JSON; fijar versión. |
| Popochiu | https://github.com/carenalgas/popochiu | EVALUAR integración real de Rooms, Hotspots, Character, Inventory, Dialogue en Godot 4.6; evitar declarar Popochiu como runtime si queda solo staging. |
| Dialogue Manager 4 | https://github.com/nathanhoad/godot_dialogue_manager | ALTERNATIVA al diálogo de Popochiu; evitar duplicar sistemas de diálogo activos. |
| LangGraph durable | https://github.com/langchain-ai/langgraph | EVALUAR como coordinador con SQLite checkpointer y CAS propio, solo si reutilizar supervisor existente es insuficiente; no crear otra fábrica paralela. |
| SpriteKiln | https://github.com/brunocpf/spritekiln | SOLO POC: 41 nodos/30 workflows 2D, GPL3, un único commit y ~73GB de modelos; validado por autor en Apple 48GB, NVIDIA no ensayada. No instalar paquete masivo ciegamente. |
| OrcDev skills | https://github.com/TheOrcDev/skills | REFERENCIA DE PROCESO, NO COPIAR: licencia no declarada, algunas etapas usan servicios/voz de pago. |
| Mark Ferrari GDC | https://www.gdcvault.com/play/1023586/8-Bit-8-Bitish-Graphics | REFERENCIA técnica para dithering, color cycling y composición del modo pixel; no copiar sprites de franquicias. |

Reglas: verificar branch/tag, licencia de código *y* pesos, SHA256 y permisos de assets, limitaciones del Windows host y aislamiento. Evitar descargas indiscriminadas, AutoRun, servicios y cambios persistentes en Windows.

## 3. Contratos de arte y runtime

- `style_bible.json`: identidad original, vocabulario de forma, paleta/colorimetría, iluminación diurna/nocturna, densidad de detalle, materialidad, resolución/cámara, referencias licenciadas y negativas; **styleId** estable e inmutable por release.
- `visual_reference.png`: una imagen maestra de dirección artística confirmada; 3 escenas de calibración, no 50 ilustraciones desconectadas. Referencia puede proceder de IA, pero solo usar referencias autorizadas.
- `scene.json`: `sceneId`, `cameraId`, `environment`, `geometryObjects`, `hotspots`, `walkmesh`, `occlusionMasks`, `lights`, `weather`, `entryPoints`, `parallax`, `assetRefs`; 16:9 explícito.
- `asset.json`: `assetId`, `styleId`, `objectId`, `sourceRefs`, `license`, `modelId`, `modelHash`, `workflowHash`, `prompt`, `seed`, `camera`, `mask`, `depth`, `material`, `blendFile`, `glb`, `png`, `sha256`, `parentSha`.
- `character.json`: personaje identificable con nombre original, hoja de expresiones, cuerpo/vestuario, 4 direcciones necesarias, armadura/rig o recorte; nunca generar cada frame desde cero con prompts independientes. El anciano de barba blanca se mantiene como requisito.
- `interaction.json`: máquina finita de estados (IDLE / WALKING / INTERACTING / DIALOGUE / TRANSITION / CANCELLED / DONE), eventos idempotentes, precondiciones y efectos atómicos con owner oracle. Abort/escape y load cancelan movimientos antiguos.
- `scene.blend` + `glb` + `textures`: la geometría y la pintura deben quedar separadas/editables. Recoger 3-5 perspectivas fijas para QA; **no prometer cámara libre** a partir de una sola pintura proyectada.
- `quality.json`: geometrias/colisiones/contornos, screenshots reales 16:9, correspondencia con biblia, artefactos visibles, silueta del personaje, UI tamaño funcional, revisión humana pendiente, resultados QA independientes, fails e intentos.

**Perfil por defecto ILLUSTRATED_25D:** resolución interna sugerida 1280×720 16:9, salida 1920×1080 o 1280×720 según rendimiento, filtros suaves/bicúbicos coherentes de ilustración, NO usar nearest de pixel art; escenario ocupa >=80% del área, barra contextual flotante/compacta. 3D con cámara fijada/ligero paneo limitado, proyección y bake. **Perfil opcional AUTHENTIC_PIXEL_2D:** 640×360 interno, pantalla 1280×720 integer scaling, nearest, paleta explícita y dithering razonado, nunca mezclar arte de distinta escala. El viejo R92B es backup y banco QA, NO la dirección final para el primer estilo.

## 4. Trabajos funcionales de agentes (UN solo modelo LLM compartido, no 9 modelos cargados)

1. **Director/planificador**: recibe petición, define material original y estilo target, descompone grafo y presupuesto de trabajo; reusa AUTOFABRICADOR existente y bitácora.
2. **Art director**: produce biblia, 3 concept arts, paleta/iluminación, estilo coherente y rechazo motivado; mantener misma referencia para TODOS los assets.
3. **World artist/Blender**: genera blockout a escala, máscara de profundidad/oclusiones, UV, cámara, proyección y bake; `bpy` automatizado y permisos mínimos.
4. **Character artist/animator**: genera identidad/turnaround/expresiones, construye rig reproducible, exporta animaciones por transformaciones de rig, revisión del contact point, nunca por re-prompt de cada frame.
5. **Narrative/puzzle designer**: historia original, anciano, inventario, grafo de puzles soluble, estados; diálogos localizados.
6. **Gameplay developer**: escenas Godot, navegación, señales, UI, guardados atomizados, transitions, overlays; un solo owner del estado.
7. **QA independiente**: ejecuta Godot real, recorre hotspots, guarda/carga, fuzz de clics, control de rutas, compara capturas con art bible, verifica licencias SHA y rechaza arte inconsistente.
8. **Repair/release agent**: causa raíz -> delta mínimo -> pruebas originales -> restaurar desde staging -> ZIP portable + manifest SHA + readback + checkpoint; nunca ACTIVE sin aceptación independiente y visual humana.

Operación GPU secuencial: el mismo modelo local toma roles como instrucciones y tools permitidos; para trabajo visual se descarga de memoria el modelo programador antes de cargar FLUX.2 klein 4B. Paralelismo permitido para tareas ligeras CPU y validadores, no para dos modelos grandes. Solo nuevas revisiones cuando hay nuevo delta, nueva prueba o nuevo asset. Errores deterministas reparados; estados UNKNOWN reconciliados contra journal/receipts antes de reejecución.

## 5. Macrotrabajo único R93 — dependencias y aceptación

**G0** verificar instalabilidad, capacidad real de modelos, versiones/licencias/sha; preservar R92B.
**B1 STYLE** construir style bible original y 3 comparativas dentro del motor. El usuario puede aprobar una imagen maestra; la automatización no debe falsificar esa aprobación.
**B2 ART** modelo local con multi-referencia y ControlNet; generar 3 escenarios artísticos y 2 personajes de identidad estable; Blender blockout; cámara-proyección; multi-layer assets y baking SHA.
**B3 GAME** Godot 4.x 2,5D enlazado con engine owner y máscaras navegación; 16:9, mapas legibles, interacción, diálogos, puzzle, inventario y final.
**B4 QA** suites de R92B conservadas, oráculos nuevos para proyección y consistencia, rutas, transparencia, sombras, frames, clipping y playthrough; 2 decoraciones de iluminación, cámara fija y ligera variación, capturas en 5 puntos, tests independientes generador/verificador.
**B5 RESTORE** crear ZIP sin autostart, extraer en carpeta limpia, arrancar Godot, repetir E2E original y reconstruir al menos un escenario/actor desde entradas.
**B6 ACCEPT** obtener valoración de usuario sobre el estilo, luego demostrar otra aventura NUEVA fabricada por la IA local (no simplemente copiando plantilla) y segunda máquina física. Si no hay pruebas, estado CANDIDATE/BLOCKED, no ACTIVE.

Las etapas se ejecutan dentro de **una orden** y se encadenan automáticamente; no equivalen a una sola llamada atómica irrecuperable. Guardar checkpoint durable después de cada gran bloque, con operación/goal/release IDs, SHA, CAS, preimágenes, último LKG y NEXT_ACTION. La IA no debe prometer trabajo en background: el ejecutor local es quien tiene que correr si se desea persistencia real.

## 6. Resultado esperado y límites

**R93-SCOPED:** tres entornos de cuento ilustrado panorámico 16:9, luces y materiales expresivos, personajes claramente reconocibles y animados, anciano blanco presente, mapa suficientemente grande, puzzles originales con final y 100% de acceptance cases originales PASS. Guardados/recuperación portable, todas las capas/texturas y escena .blend editables y un ZIP de juego portable. ComfyUI y Blender solo para la fábrica, no para jugar.

**R93-FACTORY-GENERAL ACCEPTED:** no se deriva de R93-SCOPED. Exige generar **otro juego realmente nuevo** desde otro briefing sin que el asistente escriba sus assets/código a mano, usar la IA local en operaciones E2E reales y que QA externo certifique lo generado. Evaluación artística depende del usuario. No prometer "exactitud" visual automática de la primera demo ni calidad comercial sin valorar ejemplos.

Costes/riesgos: 12 GB VRAM y 16 GB RAM obligan a secuenciar; "proyección de un solo ángulo" fallará con cámara libre; consistencia entre poses requiere rig y estilo bloqueado; licencia de repositorios/modelos distintas, UI/arte no se aprueban mediante unit tests. El riesgo más grande no es el número de agentes: **la coherencia artística y el owner visual independiente**.

**NEXT_ACTION:** ejecutar G0 + evaluación visual de 3 escenas con FLUX.2 klein 4B local en máquina real; decidir entre Blender proyección de vista fija y simple capas 2D según capturas medidas. Solo entonces completar macrotrabajo R93 y prueba de fábrica autónoma, sin tocar R92B o MMC7.
