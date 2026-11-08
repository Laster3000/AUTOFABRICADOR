# AUTOFABRICADOR - HANDOFF INTEGRAL R77
## Relevo a otra IA | 2026-11-08 | DOCUMENTO DE ESPECIFICACION, NO VERSION INSTALADA

**LEE ESTO ANTES DE HACER CAMBIOS.** Este relevo describe el objetivo, la arquitectura requerida, el estado comprobado y el trabajo pendiente. La revision R77 es DOCUMENTAL: no demuestra que los sistemas propuestos ya esten construidos.

### 0. PETICION LITERAL Y PROVENIENCIA

ULTIMA ORDEN LITERAL (usuario, conversacion actual): "guarda todo esto para que no se pierda y ademas dame un handoff para entregarselo a otra IA a ver que puede hacer".

PETICION LITERAL PREVIA DEL USUARIO: "a parte de esto: aceptación de hardware independiente y ampliación del motor generador para que pueda construir nuevas aplicaciones completas, en lugar de limitarse a integrar los componentes y contratos ya probados. Que mas cosas habría que incorporar?"

El resto de este documento es RESUMEN ESTRUCTURADO de la especificacion propuesta por ChatGPT en esta conversacion, mas REFERENCIAS a evidencias reales de R76 leidas del ordenador Windows remoto Laster. NO es una transcripcion FULL de todos los chats historicos. El identificador de conversacion nativo no es accesible aqui: se usa alias local AF-CHAT-R77-HANDOFF-20261108. Donde no hay recibo, marcar UNKNOWN y no inventar evidencias.

### 1. MISION Y LIMITES

OBJETIVO: Construir AUTOFABRICADOR como producto NUEVO, AUTONOMO Y PORTABLE DE INGENIERIA DE SOFTWARE, capaz de recibir peticiones nuevas de programas complejos y hacerse cargo de su ciclo completo: interpretar requisitos, planificar, disenar arquitectura, producir codigo y recursos, integrar, compilar, probar, corregir, empaquetar, entregar, mantener y recuperar. El objetivo no es una demo fija, una coleccion de ejemplos, ni un modelo que solo responde con codigo. NO es posible garantizar de antemano fabricacion perfecta de cualquier software; los tipos de programa se certifican por evidencias independientes.

objectiveId de este producto: autofabricador-independent-reusable-local-ai-factory-20261107
functionalId: AF.FACTORY
revision documental: R77-HANDOFF-ARQUITECTURA-20261108
Esta tarea NO es un encargo para terminar MMC7 ahora. MMC7, MMC5.5, MMC5 y MMC6 se mantienen separados.
Raiz de desarrollo: C:\AUTOFABRICADOR
Raiz portable: C:\AF-PORTABLE
Rescate y pruebas: D:\AUTOFABRICADOR-RESCATE
NO usar F: (lenta/desmontable). NO modificar C:\MMC, C:\MMC7, BOOT, PROD, CURRENT o ROOT de otros productos.
NO iniciar con Windows. Arranque manual bajo demanda, apagado seguro, ningun servicio persistente obligatorio. No activar un candidato como ACTIVE sin su evidencia.

### 2. ESTADO ORIGINAL VERIFICADO QUE SE ENTREGA

R76 es una SUITE DE REFERENCIA INTEGRADA de alcance limitado; NO una fabrica universal autonoma. El cierre R76 reporta:
- Aplicacion web local real: HTTP, SQLite, inicio de sesion, CSRF, CRUD, control de versiones, auditoria, UI.
- Minijuego Canvas 2D y escena WebGL2 interactiva que reutilizan funciones JS del modelo aceptadas en R75.
- Integracion autentificada con Qwen 3.5 9B local CUDA, llamada real comprobada, modelo detenido al terminar.
- Proyecto Android .NET compilado a APK debug firmado; falta ejecutar en Android fisico/emulado.
- API originalmente estancada (28/29) corregida por reparacion DETERMINISTA externa y 53 pruebas WASI. NO atribuir ese arreglo al agente autonomo original.
- Pruebas origen R76: 24 HTTP + 27 Chromium; desde ZIP restaurado: 24 HTTP + 27 Chromium.
- Logica C# Android: 29/29; regresiones de la fabrica: 507 (portable, 24 omitidas) y 490 (desarrollo), ambas salida 0.
- Paquete de referencia ZIP: 29 archivos restaurados por SHA; NO incluye Python ni los pesos del modelo, por lo que no es independiente de todo runtime.
- No hay prueba en segundo Windows fisico ni prueba de APK en dispositivo Android.
- Supervisor en STOP y servidores IA apagados al cierre de R76; estado VIVO debe volver a verificarse en cada reanudacion.

MANIFEST SHA256 R76: 6deb52fa2a9d4f89c47bf578502b7874fc52137b2ac8a141849a75cd13cdab60
ZIP SHA256 R76: 80a1eabc202926a1690df840732899bce2f015f65b0d86efe1e82e3413c359e6
MANIFEST R75 SHA256: 795aa499b97de0fe2ad7d12395f49e0ba5cddd87eee953faddce629956a2bf60
R76 lectura inicial: C:\AUTOFABRICADOR\CONTINUIDAD\R76-FULLAPP-INTEGRATION-20261108\LEEME-PRIMERO-R76.md
R76 manifest: C:\AUTOFABRICADOR\CONTINUIDAD\R76-FULLAPP-INTEGRATION-20261108\MANIFEST-R76.json
R76 checkpoint proyecto: C:\AUTOFABRICADOR\CONTINUIDAD\R76-FULLAPP-INTEGRATION-20261108\R76-PROJECT-CHECKPOINT.json
R76 recibo final: D:\AUTOFABRICADOR-RESCATE\R76-FULLAPP-INTEGRATION-20261108\R76-FINAL-READBACK.json
R76 fuentes/pruebas/recibos: D:\AUTOFABRICADOR-RESCATE\R76-FULLAPP-INTEGRATION-20261108
R76 ZIP: D:\AUTOFABRICADOR-RESCATE\R76-FULLAPP-INTEGRATION-20261108\PACKAGES\AUTOFABRICADOR-R76-REFERENCE-SUITE-CANDIDATE.zip
Prioridad/registro del producto: C:\AUTOFABRICADOR\PRIORIDAD-ACTIVA.json; leer, NO modificar por este handoff.

La experiencia R69-R76 demuestra capacidad real con contratos acotados; R73 revelo tipos de programa que no estaban aceptados; R74 reparo la produccion JSON/Qwen; R75 acepto cuatro familias LOGICAS; R76 construyo e integro una suite de referencia. Ninguna equivale a agente capaz de fabricar libremente una app compleja arbitraria desde cero.

### 3. ARQUITECTURA FINAL: SEIS MOTORES

MOTOR 1 - INTERPRETAR Y DISENAR
  A partir de lenguaje natural producir requisitos funcionales y no funcionales, alcance, supuestos, restricciones, riesgos, UX, esquema de datos, interfaces y criterios objetivos de aceptacion. Gestionar ambiguedades de manera razonable y registrar decisiones; distinguir peticion del usuario de especificacion inferida.

MOTOR 2 - PLANIFICAR Y ORQUESTAR
  Director del proyecto persistente: descomposicion en trabajos por dependencias, agentes especializados reutilizables, seleccion de herramientas/modelos, limites de recursos, checkpoints, leases, cancelacion, reanudacion, bloqueo y cierre por objetivo, sin microparadas innecesarias.

MOTOR 3 - FABRICAR
  Talleres especializados para Windows nativo, web fullstack, juegos 2D, juegos 3D, Android y apps con IA. Codigo, recursos graficos, animaciones, bases de datos, interfaces, tests, dependencias, compiladores, ejecucion aislada y firmados/instaladores segun plataforma. No fingir soporte de un tipo por haber probado solo su matematica.

MOTOR 4 - VERIFICAR Y REPARAR
  Laboratorio independiente con caja negra, oraculos congelados, casos reservados, pruebas funcionales, UI real, red, base de datos, concurrencia, seguridad, accesibilidad, resiliencia, stress, compatibilidad, instalacion, persistencia, actualizaciones, restauracion y regresion. Clasificador de causas y reparador que NO repite source hashes identicos.

MOTOR 5 - EMPAQUETAR Y ENTREGAR
  Dependencias y runtime incluidos cuando sea necesario; ejecutables, APK, PWA, instaladores o paquetes portables segun plataforma; firma apropiada, SBOM/licencias, SHA/CAS, manifest, provenance, ZIP restore byte a byte, despliegue en entorno independiente y rollback probado. Un ZIP con dependencias externas se declara parcial.

MOTOR 6 - MANTENER Y EVOLUCIONAR
  Leer programas existentes, comprender su estructura, modificar componentes por separado, migrar esquema de datos, conservar compatibilidad, gestionar versiones, reproducir errores, probar upgrade/rollback y reutilizar soluciones aceptadas con evidencia.

LOS SEIS SON SISTEMAS DEL MISMO PRODUCTO, NO SEIS FABRICAS PARALELAS.

### 4. SUBSISTEMAS ADICIONALES (PRIORIDADES)

P0-A. Interprete de encargos: schema validado, preguntas solo si bloqueo real, contratos editables y oraculos independientes.
P0-B. Director autonomo de proyectos: grafo de tareas, dependencias, paralelismo limitado, estados, presupuesto, deadlines y responsables.
P0-C. Laboratorio universal de pruebas: black-box E2E por plataforma, casos adversariales/congelados, aceptacion de paquete restaurado.
P0-D. Autorreparacion: detectar estancamiento, causales, estrategias alternativas, reparacion delta y repeticion selectiva.
P0-E. Entornos de build aislados: pin de SDK, toolchains, ABI, modelo, dependencias y sandbox por proyecto.
P0-F. Seguridad de agentes: permisos minimos, secretos fuera de prompts/artefactos, aislamiento del codigo, revision de acciones de alto riesgo, auditoria.
P0-G. Memoria recuperable: segmentos literales accesibles, checkpoints de chat y proyecto, journal, CAS SHA, restore point real, readback y handoff.
P0-H. Entrega integral: distribucion instalable, portable, dependencias, datos, firma, actualizaciones y rollback.
P1-A. Catalogo inteligente de componentes verificados, reutilizacion por content hash, sin reinventar ejecutores.
P1-B. Editor visual modular: ventanas, escenas, sprites, personajes, puertas, robots, dialogos, audio, UI y tests por componente.
P1-C. Motor de modelos/recursos: clasificacion del problema, GPU/CPU/RAM/contexto, cuantizacion, switching, presupuestos de tokens y concurrencia.
P1-D. Mantenimiento de apps existentes: diffs, migraciones, semantic tests, preserve data and backward compatibility.
P1-E. Centro de control: estado autenticado VIVO de agentes/runner/journal, colas, pruebas, logs, uso de GPU y controles PAUSAR/PARAR/REANUDAR.
P1-F. Provenance y dependencias: version, licencias, vulnerabilidades, manifests, signatures, SBOM/formatos interoperares.
P2-A. SDK de extensiones estables con ABI, contrato, registro de capacidades, firmas y rollback.
P2-B. Optimizacion y limpieza segura: temporales con retencion, CAS/LKG/restore protegido, sin borrar recibos o backups.

### 5. CONTRATOS DE SOFTWARE QUE SE DEBEN SOPORTAR Y DEMOSTRAR

1) Windows GUI NATIVA: especificacion libre -> .exe funcional -> interacción real de ventanas/menus -> datos persistentes -> paquete portable/instalacion -> actualizacion y rollback.
2) WEB FULLSTACK: frontend + API HTTP + DB/migraciones + login/roles + sesiones + concurrencia + navegador E2E + upgrade/restore.
3) JUEGO 2D: escenas, personajes, pathfinding, paredes/puertas bloqueantes, colision, estados, dialogos tipo aventura, animacion, audio, inventario, guardar y recuperar.
4) JUEGO 3D: mallas, shaders/camara, inputs, colisiones, fisicas, escenas, prueba grafica de pixeles/frame, rendimiento, compatibilidad GPU.
5) ANDROID NATIVO: APK/AAB compilados, firma, instalacion en dispositivo/emulador, taps/rotacion, persistencia, permisos y desinstalacion/actualizacion.
6) APP INTEGRANDO IA: proveedor local/API, streaming, timeouts, cancelacion, limites de memoria/contexto/tokens, privacidad, resiliencia y tests sin simular modelo cuando se declara E2E real.
7) SOFTWARE EXISTENTE: abrir proyecto ajeno proporcionado, entenderlo, agregar cambio, cero regresiones, empaquetado y migracion segura.
8) PORTABILIDAD: restaurar artefactos SHA en segundo entorno fisico Windows y al menos entorno aislado independiente cuando aplique.
9) SEGURIDAD: entradas maliciosas, prompt injection, SSRF/SQLi/XSS segun plataforma, dependencia adulterada, permisos y secretos.
10) CASOS DE FALLO: timeout, corte de corriente simulado, espacio insuficiente, GPU no disponible, archivo corrupto, error repetido, colision CAS, shutdown solicitado.

Un "PASS" de logica para colisiones NO es un PASS del juego completo. Un APK compilado NO es un PASS del uso en Android. Un modelo mock NO es una IA real. Un entorno aislado de la misma maquina NO sustituye a segundo PC fisico. Las pruebas se definen antes de generar el programa, se ocultan al modelo y no se rebajan despues.

### 6. FALLOS CONOCIDOS Y LECCIONES

- R73: tests de tipos nuevos mostraron limites del generador; no generalizar a partir de modulos de negocio simples.
- R74: Qwen 3.5 9B agotaba tokens en pensamiento; se corrigio la configuracion efectiva JSON y streaming. Verificar parametros REALES del servidor, no solo los solicitados.
- R75: cuatro familias de logica aceptadas (movimiento 2D, proyeccion 3D, API stateless, seleccion de robots), pero API inicial tuvo cierre de proceso incierto, y agente comparaba IDs de texto como numeros. No reintentar UNKNOWN a ciegas.
- R76: API tuvo variable no definida y codigo repetido; reparacion determinista separada supero 53 WASI. NO falsificar aceptacion original como IA autonomamente correcta.
- R76: un primer recorrido de navegador fallo por sincronizacion de UI, no por DB; pruebas deben detectar readiness real.
- R76: app de referencia se construyo con codigo de confianza mas funciones IA aceptadas; no usarla como prueba de codigo fullstack arbitrario autogenerado.
- R76: Android compila y se firma en debug con SDK/JDK de Visual Studio, pero ADB sin dispositivo. No marcar dispositivo PASS.
- En todas las revisiones: diagnosticar error y clasificar deterministic/UNKNOWN. Consultar journal/lease/receipt antes de repetir. Si varios intentos no cambian codigo, pruebas ni aceptacion, cortar la rama repetitiva y cambiar de estrategia.

### 7. DISENO DE CONTRATOS Y ARQUITECTURA INTERNA

Cada encargo deberia tener OBJECTIVE_ID, FUNCTIONAL_ID, RELEASE_ID, OPERATION_ID, CONVERSATION_ID/alias y REVISION_ID distintos; no confluirlos.
Contrato de objetivo: objectiveId, goalLiteral, clarifiedRequirements, intendedPlatforms, acceptancePlanSHA, scope, nonFunctionalRequirements, dataSensitivity, dependencies, budgets, forbiddenEffects, successDefinition.
Contrato de tarea: taskId, parentObjective, neededCapabilities, inputsCAS, expectedOutputs, originalOwner, sandboxPolicy, allowedEffects, maxAttempts, dependencies, runnerLease, journalSequence, terminalState.
Contrato de resultado: operationId, actor/tool/model-version, inputSHA, sourceSHA, testsSHA, buildSHA, packageSHA, evidenceRefs, status, failureClass, readback, nextAction.
Planificador como DAG persistente; un solo registro autoritativo de estado, con cola/journal append-only y lease para cada efecto. SUCCEEDED nunca se reproduce. UNKNOWN exige reconciliacion.
Modelo de capacidad publicado: {id,version,platform,neededToolchain,acceptedScope,ownerVerifier,signature,rollback}. No permitir que una funcion pure-JS se anuncie como "juego 3D completo".
Ejecucion: codigo de modelo dentro de sandbox; librerias y ejecutores originales de confianza para FS/compilacion/verificacion. Limitaciones de acceso al host explicitas.
Memoria: LITERAL/CITA/RESUMEN/RECONSTRUCCION/UNKNOWN_GAP, segmentos accesibles por refs; checkpoint CHAT, checkpoint PROYECTO y RESTORE_POINT de bytes/ensayo son cosas diferentes.

### 8. RECUPERACION, SEGURIDAD Y ECOLOGIA

Al reanudar: leer ultimo LEEME-PRIMERO, manifest, checkpoints del CHAT y PROYECTO, decisiones, R76 LKG, journals, leases, recibos y estado VIVO de ejecutores originales. No tomar un snapshot como monitor vivo.
Antes de cambiar ficheros: G0 sobre instalabilidad/dependencias/autoridad, SHA fuente, preimagen byte a byte, plan CAS, riesgo, prueba de rollback, aplicacion transaccional, readback, regresiones. No modificar componentes productivos o privilegios protegidos sin las autorizaciones exigidas por la plataforma.
Comandos ordinarios autorizan construir/editar/probar/staging sin microconfirmaciones, pero NO invalidan limites de seguridad o privilegios del host.
Sin falsas promesas de trabajo de ChatGPT en background. La ejecucion continua y el contador PARAR 5-4-3-2-1 son requisitos del ejecutor LOCAL, no temporizadores ficticios de ChatGPT; implementar y probar E2E antes de declararlos activos.
No borrar historicos, checkpoints, paquetes LKG, backups o recovery; limpiar solo temporales certificados no esenciales, preferiblemente mediante retencion y cuota.
No usar F:, no copiar datos MMC, no tocar PROD/BOOT/CURRENT/ROOT de MMC; AUTOFABRICADOR no depende de MMC5.5.
No subir a GitHub ni a terceros sin una nueva orden concreta; la portabilidad local es requisito.
Si otra IA no tiene acceso real al ordenador/herramientas, debe producir arquitectura/codigo/contratos y decir que no ha instalado ni ejecutado nada.

### 9. ESTRATEGIA DE TRABAJO EN UN BLOQUE INTEGRAL

FASE A: G0 e inventario de componentes existentes; reconcilia R76 y las herramientas reales. Decide reutilizar codigo y ejecutores por hashes, nunca crear una fabrica paralela.
FASE B: implementa o mejora contrato de objetivo + scheduler persistente + capacidades/talleres + verificador independiente + reparador. Usa una rama/staging candidato y un unico plan de arquitectura.
FASE C: elige un PROGRAMA COMPLEJO REAL NUNCA VISTO por el sistema (sugerencia: simulador de gestion de hospital/almacen con robots, puertas reales, pathfinding y conversaciones), congelando primero oraculos, pruebas de UI y estados. El generador local debe producir el codigo; si lo escribe otra IA, identificarlo como codigo externo y no como exito autonomo local.
FASE D: genera, compila, repara y ejecuta E2E de programa nuevo y paquete restaurado; pruebas de interaccion real, persistencia, seguridad, portabilidad y fallos. Incluye al menos un escenario sin internet.
FASE E: amplia con talleres web, 2D/3D, Android e IA SOLO cuando tengan entorno/owner verificable; mantendios aislados.
FASE F: regresion global, empaquetado, SHA, recibos, readback, checkpoint CHAT/PROYECTO, handoff nuevo y prueba de restauracion real. Si algo permanece bloqueado, aisla la rama y documenta NEXT_ACTION preciso, no declares terminado lo universal.

No dividir cada microprueba en un turno. Avanzar bloques dependientes en la misma intervencion sin inventar aprobaciones. Evitar bucles de lecturas repetidas y polling sin avance.

### 10. MARCADORES DE ACEPTACION M1-M6

M1 CONSTRUCCION: PASS solo con codigo/bundles y evidencia concreta del ejecutor original, no solo archivos preparados.
M2 INTEGRACION: PASS solo con conectores reales, contrato estable y prueba de invocacion.
M3 PRUEBAS: PASS del alcance exacto de cada taller con oraculos de propietario y casos nuevos reservados + regresion.
M4 AUTORIZACION: para efectos Host/BOOT/PROD requiere recibo y actor/planSha; si no hubo instalacion protegida, NOT_APPLICABLE, no contabilizar como PASS.
M5 INSTALACION/ENTREGA: PASS solo si el artefacto objetivo fue empaquetado y restaurado/instalado con recibo original; distinguir fuente, zip parcial y producto autocontenido.
M6 VERIFICACION: requiere funcionamiento real en ambiente destino, persistencia, reinicio/recovery, readback y compatibilidad. Si no hay otro PC o Android, BLOCKED para esa pretension.

Todos los hitos: PENDING / RUNNING / PASS / FAILED / BLOCKED / NOT_APPLICABLE; evidencias con actor, fecha, SHA, operationId, readback. Un candidato NUNCA es ACTIVE.

### 11. PROPUESTA VISUAL CONCRETA DEL PROGRAMA DE PRUEBA

Construir un juego de gestion MODERNO tipo aventura dibujada en 2D (referencias de estilo: Monkey Island / Indiana Jones and the Fate of Atlantis, sin copiar recursos protegidos). Componentes graficos individuales editables: salas, puertas, mobiliario, iconos, robots, personajes, capas, bocadillos, fondos, luces. Las rutas y colisiones deben impedir atravesar paredes y puertas cerradas; comportamiento de agentes logico y comprensible. Interacciones observables en ventana real, eventos y dialogos, guardar y recuperar. La interfaz NO debe tener iconos atravesando paredes ni elementos mal alineados; los actores pueden expresar estados y necesidades con texto. La prueba debe demostrar creacion autonoma del proyecto nuevo, no solo una ilustracion o demo programada por un tercero.

### 12. RESPUESTA REQUERIDA DE LA OTRA IA

Antes de cualquier cambio: indicar acceso disponible y limitaciones, estado original confirmado con ruta y SHA, M1-M6 existentes, capacidades de build instaladas y PLAN UNICO de efecto.
Al ejecutar: conservar recibos originales de cada tool, source SHA, artefacto, casos y resultado; clasificar UNKNOWN sin replay. Completar tareas desbloqueadas autonomamente en el bloque.
Al cerrar: entregar (1) archivos/codigo realmente generados, (2) pruebas E2E originales, (3) lista exacta de tecnologias que FUNCIONAN y las que permanecen BLOCKED, (4) datos de portabilidad, (5) plan de restauracion con bytes verificados, (6) M1-M6 y NEXT_ACTION, (7) continuidad de ESTE chat sin atribuir textos ajenos.
Si solo se ha preparado un plan, reportar PLAN_ONLY. Si se hizo una suite de referencia, reportar REFERENCE_PASS_NO_UNIVERSAL. Si se verifico generacion autonoma abierta bajo alcance acotado, reportar SCOPED_AUTONOMOUS_PASS. No reportar UNIVERSAL_COMPLETE sin cobertura independiente que realmente lo justifique.

### 13. PRIMERA ACCION SUGERIDA A LA OTRA IA

"Reanuda AUTOFABRICADOR desde el cierre R76 y este handoff R77, sin usar MMC5.5 ni F:. Verifica primero manifest y estado vivo de runner/leases. Conserva R76 como LKG y sus pruebas. Diseña e implementa sobre los ejecutores existentes el ciclo autonomo completo con contratos congelados, memoria/continuidad, autorreparacion y talleres por plataforma. Usa una prueba externa nueva y compleja con interfaz funcional, estados y persistencia. Construye, depura, valida, empaqueta y restaura en el mismo bloque tanto como sea realmente posible; no vuelvas a declarar PASS cuando solo se ha generado una pieza. Documenta bloqueos reales y la siguiente accion. No hagas instalacion protegida ni actives una revision sin autorizacion y readback."

FIN DEL HANDOFF R77. ESTE DOCUMENTO ES RELEVO DOCUMENTAL, NO RECIBO DE CONSTRUCCION NI DE INSTALACION.
