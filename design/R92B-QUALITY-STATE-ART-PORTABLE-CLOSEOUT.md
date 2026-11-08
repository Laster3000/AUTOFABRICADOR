# AUTOFABRICADOR R92B — Cierre técnico, evidencia, decisiones y límites

**Fecha:** 8 de noviembre de 2026. **Objetivo:** AUTOFABRICADOR. MMC7 continúa suspendido. Producto de prueba: videojuego original *La Luz de Bruma*, **CANDIDATE / NOT ACTIVE**. Se preservan R90C y R91B por SHA; no se modifican los juegos de otras conversaciones.

## Problemas observados y correcciones

1. **Líneas espurias:** las capas originales `R91 fine-pixel surface details` y `R91 highlights and material definition` generaban rayas y contornos geométricos muy largos. Se descartaron de la composición R92 y se sustituyeron por detalles localizados en nuevas capas semánticas. Las líneas arquitectónicas intencionales del escenario permanecen.
2. **Acciones pegadas:** máquina de estados autocontenida, `_clear_pending_action` y `_finish_action`. Tras completar una interacción se limpian verbo, objeto seleccionado, destino, ruta, cola y hover. Diálogos, cambios de sala, cargar y reiniciar tienen transiciones definidas. No se puede recoger dos veces un objeto consumido ni repetir una reparación como si no estuviera hecha.
3. **Imagen/área jugable pequeña:** fondos propios de 640×290 y HUD de 640×70, frente a 640×260 y 640×100. El área de escenario pasa de 130/180 a 145/180 unidades lógicas, sin cambiar el aspecto 16:9. M muestra un mapa ampliado; F11 alterna pantalla completa.
4. **Personajes sin definición:** sprites originales redibujados a resolución real 48×96 por fotograma, 14 fotogramas por personaje. Rostro, expresiones, ropa, manos, ojos, barba y reflejos separados por capas editables. Los personajes se presentan a mayor tamaño, con los pies anclados y A* R91B conservado.
5. **Píxeles de grosor desigual:** ventana normal de 1280×720 sobre lienzo 640×360, relación **2× entera**; Godot `window/stretch/scale_mode=integer` y filtrado NEAREST. Se descartó la escala fraccionaria de 1600×900.

## Evidencia realmente ejecutada

| Familia | Resultado | Método |
|---|---:|---|
| Juego original (tres escenas y final) | **35/35 PASS** | Godot 4.6.3 |
| Navegación, límites, hotspots y 1.709 pasos | **207/207 PASS** | Godot, owner original |
| Estados e interacciones repetidas | **49/49 PASS** | Godot, owner nuevo |
| Regresiones anteriores de AUTOFABRICADOR | **136/136 PASS** | 34 director + 22 router + 10 referencia + 35 visual R88 + 35 visual R87 |
| Pruebas unitarias del módulo A* reutilizable | **24/24 PASS** | unittest |
| Arte reproducible | **22 SHA correctos, 2 reconstrucciones PASS** | Python/Pillow independiente |
| ZIP restaurado en carpeta limpia | **35 + 207 + 49 + arte 22×2 PASS** | Lanzador de test del ZIP |
| GitHub público descargado en otra carpeta | **26 archivos, 3 generaciones de arte, 22 SHA, 291 comprobaciones PASS** | GitHub raw + Godot local |
| Capturas reales (OpenGL RTX 3060) | **5 PASS** | Puerto, taller, observatorio, diálogo, mapa |
| GitHub Actions remoto | **NO VERIFICADO** | Workflow manual configurado, sin recibo de ejecución |
| Aprobación visual humana | **PENDIENTE** | El usuario debe valorar R92B real |
| Compatibilidad física independiente | **PENDIENTE** | No ejecutado en otro ordenador |
| Fabricación totalmente autónoma de apps generales por IA | **NO DEMOSTRADA** | El videojuego sigue siendo un escaparate construido e integrado con ayuda |

En conjunto: **451 comprobaciones diferentes locales** (291 Godot + 136 regresiones + 24 unitarias) y **291 casos originales adicionales repetidos** desde las fuentes descargadas de GitHub. Ninguna de esas cifras certifica por sí sola la calidad estética.

## Paquete y lectura posterior

- ZIP: `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R92B-ARTE-ACCIONES-16x9-PORTABLE-CANDIDATE.zip`
- SHA-256: `a64eef2d9947fdcf60ada43fed92fbff756d55b6d0d5f7f2f33eade39343f36b`
- Tamaño: **80.590.949 bytes** y **68 archivos**.
- Una copia byte idéntica está en `D:\AUTOFABRICADOR-RESCATE\R92-AVENTURA-PULIDO-20261108`.
- Juego extraído y ejecutado en `C:\AUTOFABRICADOR\JUGAR\LA-LUZ-DE-BRUMA-R92B`; acceso del Escritorio: **JUGAR - La Luz de Bruma R92B**.
- `JUGAR-R92.cmd` importa texturas en el primer arranque y abre Godot sin instalar componentes. `PROBAR-R92.cmd` comprueba las tres suites desde una carpeta de restauración.
- Capturas REALES incluidas: `VISTA-PREVIA-R92B-GODOT.png` y `VISTA-MAPA-R92B-GODOT.png`. No son imágenes conceptuales.

## Cambios integrados en AUTOFABRICADOR

`autofab/adventure_quality_r92.py` añade un oráculo reutilizable (solo lectura) con verificación de las zonas, 13 hotspots alcanzables, resoluciones, escenas, capas OpenRaster y 22 hashes. Comando:

`python autofabricador.py adventure-quality-audit RUTA_DEL_PROYECTO`

La fuente pública ejecutable está en [examples/adventure-godot-r92b](../examples/adventure-godot-r92b/LEEME-PRIMERO.md). El módulo reusable está en [development/autofab/adventure_quality_r92.py](../development/autofab/adventure_quality_r92.py). El workflow de compilación y auditoría está en [.github/workflows/r92b-godot-quality-169.yml](../.github/workflows/r92b-godot-quality-169.yml). **No prometer que Actions lo ha ejecutado hasta obtener un recibo original.**

## M1–M6

| Hito | Estado |
| --- | --- |
| M1 construcción | PASS acotado: original R92B |
| M2 integración | PASS acotado: runtime Godot y capability `adventure-quality-audit` |
| M3 pruebas | PASS acotado: 451 + restauración pública 291 |
| M4 autorización protegida | NOT_APPLICABLE: no hubo instalación protegida |
| M5 instalación | PASS acotado: ZIP portable y lanzamiento manual, sin servicios |
| M6 aceptación integral | BLOCKED: arte humano, hardware independiente, IA autónoma completa |

**NEXT_ACTION:** el usuario prueba R92B y comunica las anomalías concretas restantes. Mejorar el dibujo artesanal y la animación sin introducir nuevas líneas; ejecutar la prueba en otro PC; demostrar que la IA local produce un videojuego o aplicación compleja realmente nueva y completa, con recursos, código, pruebas y correcciones autónomas; validar Pixelorama/Popochiu solo si son requeridos.
