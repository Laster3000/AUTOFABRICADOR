# AUTOFABRICADOR

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
