# AUTOFABRICADOR — prioridad vigente (8 de noviembre de 2026)

## Objetivo principal
Concluir AUTOFABRICADOR como una fábrica de software autónoma, local, reutilizable, portable y verificable: una petición del usuario debe convertirse, mediante agentes internos e IA local, en una aplicación completa nueva con diseño, código, compilación, pruebas independientes, correcciones, distribución y recuperación.

Los proyectos MMC, incluido MMC7, NO forman parte de este trabajo y no deben desarrollarse, modificarse, integrarse ni borrarse desde aquí. Sus históricos se preservan sin importar sus autoridades, dependencias o fuentes.

## Contrato del producto
- Portable y de inicio manual; no instalar arranque automático de Windows ni exigir servicio permanente o reinicio del sistema.
- Reutilizar supervisor, colas, journal, leases, director, agentes, modelos GPU, compiladores, aislamiento y recibos originales del producto.
- Separar especificación/planificación, generación real de aplicaciones, oráculos de propietario independientes del modelo, aceptación E2E y restauración.
- No ejecutar código de IA sin aislamiento; no dar a la IA autoridad sobre Host, credenciales, datos de terceros o sistemas MMC.
- Persistir SHA-256, CAS, preimagen, readback, histórico y checkpoints distintos de conversación y proyecto; UNKNOWN requiere reconciliación y nunca se repite SUCCEEDED.
- Un candidato, una prueba de contrato o un fixture no equivalen a una aplicación autónomamente fabricada o a una versión ACTIVE.

## Evidencia más reciente: R84 (alcance acotado)
La megaprueba preparó una matriz de 18 familias y 324 nuevas aplicaciones objetivo, con al menos 32.400 comprobaciones planificadas, pero no generó esas 324 aplicaciones. Ejecutó 36 sondas de contratos de 12 familias: 7 admisiones acotadas, 5 parciales, 24 rechazadas. Revalidó una aplicación de juego 2D anterior (128 comprobaciones PASS), más 24 mapas nuevos (800 comprobaciones independientes PASS), sin crear aplicaciones nuevas en R84. Seis familias carecen de oráculo E2E/runtimes nuevos. El modo portable y el entorno de desarrollo pasaron regresiones acotadas, no una certificación de fábrica universal.

Estado: CANDIDATE_NOT_ACTIVE; fábrica general NO ACEPTADA.

## Secuencia de ingeniería obligatoria
1. Desarrollar capacidad real de proyectos completos, no solo funciones WASI o integración de plantillas, con agentes internos dirigidos por el plan y sin reescribir una fábrica paralela.
2. Incorporar contratos y oráculos independientes para las familias que aún no pueden fabricar ni verificar aplicaciones completas. Cada runtime debe estar aislado y fijado por SHA.
3. Construir por IA local una aplicación nueva e inédita desde una orden natural hasta paquete y restauración; demostrar correcciones, interrupción segura y readback original.
4. Ampliar por cobertura verificable hacia la matriz de 18 familias / 324 objetivos, ejecutando solo trabajos realmente soportados, y comprobar portabilidad en un segundo equipo antes de declararla universal.

## Hitos y límites
M1 construcción, M2 integración y M3 pruebas: avances parciales/acotados. M4 autorización y M5 instalación protegida: no aplicables al modo manual portable, sin contarlos como PASS. M6 verificación general: bloqueada hasta aceptar aplicaciones completas nuevas y la compatibilidad correspondiente.

Este documento declara la prioridad, no certifica instalación, entrega universal ni tareas que sigan ejecutándose después de la conversación.
