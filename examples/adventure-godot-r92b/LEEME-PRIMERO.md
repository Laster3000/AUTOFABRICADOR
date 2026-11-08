# LA LUZ DE BRUMA R92B — AVENTURA PANORÁMICA PULIDA 16:9

**Estado:** candidato jugable, NO ACTIVE. No modifica R91B ni MMC7.

## Jugar
Descomprimir ZIP y ejecutar JUGAR-R92.cmd desde su raíz. El primer inicio importa PNG en Godot 4.6.3.
La ventana 1280×720 usa escalado **entero 2×** sobre un juego original 640×360, preserva el píxel nítido. F11: pantalla completa (escalado entero), ESC: cancelar, F1: ayuda, M: mapa grande, F5: guardar y F9: cargar. Teclas 1–5 eligen IR, MIRAR, COGER, USAR y HABLAR. Ratón para caminar, examinar y combinar inventario; al terminar se libera el verbo/objeto seleccionado.

## Mejoras sobre R91B
- Dos personajes originales redibujados al completo, 14 fotogramas por personaje y 48×96 píxeles por frame.
- 11 sprites PNG / 11 fuentes OpenRaster editables con 69 capas semánticas en total.
- Eliminados los trazos aleatorios R91 superpuestos a la escena; el dibujo arquitectónico real se conserva.
- Fondos de 640×290 + HUD compacto 640×70: más escena visible y menú sin deformaciones.
- Escalado entero y filtro NEAREST para evitar pixelado desigual.
- Sistema de acciones de un solo uso con limpieza de ruta/selección/verbo, hotspots consumidos ocultos, interacciones repetidas idempotentes y estado seguro al cargar/reiniciar.
- Walkboxes A* y límites recuperados de R91B. Las partidas personales usan user://bruma_r92.json y están separadas de las rutas QA.

## Pruebas independientes
- 35 casos E2E originales de Godot, 207 casos de navegación con 1.709 pasos simulados, 49 pruebas originales de acciones y UI, 22 recursos artísticos reproducidos dos veces por SHA.
- Auditoría reutilizable: python autofabricador.py adventure-quality-audit RUTA_PROYECTO.
- Archivo ci_verify_art.py en el juego para reconstrucción independiente del arte; requiere Python + Pillow 12 solo para los generadores. El juego NO requiere Python.

## Evidencia visual
VISTA-PREVIA-R92B-GODOT.png recoge cuatro capturas REALES de Godot OpenGL 3.3, no dibujos promocionales. VISTA-MAPA-R92B-GODOT.png muestra el mapa real.

## Límites
No equivale a videojuego de calidad comercial aprobada; el arte sigue siendo pixel art original procedimental. No está demostrado que la IA local cree autónomamente aplicaciones completas generales. No se ha probado en otro ordenador ni certificado un workflow GitHub Actions remoto. No se incluye Popochiu como dependencia ni fuentes tipográficas de terceros.
