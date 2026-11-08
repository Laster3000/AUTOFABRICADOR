# R84 - Megaprueba de capacidades: 18 familias (2026-11-08)

**Estado: diagnostico acotado aprobado; AUTOFABRICADOR NO es aun una fabrica universal.**

## Alcance propuesto de aceptacion

18 familias x 3 dificultades x 3 encargos nuevos x 2 generaciones independientes = **324 aplicaciones nuevas objetivo**. Requisito propuesto: al menos 100 aserciones independientes por app (32.400 minimo), build propio, E2E y restauracion limpia; hardware independiente cuando aplique. Los 324 trabajos no se han ejecutado ni aceptado.

Las 12 familias originales: utilidades CLI, Python y datos, frontend web, backend web, escritorio Windows, ERP, bases de datos, juegos 2D, juegos 3D, Android, colaboracion y aplicaciones con IA.
Las seis categorias adicionales propuestas: escritorio multiplataforma, DevOps/infraestructura, herramientas defensivas de seguridad, multimedia, IoT/embebidos y servicios de sistema.

## Ejecucion verificable R84

| Tipo de comprobacion | Comprobaciones | Resultado |
|---|---:|---|
| Pruebas vivas de admision de contrato, no programas | 36 | 7 admitidos, 5 parciales, 24 rechazados |
| Juego 2D R83F ya generado por Qwen local, oraculo original R81 | 128 | 128 PASS |
| Juego 2D R83F, 24 niveles nuevos no vistos por el modelo, mismo oraculo original | 800 | 800 PASS |
| Regresion de la copia portable, post correccion de test hermetico | 552 | PASS, 24 omitidos |
| Regresion de la raiz de desarrollo, post correccion | 535 | PASS, 0 omitidos |
| **Total de invocaciones de comprobacion** | **2.051** | **24 omitidas** |

El resultado R84 original descubrio que `test_no_export_initial` dependia del estado vivo de exportacion. Se conservaron ambos fallos y se corrigio el test con preimagen, CAS y readback. R84D verifico la correccion en las dos raices (10 pruebas focalizadas por raiz y regresiones 552/535). Esta correccion no cambia el juego ni instala servicios.

El juego aceptado se publica en [examples/r83f-robot-workshop](../../examples/r83f-robot-workshop). Los 24 mapas originales nuevos no se entregaron al modelo; se evaluaron en Chromium aislado y sin red. No se publican oraculos reservados, logs, entornos locales ni pesos de modelos.

## Veredicto

- PASS para la infraestructura acotada de pruebas, el juego 2D generado anteriormente, el nuevo conjunto de mapas y las dos regresiones.
- NO PASS para generar aplicaciones completas de las 18 familias. Muchas familias siguen sin motor y oraculo original independiente; no se han generado 324 aplicaciones.
- No hubo alteracion de la version ACTIVE, arranque Windows, MMC, BOOT, PROD, ni cambios a F:.
- No se certifico un segundo equipo fisico.

SHA-256 manifiesto R84: `2685002a13877a8a45c13f6e57420188d44b12b5589618b73352aebe22662c0e`.

**Proxima accion:** proporcionar toolchains y oraculos originales aislados para las familias no cubiertas y ejecutar la matriz de 324 encargos realmente nuevos, secuenciando los modelos GPU y usando readbacks. Ninguna matriz de pruebas finita demuestra capacidad universal para software arbitrario.
