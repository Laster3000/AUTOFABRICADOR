# AUTOFABRICADOR — Relevo técnico R93 VISUAL FACTORY (sin transcripción privada)
**Fecha:** 2026-11-09. **Operación documental:** `AF.R93.DOCUMENTARY-HANDOFF-20261109`. **Estado R93:** PROPUESTO / INVESTIGADO / NO PROBADO / NO ACTIVE.
**Estado previo:** R92B es CANDIDATE_NOT_ACTIVE, no aprobado artísticamente. **Prioridad:** AUTOFABRICADOR; MMC7 suspendido y conservado como histórico.
**Nota de privacidad:** el documento completo y la transcripción literal accesible se entregan únicamente al usuario como archivo privado de la conversación; **no se publican mensajes de chat** en este repositorio público. Esta página es un índice técnico seguro, NO un transcript FULL.

## Objetivo y por qué
El videojuego original `La Luz de Bruma` prueba mecánica, navegación y empaquetado, pero sus gráficos programáticos no alcanzan la calidad atmosférica, expresividad de personajes y coherencia visual deseadas. La primera referencia del usuario fue https://www.reddit.com/r/aigamedev/comments/1x6xh4v/finally_found_a_way_to_get_my_dream_art_style/ . Otras: https://www.reddit.com/r/Makkoai/comments/1txr10a/ y https://www.reddit.com/r/PixelArt/comments/1ehr5ue/ .

**Decisión:** fábrica de arte dual, prioritaria `ILLUSTRATED_25D` (biblia de estilo original, concepto por IA local, blockout Blender, edición guiada, proyección a textura, bake, personajes con rig/expresiones y juego Godot 16:9), con alternativa `AUTHENTIC_PIXEL_2D` (Pixelorama, paletas y dithering, rejilla de píxeles real). El resultado debe ser independiente de IA/Blender/ComfyUI en runtime; todo editable y 16:9. No copiar personajes/activos de franquicias existentes. Personajes originales, incluido el anciano de barba blanca.

**Investigación técnica completa ya publicada:** [R93-VISUAL-FACTORY-RESEARCH-20261109.md](R93-VISUAL-FACTORY-RESEARCH-20261109.md), commit `52bfda0d716700be8363445ef8c256c8e703e6ae`, blob Git `61f1e95187ceb85b94d7eed8081472cc6e634d1f`. Leer ese documento para la matriz de herramientas/licencias, contratos, agentes, pipeline y riesgos.

## Fuentes y estado verificable (lectura Windows 2026-11-09)
| Versión | SHA-256 del ZIP portable | Estado |
|---|---|---|
| R90C | `0518ecc18b8c670e124d3366aecf751dbc3786dfe2b7b1a17bb2b2cfc2318529` | anterior candidato conservado |
| R91B | `14b7ea48325cb41ff713cba27bc83ece5ae6fcd544b3327497cb8c1a2468e331` | 35 Godot +207 navegación, arte 22x2 |
| R92B | `a64eef2d9947fdcf60ada43fed92fbff756d55b6d0d5f7f2f33eade39343f36b` | 35 Godot +207 navegación +49 FSM, 136 regresiones +24 unitarias, 22 artes x2 |
| R93 | Ningún ZIP ni ejecutable | PROPUESTO, sin pruebas propias |

Ruta R92B: `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R92B-ARTE-ACCIONES-16x9-PORTABLE-CANDIDATE.zip` (80.590.949 bytes, 68 miembros).
Checkpoint proyecto: `C:\AUTOFABRICADOR\CONTINUIDAD\R92-QUALITY-STATE-ART-20261108\CHECKPOINT-PROYECTO.json` SHA `7902c885d653cbc776bdb82b0a3e0df661f91e7d112dbefe3652e7a84a3fd343`.
Manifest y espejo de D SHA `c78038cb0a8b39677a72d1bd89134715c1e86db383e736805da826f2ddf609f3`.
Recibos: `D:\AUTOFABRICADOR-RESCATE\R92-AVENTURA-PULIDO-20261108\R92B-PORTABLE-RESTORED-OWNER.json` y `R92-GITHUB-PUBLIC-RESTORE-OWNER.json`; fuente pública R92 [aquí](../examples/adventure-godot-r92b/LEEME-PRIMERO.md). En recuperación se reprodujeron R90→R91→R92 con 26 fuentes públicas, 22 archivos artísticos idénticos y 291 casos Godot.
La suma 35+207+49+136+24 = **451 comprobaciones acotadas**; NO 451 aplicaciones ni una aceptación general.

Supervisor: `C:\AUTOFABRICADOR\supervisor\control.json` y `C:\AF-PORTABLE\supervisor\control.json`: ambos STOP en última lectura. No deducir estado vivo sin consultar journal/lease/recibos originales.

Hardware medido: RTX3060 12.288 MiB VRAM, CPU i7-12700K, RAM 16.908.410.880 bytes, C: 234,3 GiB libres, D: 336,8 GiB libres. No usar F:. Blender/Krita/ComfyUI no detectados en rutas habituales consultadas; no se puede afirmar ausencia total. Ollama no estuvo en PATH de ese proceso; el modelo anterior reportó NOT_STARTED. Instalar/verificar mediante G0 y permisos realmente disponibles, no suponer capacidad probada.

## Software que debe evaluarse, no declarar instalado
- `Comfy-Org/ComfyUI`, `black-forest-labs/flux2` (klein 4B candidato Apache2, comprobar licencias **de pesos** y benchmark VRAM real; 9B tiene restricciones distintas).
- `blender/blender`, `smewedsmew/camera-projection-paint` (POC de proyección), `ahujasid/blender-mcp` (sandbox, límites de ejecución), `Acly/krita-ai-diffusion`.
- `facebookresearch/sam2`, `DepthAnything/Depth-Anything-V2` (licencias Small vs pesos más grandes).
- `Orama-Interactive/Pixelorama`, `carenalgas/popochiu` (integración E2E no acreditada), `nathanhoad/godot_dialogue_manager` como alternativa.
- `brunocpf/spritekiln` como POC parcial; no instalar 73 GB sin comprobar RTX. `TheOrcDev/skills` es solo una referencia de proceso con licencia no declarada.

## Macrotrabajo habilitable bajo una orden, no microconfirmaciones
1. **G0:** control de instalación, GPU/VRAM, versiones, licencias/sha, sandbox y restauración de R92.
2. **B1:** biblia de estilo, 3 conceptos 16:9 y referencia maestra original con consentimiento visual real.
3. **B2:** IA local de imágenes (GPU secuencial, descarga LLM de código al cargar modelo visual), Blender/UV/proyección/bake, máscaras, modelos y capas.
4. **B3:** Godot 16:9, 3 escenarios, personaje + anciano de barba blanca, mapa amplio, diálogo, puzles, FSM, guardado/carga y final.
5. **B4:** QA independiente (incluye navegación, arte, cámara, identidad facial, sombras, hotspots, escenas, pruebas adversas), reparaciones en un único ciclo supervisor.
6. **B5:** ZIP portable, SHA/manifiesto, fuente editable, restauración en carpeta limpia, E2E.
7. **B6:** generar con IA local **OTRO JUEGO NUEVO** sin edición manual de arte/código; segundo PC físico, aceptación visual humana y pruebas originales de la fábrica general.

Agentes funcionales: Director/orquestador, Director artístico, Artista de escena/Blender, Animador/Personajes, Narrativa y puzles, Programador Godot, QA independiente, Reparador/Packager. **No ocho modelos de GPU residentes:** reutilizar un LLM local con roles y un motor de imágenes por turnos; verificadores CPU deterministas.

## M1-M6 / NO PROMOVER
R93: M1 construcción **PENDING**, M2 integración **PENDING**, M3 pruebas **PENDING**, M4 autorización protegida **NOT_APPLICABLE** salvo cambios protegidos, M5 instalación **PENDING**, M6 verificación general **BLOCKED**. No hay modelo visual R93 instalado ni juego R93 ejecutable. Faltan aprobación artística humana, segundo ordenador y demostración de fábrica IA general. R92 conserva PASS solo en su alcance previo.
No usar FULL transcript sin exportación nativa, ni inventar porcentaje/ETA de saturación interna.

## NEXT_ACTION
**Ejecutar G0 de R93 y producir una única escena panorámica 2,5D verdaderamente generada/editada/proyectada por IA local; medir VRAM, consistencia visual y proyección en capturas reales de Godot.** Si pasa, continuar B1–B6 como operación con checkpoints SHA/CAS, rollback ensayado y recibos originales. Conservar R92B como LKG. No reejecutar SUCCEEDED ni repetir efectos UNKNOWN sin journal/lease/readback. No tocar MMC7 ni otros proyectos independientes.

**Handoff íntegro con literal:** distribuido en un paquete de la conversación del usuario, deliberadamente **no** en este repositorio público.