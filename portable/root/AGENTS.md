# AUTOFABRICADOR 0.8.0 — contrato CLI para otras IA

El proyecto independiente está en C:\AUTOFABRICADOR. Ningún agente dispone
de autoridad sobre MMC7, MMC5.5, Host/PROD/BOOT/ROOT, contraseñas o terceros.

## Contrato público

El CLI presenta JSON en stdout y código de salida 0/2. No inventar
capacidades, recibos, estados ni identificadores. Comprobar en vivo:

    python C:\AUTOFABRICADOR\autofabricador.py capabilities
    python C:\AUTOFABRICADOR\autofabricador.py doctor
    python C:\AUTOFABRICADOR\autofabricador.py metrics

Crear encargo con goal, language=python, test_command de unittest,
y acceptance opcional con relativePath bajo examples/test_*.py y sha256.
El owner suministra pruebas de aceptación ANTES de generación.

    python C:\AUTOFABRICADOR\autofabricador.py create <spec.json>
    python C:\AUTOFABRICADOR\autofabricador.py run <AF-jobId>
    python C:\AUTOFABRICADOR\autofabricador.py verify <AF-jobId>
    python C:\AUTOFABRICADOR\autofabricador.py status <AF-jobId>

DRAFT_READY_UNTESTED no equivale a PASS. Los PASS con
independentTestCount=0 solo superaron pruebas escritas por el modelo.
La aceptación distinta se ejecuta dentro de otro invitado WASI y su fuente
pinned no se envía al modelo ni se deja editar por él.

## Estados

PENDING: creado. DRAFT_READY_UNTESTED: archivos generados; falta ejecutar.
MODEL_PENDING, TEST_PENDING o UNKNOWN: reconciliar originales, no repetir
a ciegas. FAILED_ATTEMPT: fallo determinado, el motor puede corregir si
el límite de intentos lo permite. PASS: prueba aislada superada (ver si hay
aceptación independiente). PASS_FIXTURE: prueba de infraestructura, NO IA.
STOPPED: control STOP reconocido, resume y run cuando proceda.
BLOCKED_PROVIDER / BLOCKED_ISOLATION: dependencias ausentes.
FAILED: requiere nuevo trabajo tras análisis.

## Recuperación y costes

Leer continuidad actual (CONTINUIDAD/LEEME-PRIMERO.txt), luego
CHECKPOINT-PROYECTO.json, CHECKPOINT-CONVERSACION.json, manifest,
work/<AF-ID>/state.json, control.json, journal y recibos del ejecutor.
No atribuir contenido de otros chats a esta conversación ni hablar de
transcripción FULL sin acceso literal. No reejecutar SUCCEEDED.

La caché SHA conserva respuestas solo cuando modelo+versión+prompt+
sistema+política coinciden. La tabla de metrics expone tokens y llamadas
reales conocidos, no calcula costes eléctricos no medidos.

## Seguridad

No ejecutar nunca código del modelo con Python anfitrión. Usar WASI
provisionado por bootstrap, sin grants/mounts/red/herramientas de Host.
Una carpeta aislada no equivale a sandbox. No instalar Docker, WSL,
opciones de Windows ni modificar PATH global sin control protegido.
No enviar secretos al modelo. No asumir que la interfaz CLI concede
autorización universal a una IA: necesita herramienta de terminal autorizada.

## Regla operativa

No dividir un trabajo ordinario en microconfirmaciones: intake, generación,
recibos, pruebas, corrección, verificación, empaquetado y continuidad en el
mismo bloque cuando esté permitido. Si un modelo retorna JSON truncado,
persistir UNKNOWN con journal y aislar causa antes de un nuevo job;
no reintentar a ciegas el mismo ID. La lógica local no proporciona
temporizador visual ni control de PARAR E2E probado.


## Compatibilidad de agentes históricos y no acumulación de residuos

`python C:\AUTOFABRICADOR\autofabricador.py agents` distingue las
fases originales de los nuevos adaptadores locales R032; Aider está
cualificado como editor de una fuente, Codex/OpenCode solo como asesores.
Los scripts originales están ligados a MMC7: no importarlos ni ejecutarlos
directamente sobre esta nueva raíz. Las propuestas de un editor externo
exigirían CAS independiente y un sandbox verificado.

`python C:\AUTOFABRICADOR\autofabricador.py housekeeping` lista el
espacio y la limpieza segura en modo DRY_RUN. Con `--apply` limpia solo
bytecode regenerable y rota logs grandes con compresión verificada. No
borra cachés de modelos, estados, UNKNOWN, trabajos, recibos ni rescates.
Al terminar `run` se ejecuta esta limpieza mínima de forma automática.
Los temporales inciertos se conservan y se presentan para reconciliación.


## R032 / versión 0.4.0: contrato de editores locales

Para descubrir capacidades y disponer de los editores en una máquina nueva:

    python C:\AUTOFABRICADOR\autofabricador.py bootstrap-editors
    python C:\AUTOFABRICADOR\autofabricador.py editors
    python C:\AUTOFABRICADOR\autofabricador.py agents

Aider puede proponer UNA fuente y su salida solo se admite con SHA y pruebas
independientes en WASI. Ejemplo: crear el JSON de
`examples/aider_normalize_con_aceptacion.json` y ejecutar
`run-aider AF-ID slugger.py examples/slugger_seed.py`.
El trabajo de origen ha de estar PENDING y tener aceptación fijada.

Codex CLI y OpenCode actúan como asesores de texto en modo local sin permisos
de shell o edición. Comandos: `advise codex AF-ID` y
`advise opencode AF-ID`, cuando el servidor local está READY.
Sus respuestas son orientativas, se registran por SHA y no aceptan ni
instalan cambios. Un PASS previo no dispara asesor ni consume tokens.

Al reiniciar, leer los recibos de R032, el proyecto R031 anterior, los jobs
originales y el estado VIVO del servidor. UNKNOWN y TIMEOUT no se
repiten sin reconciliación; no convertir un asesor en editor sin una nueva
admisión E2E con pruebas propias y sandbox.


## R033: integración universal acotada y misiones recuperables

La versión 0.5.0 **sí ofrece** propuesta textual + aceptación independiente
WASI de una fuente Python mediante cada una de Aider, Codex y OpenCode,
y un controlador de misión secuencial con dos revisores y un editor.

**No dispone** de autoridad de shell/montaje de Host para el modelo, agentes
paralelos reales, instalación Windows protegida, reanudación de UNKNOWN sin
recibo original ni construcción universal de cualquier lenguaje. Nunca
atribuir el propietario/autorización original de MMC7 a esta fábrica.

Verificar en vivo:

    python C:\AUTOFABRICADOR\autofabricador.py agents
    python C:\AUTOFABRICADOR\autofabricador.py editors
    python C:\AUTOFABRICADOR\autofabricador.py metrics

Contrato de trabajo:

    create <spec.json>
    run-source codex|opencode <AF-ID> <file.py> examples/<seed.py>
    run-aider <AF-ID> <file.py> examples/<seed.py>
    reconcile-source <AF-ID>   # solo parser determinista + stdout original
    mission-create <AF-ID> aider|codex|opencode <file.py> examples/<seed.py> --reviewers codex,opencode
    mission-run <AM-ID>
    mission-status <AM-ID>
    mission-stop <AM-ID>
    mission-resume <AM-ID>
    mission-reconcile <AM-ID>
    verify <AF-ID>

La aceptación independiente del propietario debe existir antes del pedido
al modelo. Las propuestas completas se limitan a una fuente y se ensayan
en WASI, no en Python anfitrión. El trabajo pasa únicamente si se
validan los hashes/recibos y las pruebas de aceptación originales.

La misión conserva plan, journal, control y recibos de etapas por separado.
PASS no se reejecuta. STOP solo es inmediato entre etapas; UNKNOWN
requiere reconciliación de ejecución viva. No iniciar el mismo job en
dos misiones ni inventar etapas completadas.

Al reiniciar leer la continuidad R033, el manifiesto, los checkpoints,
los jobs y misiones originales y el estado vivo del servidor/CLI;
no se debe usar un simple snapshot como prueba de proceso activo.


## R034: alcance demostrado y prohibiciones (0.6.0)

Funciones verificadas: Python stdlib con Aider/Codex/OpenCode y WASI;
JavaScript (Javy 9.1.0 + Wasmtime) y TypeScript (tsc 5.9.3 + Javy)
en tareas de fuentes acotadas y owner tests; C# compilación Roslyn
COMPILED_UNEXECUTED, SIN aceptación funcional; supervisor independiente
con cola, PID/lease comprobado y STOP por frontera.

Comandos de lenguaje:

    language-create examples\<spec.json>
    language-run AL-ID codex|opencode
    language-verify AL-ID
    language-status AL-ID
    language-stop AL-ID
    language-resume AL-ID

Comandos C#:

    csharp-create examples\<spec.json>
    csharp-run AC-ID codex|opencode
    csharp-status AC-ID
    csharp-reconcile AC-ID
    csharp-repair AC-ID
    csharp-reconcile-refs AC-ID
    csharp-repair-using AC-ID

Supervisor:

    supervisor-queue language --ref AL-ID --editor opencode
    supervisor-queue mission --ref AM-ID
    supervisor-start
    supervisor-status
    supervisor-stop

No atribuir E2E universal a estos comandos. NO ejecutar ensamblados
C# de IA en Host; NO dar poderes shell/FS a modelos. Los editores nativos
se limitan por políticas y SHA, pero no disponen de aislamiento completo
de su propio ejecutable. Las pruebas JS/TS solo ejecutan Wasm en WASI.
No repetir UNKNOWN/SUCCEEDED ni borrar evidencia, cache útil o modelos.
La reanudación literal es PARCIAL, no hay API de transcript FULL.

## R035: contrato 0.7.0, candidato no activo

Python: Aider/Codex/OpenCode con owner tests WASI originales.
JS/TS: Javy y Wasmtime, y opcionalmente globals Day.js/Lodash previamente fijadas SHA. Sin npm scripts ni acceso a filesystem/red del Host.
C#: Roslyn/componentize-dotnet + Wasmtime WASI2, owner test previo al modelo, fuentes enteras y hashes originales. El intento AC-7c5bac4a13774f1f falló 3/15; su único hijo AC-be5d9f5e81864328 alcanzó PASS 15/15. Preservar ambos recibos.
Supervisor: STOP seguro, reanudación de una tarea sin efectos por el mismo SQ-ID, reconciliación de lease incierto sin replay; no es un servicio Windows.

Comandos:

    bootstrap-extra
    csharp-create examples\csharp_wasi_sum_doubles.json
    csharp-run AC-ID codex|opencode
    csharp-repair-create AC-FAILED
    csharp-verify AC-PASS
    language-create examples\js_pinned_dayjs_lodash.json
    language-run AL-ID codex|opencode
    supervisor-resume-task SQ-ID
    supervisor-reconcile

Nunca declarar funcional un C# COMPILED_UNEXECUTED ni aceptar post-hoc como dueño original. Nunca ejecutar código de modelo con dotnet run sobre Windows ni darle shell al modelo. No instalar npm arbitrario ni modificar MMC7/MMC5.5.

## R036 / AUTOFABRICADOR 0.8.0 (CANDIDATO)

Rutas reales: Python Aider/Codex/OpenCode, JS/TS Javy+WASI, C# componentize-dotnet+WASI. R036 añade alternativa sin editor nativo: direct_agent local llama.cpp streaming, JSON y owner tests WASI. La IA no ejecuta comandos ni herramientas. No asumir que el modelo local tiene acceso a estos programas por sí solo: debe conectarse por CLI.

Trabajo AD-d97a5e0f778944da PASS 11/11; su respuesta original se reconcili ó sin nueva llamada. CP-6be9f4d5874c4405 CANCELLED_VERIFIED desde slot activo y sin replay, 383 fragmentos. Supervisor SQ-003279882d2e4f5f SUCCEEDED con trabajo directo y estado final STOPPED.

Exportación webapp-export: dos apps completas de tipo SPA local, plantilla confiada y lógica de IA comprobada; browser E2E Chrome offline PASS 11 y 12 casos, sin red externa. Paquetes en C:\AUTOFABRICADOR\apps. No soporte genérico React/Node/npm.

Proveedor externo: F:\AUTOFABRICADOR-RESCATE\AUTOFABRICADOR-0.8.0-PRIVATE-VENDOR.zip. Incluye proveedores privados y .wasi-sdk de usuario con SHA. Sin Python, Node, Chrome ni SDK .NET del sistema. Restauración offline en el mismo entorno soportado NO equivale a instalación en Windows limpio.

Comandos: direct-create, direct-run, direct-stop, direct-reconcile, direct-verify, direct-status; cancel-probe-create, cancel-probe-run, cancel-probe-stop, cancel-probe-status; webapp-export, webapp-verify; offline-vendor-inspect, offline-vendor-verify; supervisor-queue direct --ref AD-ID.

NO ejecutar modelo como Host DLL, shell o npm lifecycle. No alterar MMC7/MMC5.5. No reintentar UNKNOWN, PASS, CANCELLED sin recibos. No borrar pesos, vendor, journals, checkpoint, históricos o LKG. Contexto ChatGPT completo no garantizado.

## R037 / ruta exclusiva de rescate y ejecutor de proyectos

ATENCION: cualquier referencia histórica a F:\AUTOFABRICADOR-RESCATE en
R033-R036 queda archivada como origen, NO como destino vigente.
Desde R037 el único destino de rescates de AUTOFABRICADOR es
D:\AUTOFABRICADOR-RESCATE. La carpeta de F fue retirada tras
migración y readback de todos los hashes originales.
Recibo: CONTINUIDAD/R037/F-D-MIGRATION-FINAL.json.
Proveedores: D:\AUTOFABRICADOR-RESCATE\AUTOFABRICADOR-0.8.0-PRIVATE-VENDOR.zip.
No recrear rutas F. Conservar históricos en D y C, no sustituir
paquetes aprobados por una edición de documentación.

Motor de proyectos: direct-create/run con propuesta de 3 módulos JS
reales, corrección acotada y owner WASI; ledger-project-export con
navegador E2E real, respaldo separado, y manifiestos SHA.
No equivale a ejecutar arbitrarios repositorios npm, nativos o DLL Host.


## R038 / AUTOFABRICADOR 0.9.0 CANDIDATE — repositorios ESM, npm fijado y modelo 14B

**Estado de instalacion: CANDIDATO PROBADO EN SU ALCANCE, NO servicio Windows, NO constructor universal de cualquier software.** Se conserva el historico R037/0.8.1 y las 3 entradas Python UNKNOWN originales. El usuario eligio exclusivamente D:\AUTOFABRICADOR-RESCATE como unidad de rescate (NO F:).

### Flujo independiente de repositorios completos dentro del alcance ESM

- Fuente de proyecto `repo-import <archivo.zip> <contrato-owner.json>` admite ZIP no confiables: valida rutas, limite de tamano, archivos .js/.ts declarados, package.json privado type=module sin scripts, npm pin exactamente Day.js/Lodash cuando se requieren. Rechaza traversal, enlaces simbolicos, lifecycle hooks, addons y paquetes arbitrarios; no ejecuta archivos del ZIP al importarlos.
- `repo-create examples\repo_sales_esm_dayjs.json` congela casos funcionales del propietario ANTES de consultar a la IA. `repo-run RJ-ID --provider small|coder14b --max-attempts 3 --max-tokens 2300` consulta el modelo local via HTTP 127.0.0.1, guarda todos los fragmentos originales, journal SHA e intent de cada intento. Para cada modelo admite hasta 3 intentos separados con feedback original de compilador y WASI. STOP y UNKNOWN no hacen replay a ciegas.
- Los modulos `src/*.js` o `src/*.ts` pueden importar/exportar ESM relativas; el compilador `esbuild-wasm@0.25.12` esta fijado por SHA256 y SRI del tar npm original. Un script propio en Node solo analiza y empaqueta; NUNCA eval, require ni importa codigo de la IA en Node. Solo la salida JS se ejecuta con Javy/Wasmtime WASI, sin acceso al Host, archivos o red, con fuel y memoria limitados. Solo Day.js y Lodash UMD previamente auditados; no npm install ni lifecycle scripts.
- `repo-verify RJ-ID` comprueba manifiestos, stream original, modelo, todos los hashes y pruebas propietarias. `repo-export RJ-ID` genera un ZIP de programa ESM con codigo fuente original, HTML/CSS/controlador de confianza y bundle exacto aprobado en WASI. El propio Chrome con contexto offline, CSP y sin permisos ejecuta los casos de interfaz. `repo-export-verify RJ-ID` comprueba el archivo sin repetir IA.
- El `supervisor-queue repo --ref RJ-ID` usa el supervisor persistente con lease PID/nacimiento, journal, STOP cooperativo y resultado SHA. Requiere trabajo PENDING sin intento previo. Rehusar peticiones repetidas de SUCCEEDED/UNKNOWN.

### Pruebas de extremo a extremo reales

1. Repositorio JavaScript ESM de tres modulos y Day.js. El modelo original 1.5B en `RJ-e548f679d85b4f8b` fallo 3 intentos (cada uno paso solo 2/12 casos); su estado FAILED_OWNER_ACCEPTANCE y recibos se conservaron. Un **nuevo** trabajo hijo `RJ-ca8e3c3d64a541ba` con **Qwen2.5-Coder 14B** presente originalmente en la cache Ollama, SHA-modelo `ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed`, gano con 1 inferencia, **12/12 WASI y 12/12 Chrome**. No hubo descarga ni duplicacion de pesos del 14B. Export:
   `C:\AUTOFABRICADOR\repoexports\AF-REPO-RJ-ca8e3c3d64a541ba.zip`.
2. Importacion independiente de ZIP `RI-071016a636a340cb`, con contrato de propietario 10 casos y dos archivos ESM; ejecucion real de fuente con la IA 1.5B mediante el supervisor `SQ-4eb380e338274995` SUCCEEDED. **10/10 WASI y 10/10 Chrome**. El original del ZIP ya era correcto; no afirmar generacion de nuevo algoritmo. Export:
   `C:\AUTOFABRICADOR\repoexports\AF-REPO-RJ-0a8141a5fbb844aa.zip`.
3. Compilacion extraida de fuente privada TypeScript+Day.js con 3 modulos ESM, **6/6 WASI** sin IA, en `CONTINUIDAD\R038\TRUSTED-ESBUILD-DAYJS-SMOKE.json`. Es una prueba del compilador pinneado.
4. Programa de inventario R037 y dos apps anteriores siguen verificados: sus historias/recibos originales no se reescriben.

### Modelos, proveedores y restauracion

El modelito Qwen2.5-Coder 1.5B usa el servidor propio 127.0.0.1:11435; el modelo 14B original de Ollama se puede abrir **a demanda** en 127.0.0.1:11436 mediante `local_escalation.py`. El SHA original del blob de casi 9GB se almacena como recibo de hash completo + identidad/mtime/size, evitando lecturas repetidas a igualdad de preimagen. Se reconcilian PID, comando y lease antes de STOP; al finalizar el trabajo se detiene el servidor. El material original de Qwen 14B esta en cache de usuario; no se promete instalacion offline de ese modelo en otra maquina.

El ZIP privado de proveedores original de 0.8.0 sigue en D y conserva los SHA historicos, sin copiar de nuevo sus 5.87GB. Los 15 archivos del compilador nuevo se guardaron separados:
`D:\AUTOFABRICADOR-RESCATE\AUTOFABRICADOR-0.9.0-MODULE-VENDORS.zip`, con paquete npm original SHA+SRI, script propio y lock. Extraccion fisica y prueba compilacion ESM desde C y D: PASS. **No dejar nada en F**.

Esta revision NO crea un servicio Windows ni ejecuta proyectos Node arbitrarios, React plugins, npm con install scripts, compilaciones nativas C++ o GUI privilegiada. Windows Sandbox/WSL estan desactivados y Docker ausente; sin un aislamiento por SO no se otorgan capacidades nativas a codigo no confiable.

Checkpoint vivo R038: `C:\AUTOFABRICADOR\CONTINUIDAD\R038\LEEME-PRIMERO.txt`. El checkpoint de ChatGPT es PARTIAL, no transcript FULL. No borrar archivos de modelo, historicos ni paquetes con SHA verificado. Siguiente objetivo: sandbox de SO para repositorios arbitrarios y prueba de instalacion/servicio en entorno no protegido sin tocar MMC7/MMC5.5.


## R039 | Windows Sandbox: adaptador 0.9.2 preparado, OS bloqueado

OBJETIVO: ejecutar proyectos nativos y scripts de build solo dentro de Windows Sandbox real, no bajo permisos del Host. R039 NO ha activado caracteristicas de Windows ni reiniciado el equipo.

Lectura G0 07-11-2026: Windows 11 Pro build 26300; HypervisorPresent=True; usuario con token administrador. Containers-DisposableClientVM, WSL, VirtualMachinePlatform y Microsoft-Hyper-V-All DISABLED. C:\Windows\System32\WindowsSandbox.exe NO existe. No se puede demostrar arranque real del Sandbox ni aceptar una compilacion nativa sin instalar esa caracteristica protegida.

NUEVO: autofab/windows_sandbox.py: CLI sandbox-preflight, sandbox-stage, sandbox-verify, sandbox-launch, sandbox-stop, sandbox-reconcile y runner invitado qa/windows_sandbox_guest.ps1. sandbox-stage usa ZIP solo de carpeta examples, comprueba nombres Windows reservados, traversal, symlinks, bomba ZIP, duplicados case-insensitive y scripts declarados. Registra SHA originales, owner separado, journal, nonce y manifest.

El perfil .wsb desactiva networking, clipboard, vGPU, audio, video y printer, activa ProtectedClient, 4096MB, y mapea SOLO entrada read-only y salida nueva dedicada writable. No comparte directorios de usuario ni C:\AUTOFABRICADOR completo. Las aplicaciones, scripts y comandos de terceros NO se ejecutan en Windows Host. Guest-report.json es evidencia NO CONFIABLE: aunque diga PASS nunca certifica pruebas de propietario.

Trabajo original: sandboxjobs/SX-c042df1442744109 STAGED, policy SHA y XML verificados. sandbox-launch devolvio BLOCKED_OS_SANDBOX_FEATURE_DISABLED, launchIntentWritten:false y hostUntrustedCodeExecuted:false. sandbox-reconcile NO_ORIGINAL_GUEST_RECEIPT. Se preservan los 19 trabajos originales aceptados de R038 y los historicos desconocidos, sin replay.

La activacion de la caracteristica Host queda descrita en CONTINUIDAD/R039/OS-ENABLEMENT-READINESS.json con operationId, planSha, preimagen de feature y rollback condicionado. NO se afirma un RESTORE_POINT real de Windows ni una instalacion original autenticada. Por ello la activacion/reinicio real, el servicio Windows y los tests nativos E2E estan PENDING/BLOCKED, no PASS. No guardar ni crear nada en F:. Rescate exclusivo D:\AUTOFABRICADOR-RESCATE.

Fuente oficial Microsoft: https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file. Los directorios writable compartidos pueden ser modificados por codigo dentro del invitado y no deben incluir archivos importantes.

NEXT_ACTION: tramitar activacion protegida/reinicio con rollback y readback autentificados, probar Windows Sandbox E2E real, obtener verificacion independiente de owner y solo despues abordar servicio/instalacion M4-M6.


## R043 / 0.9.4: native Windows Sandbox observado

Ejecutar primero sandbox-preflight. Antes de sandbox-launch: original
control RUN, state STAGED, entradas y WSB por SHA, output privado vacio.
Cada launch genera intent inmutable y no puede repetirse con el mismo jobId.
El invitado puede ejecutar PowerShell solo DENTRO de Windows Sandbox,
nunca ejecutar scripts recibidos sobre Host. Reconciliar con sandbox-reconcile.

Aunque el guest reporte 5/5, esos bytes son UNTRUSTED. El original owner
debe validar independientemente las pruebas, SHA y autorizaciones. No
confundir prueba acotada de invitado con universalidad o instalacion Host.
Los errores/UNKNOWN requieren reconciliacion de journal/lease antes de
cualquier nuevo job diferente; nunca borrar trabajo/historial/recuperacion.

## R044: native repo bridge v0.9.5
repo-native-stage RJ-ID accepts ONLY a previously PASS original repo,
verified SHA and original owner WASI PASS. sandbox-launch SX-ID is a
one-shot original Windows Sandbox launch. repo-native-verify SX-ID checks
original + guest receipt correlation; guest bytes remain UNTRUSTED.
Do not run the accepted JS on Host Node or install a service. Portable package
excludes large Node runtime; this PC has OpenJS-signed 24.20.0 SHA-pinned.

## R045 native persistent cycle
Queue only accepted NC-* with the ORIGINAL supervisor native kind.
Use original SHA, journal, PID+birth. STOP is immediate and propagated.
No blind replay after launch intent. Guest result is untrusted; only
independent original WASI is certified owner acceptance.

## R046 Single original factory intent
factory-submit OWNER JSON orchestrates original repo/WASI/native under
the existing supervisor. Protect original tests and SHA; propagate STOP.
No replay UNKNOWN or SUCCEEDED. Guest is untrusted, not certified owner.
No Host service install or changes to other MMC products.

## R047 Closed owner catalog
factory-request exact catalog text only, never generic free-form user intent
accepted silently. Deterministic owner cases frozen BEFORE model inference.
No replay on prior intent, checksum drift or UNKNOWN. Guest output remains
untrusted: only original WASI owner independently accepted.
R047 artifact: first-party static program ZIP from owner-accepted original
compiled JS, never run model code on Host; no Chrome E2E certification.
Original factory PASS and portable artifact SHA status remain distinct.

## R048 Guest-only original service SCM lifecycle
First-party C# service sample compiled and sha pinned, executed and installed
ONLY in Windows Sandbox. Original guest reports UNTRUSTED; no Host service.
Original signed M4 and full Host restore rollback still absent.

## R049 service-worker is original supervisor
service-worker calls ORIGINAL supervisor.worker, no new factory. Real C# ServiceBase config is guest-only; original SHA-pinned Python/CLI/worker and lease STOP/RUN readback. DO NOT install on Host without original signed M4 and full OS rollback. Never replay UNKNOWN/SUCCEEDED.

## R051 independent factory capacity gate
Original user priority is C:/AUTOFABRICADOR/PLAN-PRINCIPAL.md.
MMC projects/tunnels/Host are unrelated. Real model code must pass original
owner WASI tests before native execution; failed model projects stay failed.
Original repo feedback correlates fixed owner examples, not model-generated
tests. Node process properties are static-denied; no trust in static filter
alone. Release 0.9.11 is a CANDIDATE, not an installed Windows service.


## R052 model progress and safety
Independent original owner acceptance controls all software promotion.
Two identical original owner failures => STAGNATED_OWNER_NO_PROGRESS; no
blind third inference. A complete model response ending by token limit
must not be considered successful. Prior Python UNKNOWN jobs remain
quarantined. 14B model requires measured RAM headroom; no simultaneous
model servers. C# Codex local AOT WASI: original AC-41d34477f42d4097
21/21 but source-only, not installed. AUTOFABRICADOR 0.9.12 candidate,
not ACTIVE. Do not use MMC or F drive; keep D recovery intact.


## R053 BLACKBOX acceptance and safety boundary
Use autofab.blackbox as an evidence recorder ONLY, never as a substitute
for original WASI/C# independent owner tests. Case contract is frozen before
the model call. blackbox-verify checks SHA of every original referenced
receipt and chained journal; no raw user secrets/prompts in events. Count
original EXPECTED REJECT/UNKNOWN as defensive controls, not as software
generation successes. Track missing owner cases and literal failures.
R053 uses bounded 2,812 static adversarial inputs + real JS/TS/Python
model jobs. Native sandbox guest reports are UNTRUSTED. Previous terminal
and UNKNOWN jobs never replay. Javy owner original NUL transport fixed;
no owner contract downgraded. Version 0.9.13 candidate, NOT Host-installed.
Independent AUTOFABRICADOR only, no MMC/F. Preserve C/D LKG and preimages.


## R054 AUTONOMOUS SELF-AUDIT
Supported scope: original first-party repo_factory JS/TS owner failures.
A local pinned advisor MAY diagnose and propose a repaired functional goal.
It NEVER changes original owner tests, trusted Host code, security guards,
privileges, service trust or rollback. Only a NEW original repo_factory
model intent may generate code, and it executes only within first-party WASI;
optional Windows Sandbox claims UNTRUSTED. All original receipts are pinned.
Abort on zero new owner improvement, budget, STOP, UNKNOWN or hostile input.
Whole-system audit-inventory is READ ONLY; Python and browser delivery remain
blocked until original independent acceptance and owner reconciliation.
Never claim ACTIVE or install Host SCM without fully rehearsed OS rollback.
AUTOFABRICADOR independent; no MMC, no F.


## R055 SHA-BOUND HYBRID OWNER REPAIR
Only two trusted, exact first-party code-repair rules: TS numeric -1
sentinel output type and Python ASCII slug literal string.replace misuse.
Never model-write/run on Windows Host. Freeze original source, spec and owner
SHA; execute new repaired code and original independently frozen owner
ONLY in no-network/no-filesystem WASI with bounded fuel. Record all
model failures separately: hybrid PASS != pure AI autonomous PASS. No
modification of owner tests or original terminal/UNKNOWN jobs. Duplicate
specs must reconcile not replay. Browser export original APP_INTENT without
ZIP is UNKNOWN and cannot be repeated blindly; new exports use original
offline Chrome QA. Preserve C/D old release and LKG by SHA. No F or MMC.
M4/M5/M6 protected Windows service gates must not be bypassed.


## R056 ORIGINAL LOCAL PYTHON DIRECT SSE TRUST
Only one new model effect per PD intent, source-only strict JSON.
The transport MUST read [DONE] AND finish_reason stop, original thread
exit and no errors. Other outputs are UNKNOWN/FAILED, never replayed.
Source parsed as data on Host and tested only in no-grants WASI guest.
Original SHA-pinned owner tests are not editable by any model. The
first-party AST repair for an exact literal str.replace mistake MAY
use only one standard import re, and only after the original model
source has failed. Hybrid PASS is not pure AI PASS. New Python STOP
preintent or stream requires original socket/lease readback.
No arbitrary model written Host code, MMC, F, SCM service or privilege
change without original OS-restorable preimage and tested rollback.


## R057 NEW-DOMAIN OWNER AND RECOVERY
Original 12 strict-int and 14 interval tests frozen before model calls.
Do not equate the FIRST PARTY type-guard exact repair 12/12 with pure
model success; original pure model failed, and intervals FAILED owner.
New R057 stream-only original job was recovered from COMPLETE saved
SSE without a model replay, original lease EXITED readback SHA.
Local server STOP receipt now PID+LEASE SHA, preserve old receipts.
R053 browser APP_INTENT was closed INCOMPLETE, not Chrome PASS.
Keep all original source/owner/journal SHA immutable. No generated
Host code execution, service install or MMC/F usage. Safe STOP.
