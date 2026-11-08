# LA LUZ DE BRUMA — demostración jugable original 16:9 (R88B)

Este paquete es el **vertical slice de ingeniería** creado para AUTOFABRICADOR. No es el videojuego definitivo ni una aceptación de calidad artística equivalente a Monkey Island 2. Está construido con elementos visuales y narrativos originales, sin copiar sprites ni material protegido.

## Resolución y visuales

- Presentación 16:9 nativa: **640×360 píxeles**, a partir de arte fuente de **320×180**, con escalado pixelado 2× (y ampliación proporcional en pantallas mayores).
- La zona de escena ocupa 320×130 píxeles de arte, y la interfaz 320×50.
- Incluye 2 escenas, 2 personajes originales (protagonista y guardafaro anciano de barba blanca), 7 recursos gráficos separados, 14 fotogramas por personaje, verbos, 2 objetos de inventario, conversación, combinaciones, guardado y un final.
- Todos los 7 recursos gráficos tienen archivos maestros OpenRaster `.ora` con capas editables independientes en la carpeta `source`. Los PNG originales están en `assets`.
- Las imágenes son un prototipo técnico generado con geometría procedural, **NO un producto visual profesional ni un dibujo aceptado**. Falta arte pixel a pixel dirigido, retratos expresivos, animaciones más fluidas, profundidad y aprobación humana.

## Uso

En Windows, abre `INICIAR_JUEGO.cmd` o haz doble clic en `index.html`. Se abre el navegador predeterminado, **sin red, instalación ni arranque con Windows**.

Usa el ratón en la parte inferior para elegir IR, MIRAR, COGER, USAR o HABLAR. Para aplicar un objeto, selecciónalo en el inventario y después pulsa sobre su objetivo en la escena. El botón Guardar crea una partida local del navegador; Cargar la recupera. El botón Pantalla completa conserva el aspecto 16:9. Teclas 1-5 para verbos, espacio para saltar texto, Ctrl+S / Ctrl+L para guardar/cargar.

Secuencia de solución comprobada: recoger lente en el puerto → hablar con el guardafaro → ir al taller → recoger brújula → seleccionar lente y usarla en el mecanismo → seleccionar brújula y usarla en el mecanismo → volver al puerto y usar el faro.

## Arquitectura

- `index.html`, `styles.css`, `game.js`: motor point-and-click sin dependencias remotas.
- `data.js`: escenas y entidades definidas en datos; motor desacoplado de la generación de recursos.
- `art/generate_assets.py`: fuente original reproducible para reconstruir PNG y ORA con Python estándar en un directorio nuevo.
- `scene-harbor.json`, `scene-workshop.json`: contratos inmutables del verificador técnico R88 16:9. Los cambios a recursos deben actualizar SHA, no editar arbitrariamente los manifiestos.
- `qa`: evidencias de Chrome real y capturas del flujo.
- `MANIFEST-SHA256.json`: integridad de archivos del paquete.
- `source`: maestros OpenRaster para Pixelorama y otros editores compatibles.

## Alcance exacto de la aceptación

R88: 35 pruebas del nuevo validador 16:9 y 35 pruebas históricas de R87 pasaron separadamente; ambas escenas pasaron el validador de manifiestos (solo aceptación técnica). R88B: 25 verificaciones de comportamiento completo en Chrome (clics reales, inventario, transiciones, diálogos, guardado, carga, final y ausencia de red), con cero errores. La aceptación artística humana está **PENDIENTE**. Ninguna de estas pruebas demuestra que una IA local haya fabricado autónomamente todo el juego ni certifica AUTOFABRICADOR como fábrica general.

## Próxima integración

Adquirir y verificar SHA, licencias y compatibilidad de Godot 4.6.3 y Popochiu correspondiente, más Pixelorama para animación y edición manual. Exportar las escenas y contratos a Godot, completar hojas de personaje de alta calidad, importar spritesheets, consolidar el sistema de puzles y superar una prueba independiente en otro PC.

La aplicación web incluida **sí se ejecuta como demostración offline**, pero Godot/Popochiu/Pixelorama **NO están instalados** en este paquete. No se reactivaron los supervisores de AUTOFABRICADOR ni se modificó el juego FUJU de otra conversación.
