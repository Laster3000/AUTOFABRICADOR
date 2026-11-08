# AUTOFABRICADOR R87 — Integracion de motores de aventuras, pixel art y calidad visual

Fecha de contraste: 2026-11-08. Estado: INVESTIGACION + PRIMER VALIDADOR INTEGRADO. NO JUEGO FINAL, NO MOTOR GODOT INSTALADO.

## Decision

Objetivo: aventura grafica original de aspecto VGA de los 90 (Monkey Island 2 / Fate of Atlantis como referencias tecnicas), animacion expresiva, escenarios pintados y experiencia point-and-click; **sin copiar recursos, personajes ni marcas protegidas**. La aceptacion artistica humana manda; las pruebas programaticas solo verifican condiciones medibles.

La primera implantacion candidata sera un motor con **Godot 4.6 + Popochiu v2.1.1**, no version sin verificar. Popochiu ya resuelve habitaciones, personajes, hotspots, dialogos e inventario. Pixelorama sirve como herramienta de arte **independiente** (las versiones actuales de sus fuentes requieren Godot 4.7.x, pero eso no impone version del motor del juego). Godot y Popochiu aun no se han instalado ni probado E2E en este Host. Mantener **Phaser 4.2.1 + inkjs** como ruta web secundaria: la compatibilidad del juego en navegador no sustituye la del ejecutable Godot. No crear dos fabricas.

## Catalogo comparado de implementaciones publicas

| Proyecto / repositorio | Licencia documentada | Funcion reutilizable | Decision y verificacion |
| --- | --- | --- | --- |
| https://github.com/carenalgas/popochiu | MIT | Godot: salas, personajes, hotspots, verbos, inventario, dialogos | P1. v2.1.1 publicado para Godot 4.6; la pagina itch anuncia v2.2.1 (2026-10-18), pero requiere leer su migracion y validar binario antes de seleccionar. NO INSTALADO |
| https://github.com/godot-escoria/escoria-core | MIT | Alternativa de aventura con escenas, inventario, dialogs y ASHES | P2 en reserva, no instalar junto con Popochiu sin incompatibilidad probada |
| https://github.com/adventuregamestudio/ags | Artistic License 2.0 | Editor y runtime clasicos especializados | Excelente alternativa Windows, pero el formato AGS es mas especifico; no elegir a la vez que Popochiu |
| https://github.com/godotengine/godot | MIT | Motor de juego, renderer, escenas, audio, exports | Necesario para ruta Popochiu; pin del ejecutable y plantillas pendientes |
| https://github.com/Orama-Interactive/Pixelorama | MIT | Pixel art por capas, frames y CLI export, OpenRaster, .pxo | P1 de pipeline grafico. NO INSTALADO |
| https://github.com/LibreSprite/LibreSprite | GPLv2 | Editor sprites con capas, tags y export batch | Alternativa editor; no redistribuirlo como codigo del juego propietario sin revisar obligaciones |
| https://github.com/aseprite/aseprite | EULA propia | Editor comercial de sprite art, CLI Lua | No redistribuir binarios. Puede utilizarse externamente si el usuario tiene su propia copia; NO INSTALADO |
| https://github.com/MalloyTheDev/aseprite-mcp | Licencia a reconfirmar en commit fijado | Dibujar pixel art, capas, exportar y medir por herramientas IA | CANDIDATE_REVIEW_ONLY; requiere Aseprite autorizado y aislamiento de escrituras |
| https://github.com/oaktreegames/aseprite-live-mcp | MIT | Edicion interactiva y QA de pixels | CANDIDATE_REVIEW_ONLY; no habilitar Lua arbitrario sin sandbox |
| https://github.com/deepnight/ldtk | MIT | Editor JSON de escenarios, tiles y entidades | Complementario; escenas pictoricas de aventuras no dependen exclusivamente de tiles |
| https://github.com/mapeditor/tiled | GPL-2.0-or-later editor; libtiled BSD-2 | Objetos, mapas y capas exportables como JSON | Complementario para hotspots, zonas transitables, propiedad y posicion |
| https://github.com/phaserjs/phaser | MIT | Phaser 4.2.1 (2026-07-09), escenas Canvas/WebGL | P2 web alternativo a Godot, compatible con las pruebas Chrome preexistentes |
| https://github.com/inkle/ink | MIT | Escritura narrativa, guion, ramas, flags y compilacion | P1; mantener contrato narrativo comun para varios motores |
| https://github.com/y-lohse/inkjs | MIT | Runtime JS de Ink para browser, sin dependencia runtime pesada | P2 para modo Phaser |
| https://github.com/nathanhoad/godot_dialogue_manager | MIT | Sistema de dialogos para Godot 4.6+ | Complemento a evaluar: no crear dos sistemas de dialogo en el mismo juego |
| https://github.com/microsoft/playwright | Apache-2.0 | E2E de interfaz, capturas reproducibles y clicks | P1 para pruebas browser, con versions/browser pinned |
| https://github.com/KantaiMishima/godot-vrt | Revisar LICENSE en revision elegida | Captura escenas Godot para regresion | P2; compara snapshots pero no sustituye pruebas de jugador |
| https://github.com/ramonsamagaio/Hermes-Pixelorama-MCP | Licencia/seguridad por verificar | Agente -> Pixelorama para dibujo automatizado | INVESTIGAR: servidor MCP, extension y autenticacion; no instalar automaticamente |

Ningun catalogo implica autorizacion de ejecutar binarios externos, importar recursos de otros juegos o redistribuir proyectos con licencias incompatibles. Version, SHA, licencias de subdependencias y funcionamiento propio deberan quedar congelados en un paquete posterior.

## Implementacion ya integrada en C:\AUTOFABRICADOR

Modulo: autofab/adventure_visual_gate.py
Tests: tests/test_adventure_visual_gate_r87.py
CLI original: autofabricador.py adventure-visual-audit RUTA\scene-visual-contract.json

El comando audita SIN EJECUTAR CODIGO DEL MODELO:
- Formato VGA 320x200, presentacion 4:3, 140 pixeles de escena + 60 de UI, nearest.
- PNG reales, sin chunks corruptos/CRC falsificados ni bombas de descompresion; color y alpha por pixel.
- Imagenes maestras editables OpenRaster con capas reales, ZIP interno y dimensiones verificadas.
- SHA256 de sprites/fondos/UI y masters; bloquea una manipulacion despues de congelar contrato.
- Sprite sheets, canales alpha, grillas y limite de paleta.
- Animaciones por personaje (idle, walk, talk, look, pick, use, react) y pivotes.
- Navegacion basica de hotspots y area transitable; spawn y punto de acercamiento.
- Verbos principales y usabilidad minima del inventario; feedback para cada hotspot.
- JSON estructurado estricto, nombres seguros, rutas sin escape del proyecto.
- Resultado: PASS_TECHNICAL_VISUAL_REVIEW_REQUIRED, que NUNCA significa arte aprobado ni juego completo.

Las pruebas de fixture son dibujos geometricos temporales, NO modelos artisticos. El arte final requiere un artista/director creativo y aprobacion visual a resolucion real.

## Cadena que hay que implementar despues de R87

A1: ficha artistica de cada personaje original, hoja de turnaround, rostro, expresiones, 7+ animaciones, pivotes, paleta y sombras.
A2: escena original pixel-by-pixel creada en Pixelorama, con .ora/.pxo editables y spritesheets versionados. No usar collage de IA sin repintado.
A3: Godot+Popochiu PORTABLE en carpeta encapsulada, sin Windows autostart, importador de recursos y contratos; proyecto minimal con 1 escena P0.
A4: agente interno de arte con herramientas confinadas a un directorio de staging + CAS; no permitir escrituras en otras escenas, masters firmados ni Host.
A5: integracion de Ink/dialogos con mundo, inventario, objetivos, guion y reglas deterministas; anciano de barba blanca original consistente en cada escena.
A6: Playwright/Godot VRT y oraculos originales congelados: visuales, jugabilidad, inventario, guardado, navegacion, pruebas de partida completa.
A7: empaquetado portable, licencia/creditos de cada dependencia, restore point real, lectura posterior y prueba en segundo PC.

## G0 y bloqueo actual

- En el Host en esta intervencion: godot, pixelorama, libresprite, aseprite NO aparecen en PATH; Pillow tampoco esta instalado en el Python externo. No se han ejecutado ni instalado esos binarios.
- R87 conecta con el CLI original y usa solo Python stdlib; no reanuda supervisores en STOP.
- La prueba FUJU de otra conversacion se mantiene intacta. No afirmar su aprobado artistico por existir ZIP/capturas.
- La configuracion 0.9.17 continua CANDIDATE_NOT_ACTIVE; MMC7 queda suspendido.
- NEXT_ACTION: seleccionar y fijar distribuciones portables oficiales de Godot/Popochiu/Pixelorama con licencias y SHA; construir un vertical slice original con assets editables reales y validar la calidad visual humana, no solo codigo.
