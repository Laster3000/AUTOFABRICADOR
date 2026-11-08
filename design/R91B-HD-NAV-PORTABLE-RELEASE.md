# R91B — Aventura panorámica HD, navegación segura y fuente recuperable

**Objetivo principal:** mejorar el prototipo original *La Luz de Bruma* para alimentar las capacidades reutilizables del **AUTOFABRICADOR**. **MMC7 sigue suspendido**. Fecha: 8 de noviembre de 2026. No se ha tocado el juego FUJU de otra conversación.

## Resultado original probado (candidato, no ACTIVE)

- Formato 16:9, lienzo nativo **640×360**, salida habitual **1280×720**; lógica interactiva conservada en coordenadas 320×180 para no reprogramar los hotspots.
- Tres salas originales (puerto, taller, observatorio), diálogos, inventario, puzle completo, guardado/carga y final. Anciano original de barba blanca obligatorio y presente.
- **Walkboxes y obstáculos por sala** en `navigation_r91.json`, AStarGrid2D de 2 px en `adventure_nav_r91.gd`, proyección de clics exteriores, detección de llegada, pies/silueta dentro del encuadre, proyección de guardados antiguos a suelo seguro, colisión con el anciano, escala por profundidad y ordenación visual por posición de los pies.
- Interfaz: F1 ayuda, teclas 1–5 para verbos, ratón, F5 guardar, F9 cargar, ESC cerrar diálogo y R reiniciar tras el final. Los recibos de test usan rutas de guardado independientes de las partidas del usuario.
- **11 recursos gráficos originales PNG con 11 maestros OpenRaster** de 6 o más capas semánticas cada uno. Dos reconstrucciones limpias reproducen los 22 archivos con SHA-256 idéntico.
- Esas reconstrucciones usan las fuentes originales R90C como punto de partida (cada fuente preservada) y añaden resolución física, microdetalles de iluminación y un muelle continuo en el puerto. No es una ilustración conceptual ni una producción humana aprobada.
- Generación de narración por CUDA7B: solo contribución textual original del observatorio de R89B, **no** creación autónoma de todo el código o arte de R91B.

## Pruebas originales y reproducibilidad

| Prueba | Evidencia |
| --- | --- |
| 35 comprobaciones originales del juego | PASS real Godot 4.6.3 |
| 207 verificaciones adicionales de walkboxes/rutas | PASS real Godot; 1.709 pasos de movimiento comprobados |
| 24 tests del módulo reutilizable | PASS unitario |
| 136 regresiones previas del AUTOFABRICADOR | PASS (director, enrutador, referencia, validadores R87/R88) |
| Doble reconstrucción PNG/ORA | PASS, 22 SHA idénticos |
| Zip restaurado en carpeta limpia | PASS 35 + 207 + reproducción de 22 archivos dos veces + arranque Godot |
| Recuperación de fuentes desde GitHub público | PASS 22 fuentes textuales, reconstrucción R90C→R91B de 22 archivos, nuevo Godot 35 + 207 |
| Cuatro capturas de vista real OpenGL RTX 3060 | PASS 1280×720 cada escena, mosaico 2560×1440 |
| Ejecución de GitHub Actions remoto | NO VERIFICADA (workflow manual disponible) |
| Aceptación artística humana y otro PC físico | PENDIENTE |
| AUTOFABRICADOR capaz de generar apps generales completas sin intervención humana | NO DEMOSTRADO |

## Producto portable probado

Archivo: `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R91B-AVENTURA-HD-NAV-16x9-PORTABLE-CANDIDATE.zip`

SHA-256: `14b7ea48325cb41ff713cba27bc83ece5ae6fcd544b3327497cb8c1a2468e331`. 80.567.803 bytes, 76 archivos. Incluye Godot 4.6.3 original anclado al release oficial SHA-256 `e39986a178d585ce7ac198fb8de6ea436366dc0cc00e594810c2e3e104c04b90`, licencias y lanzadores `JUGAR-R91.cmd`, `ABRIR-EDITOR-R91.cmd`, `PROBAR-R91.cmd`. Ninguna fuente tipográfica externa ni archivos protegidos de videojuegos comerciales. Sin instalador, autoinicio, servicio ni cambio de PATH persistente.

El ZIP se preservó con SHA idéntico en `D:\AUTOFABRICADOR-RESCATE\R91-AVENTURA-HD-NAV-20261108`. La versión R90C sigue intacta como anterior LKG.

La carpeta lista para jugar está en `C:\AUTOFABRICADOR\JUGAR\LA-LUZ-DE-BRUMA-R91B` y el acceso directo en el Escritorio se llama **JUGAR - La Luz de Bruma R91B**. Godot ya se ha iniciado en sesión Windows 1.

## Capacidad reutilizable del AUTOFABRICADOR

`autofab/adventure_navigation_r91.py` y `adventure_nav_r91.gd` son reutilizables, no hardcoded a una única habitación. El nuevo CLI registra **`python autofabricador.py adventure-nav-audit RUTA_PROYECTO`**. Sus controles independientes verifican rutas, hotspots accesibles, dimensiones, archivos PNG/ORA y hashes. La API `build_contract` permite crear otro archivo de navegación desde nuevas escenas y una declaración de obstáculos.

Fuentes públicas: [aventura R91B](../examples/adventure-godot-r91b/LEEME-PRIMERO.md), [módulo genérico](../development/autofab/adventure_navigation_r91.py), [suite unitarios](../development/tests/test_adventure_navigation_r91.py), [workflow manual de GitHub](../.github/workflows/r91b-godot-hd-nav.yml).

## Estados M1-M6

- M1 Construcción: **PASS acotado**, nuevo R91B con sprites/pixel art y walkbox original.
- M2 Integración: **PASS acotado**, Godot jugable y validador integrado en el AUTOFABRICADOR.
- M3 Pruebas: **PASS acotado**, 35 + 207 + 24 + 136 + arte/ZIP/repositorio restaurados.
- M4 Autorización protegida: **NOT_APPLICABLE**, no se ejecutó ninguna instalación protegida.
- M5 Instalación/paquete: **PASS acotado** por ZIP portable lanzado manualmente, no promoción de fábrica.
- M6 Verificación final de producto general: **BLOCKED** por estilo visual humano, aceptación en segundo ordenador y autonomía real del modelo construyendo nuevas apps completas.

**NEXT_ACTION:** evaluar visualmente R91B con el usuario, mejorar aún más las proporciones de personajes/animaciones y el acabado profesional del entorno; hacer la prueba física en segundo equipo, exportación bidireccional Pixelorama/ORA, salas Popochiu si son requeridas; demostrar una app NUEVA completamente fabricada por IA local con generación de arte, código, pruebas, corrección e instalación portable sin edición humana. No declarar ACTIVE hasta obtener originales E2E para todo ese alcance.
