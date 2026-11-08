# AUTOFABRICADOR R89E — entrega verificable y límites (8 noviembre 2026)

**Prioridad**: AUTOFABRICADOR, sin reanudar MMC7. Juego original 16:9 nativo (320x180 pixel art, presentación 640x360). Estado **CANDIDATE_NOT_ACTIVE**.

## Producto local
- ZIP: `C:\AUTOFABRICADOR\DIST\AUTOFABRICADOR-R89E-GODOT-16x9-REPRO-PORTABLE-CANDIDATE.zip`
- SHA-256: `0e84861726c54cc9a85e276bf52db41766ca22b1754661543cc650b46e1b54ef`
- Tamaño: 80.211.870 bytes; 45 entradas. Existe copia SHA-idéntica en `D:\AUTOFABRICADOR-RESCATE\R89-ART-ENGINE-169-20261108`. En Windows basta con descomprimir y abrir `INICIAR-JUEGO.cmd`; trae Godot 4.6.3 oficial, no instala servicios.
- Manifiesto del ZIP: SHA-256 `fe490a55b2184cc3654943599e22cdc43cc262185f64836fddda70119110fea6`.
- Continuidad del proyecto verificada con manifiesto SHA-256 `14d5ab69e4964cb904728a0802b097917c921415f830c75c0de915a18a4b01cb`.

## Evidencia original y reproducibilidad
- 3 habitaciones jugables, protagonista original, anciano de barba blanca, 11 assets PNG y 11 masters OpenRaster de dos capas, inventario, puzle, diálogos, guardado, carga y final.
- Godot 4.6.3 ejecutado; 31 owner checks en entorno de desarrollo con Popochiu 2.1.1 como addon/GUI. La lógica del juego sigue en adaptador propio, no en el subsistema de habitaciones de Popochiu.
- 30 owner checks en el standalone Godot, ejecutados sobre una extracción independiente del ZIP R89E.
- 2 reconstrucciones frescas de PNG/ORA con SHA-256 idénticos para las 22 fuentes. 3 manifiestos visuales 16:9 validados sin aprobar la calidad estética. Reconstrucción CI first-party adicional PASS.
- Regresión: 136/136 (34 director + 22 enrutador + 10 juego referencia + 35 visual R88 + 35 visual R87).
- Modelo original GPU CUDA7B: una tarea de geometría rechazada, seguida de **una narrativa original** aceptada bajo contrato JSON y prueba de integración en el observatorio. La IA no construyó autónomamente el videojuego entero. Servidor GPU parado al terminar.
- Godot oficial v4.6.3 y Pixelorama 1.2.2 descargados de GitHub release, SHA-256 cotejado con metadata oficial; Pixelorama ejecuta, pero su exportación automática OpenRaster → PNG no quedó verificada.
- Popochiu v2.1.1 integrado en entorno de desarrollo; **no se incluye en el ZIP standalone ni se distribuyen fuentes tipográficas**. Fuentes y editor se mantienen como herramientas opcionales de desarrollo.

## Reproducción pública
- [Fuentes Godot, escenas, generadores y QA](../examples/adventure-godot-r89e/LEEME-PRIMERO.md).
- [Reconstrucción original de 22 recursos y 3 escenas](../examples/adventure-godot-r89e/ci_verify_art.py).
- [Workflow manual de aceptación GitHub Windows Godot](../.github/workflows/r89e-godot-repro-169.yml). Creado, **aún sin recibo de ejecución de GitHub Actions**.
- No se han publicado assets binarios ni el archivo de 80MB en GitHub; pueden regenerarse los recursos por los scripts y obtener Godot desde el release oficial anclado por SHA.

## Hitos oficiales R89E
| Hito | Estado |
| --- | --- |
| M1 construcción | PASS acotado: 3 escenas y 11 PNG/ORA |
| M2 integración | PASS acotado: Godot, addon editor, standalone propio |
| M3 pruebas | PASS acotado: 136 regresiones, 31 Godot dev, 30 ZIP restaurado, 2 builds deterministas |
| M4 autorización protegida | NOT_APPLICABLE |
| M5 instalación | PASS acotado: paquete portable manual, NO instalación de servicio |
| M6 aceptación final | BLOCKED |

**Pendientes materiales:** acabado visual profesional y aprobación humana a resolución final; automatizar de manera fiable la edición/exportación de pixel art; transformación de adaptador propio a sistema de salas Popochiu si se requiere; demostración de que agentes + IA local fabriquen por sí solos una aplicación compleja completa; prueba en un segundo PC. No declarar AUTOFABRICADOR general terminado ni release ACTIVE.

**NEXT_ACTION:** fortalecer la dirección artística, expresividad, paletas, proporciones, animación y pruebas reales de jugador; luego integrar esa cadena de recursos con la autonomía completa de IA local y aceptación independiente multi-equipo. No interferir con juegos de otras conversaciones.
