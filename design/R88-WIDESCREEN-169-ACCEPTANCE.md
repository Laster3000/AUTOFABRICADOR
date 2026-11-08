# AUTOFABRICADOR R88 — CONTRATO VIGENTE DE VIDEOJUEGOS 16:9

**Decisión explícita del usuario:** videojuego panorámico **16:9 nativo**, no 4:3, no estiramiento y no recorte de un fondo clásico. Esta instrucción sustituye la disposición histórica 4:3 propuesta en R86 y R87 para nuevos videojuegos.

## Sistema de arte y presentación

- Lienzo nativo de pixel art **320×180**, aspecto matemático 16:9.
- Presentación de referencia **640×360** con incremento 2× nearest-neighbor; pantallas mayores mantienen proporción sin deformación de sprites.
- Área del escenario: 320×130; banda de interfaz: 320×50, ambas forman parte del mismo lienzo 320×180.
- Dibujado independiente por capas: fondo, primer plano, sprites, objetos, luces y UI; cada recurso mantiene ID, PNG, fuente editable OpenRaster, SHA y versión.
- Paletas limitadas por escena y personaje; no aceptar un render fotográfico reducido como sprite terminado.
- Hoja de personaje: identidad original, giro/3⁄4/perfil según cámara, pivote, sombra, escalas, atuendos, expresiones y estados idle/walk/talk/look/pick/use/react.
- Comportamiento de jugador: movimiento sobre espacio transitable, cursor claro, respuestas originales a errores, inventario persistente, puzles deducibles, diálogos ramificados, guardado/carga y final.
- **La aceptación artística humana es obligatoria**. PASS de PNG, capas, animación formal y click E2E solo equivale a aceptación técnica acotada.

## Implementación R88 / R88B

Módulo original: `autofab/adventure_visual_gate_r88.py`.
Comando CLI existente: `python autofabricador.py adventure-visual-audit RUTA/scene-harbor.json` — ahora exige 16:9. R87 antiguo queda consultable en `adventure-visual-audit-r87` para auditar históricos, **no** como nuevo valor por defecto.

Ejemplo original jugable: `examples/adventure-169-r88b`. El director de fuentes genera 7 PNG, 7 archivos maestros OpenRaster, 2 contratos de escena y data.js mediante `python art/generate_assets.py`. El juego se ejecuta sin red desde `index.html` o `INICIAR_JUEGO.cmd`.

Entrega verificada en el Host autorizado: `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R88B-AVENTURA-169-PORTABLE-CANDIDATE.zip`; SHA-256 `c737d0d437e7cf2f90373c9a2622c98e8429b2dd52e3934585874868c08bf91d`. Rescate en `D:\AUTOFABRICADOR-RESCATE\R88-AVENTURA-169-20261108`. El ZIP local tiene 29 archivos con readback exacto y aceptación de restauración Chrome.

## Evidencias acotadas

- R88 nuevo: 35 pruebas unitarias del validador panorámico; R87 legado: 35 pruebas sin regresiones.
- Dos contratos de escena con verificación independiente de PNG reales, masters `.ora`, sprites, pivotes, paleta, acción, interfaz y SHA.
- R88B: 25 comprobaciones de Chrome real por clics (diálogo, puzles, inventario, transición, guardar/cargar, final), además de 25 al repetir el itinerario sobre el ZIP restaurado en carpeta separada.
- Sin peticiones de red ni errores JavaScript en esas pruebas.
- Código y manifiestos reproducibles publicados en GitHub; workflow manual de generación `.github/workflows/adventure-169-r88b.yml`. La ejecución GitHub Actions **no se declara PASS hasta tener su propio recibo**.

## Limitaciones explícitas

El arte que acompaña a la demo son sprites geométricos originales de nivel técnico, **no** el acabado ilustrado artesanal que se exige para un producto de calidad comercial similar a Monkey Island 2. Tampoco acredita creación autónoma integral por IA local; el motor es Canvas2D propio, no Popochiu/Godot instalado. Godot 4.6.3, Popochiu compatible y Pixelorama siguen como dependencias candidatas a adquirir con licencia/SHA y aceptación E2E. No se ha realizado prueba física en otro PC.

No declarar AF `ACTIVE`, ni producto terminado, ni instalación de tercero ni 324 programas construidos; mantener MMC7 suspendido. Preservar trabajos FUJU de otras conversaciones.

**NEXT_ACTION:** mejorar radicalmente arte y animaciones con Pixelorama y un artista/QA visual, fijar distribuciones portables Godot + Popochiu e importar el contenido desacoplado; demostrar un ciclo de IA local real que construya una nueva escena bajo el control R88 sin intervención humana en código, y someter su apariencia a aprobación.
