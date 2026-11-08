# AUTOFABRICADOR 0.8.0 — fábrica independiente de software con IA local

**ESTADO: CANDIDATO.** La versión 0.6.0 tiene un ciclo real de generación y
pruebas en WASI para proyectos pequeños de Python. No es una fábrica universal
ni un servicio instalado en Windows. MMC7 y MMC5.5 siguen independientes.

## Función demostrada

- El modelo local Qwen2.5-Coder 1.5B, servido por llama.cpp en 127.0.0.1,
  creó un módulo de operaciones matemáticas y pruebas unittest reales.
- Primer trabajo: AF-34f30fcaa25845f2, 3/3 tests generados por IA PASS.
- Segundo trabajo: AF-4d1f91430b93422d, 3/3 tests del modelo + 7/7 tests
  de aceptación independientes, fijados por SHA, PASS en invitados WASI
  separados. Este trabajo evitó una segunda llamada al modelo por caché SHA.
- La IA consumió 170 tokens de entrada, 256 de salida y 8.219 ms de inferencia
  durante la generación original. La segunda aceptación reutilizó los bytes
  verificados y no generó nuevas llamadas de IA.
- Dos intentos experimentales de otro encargo, AF-2ac6925b0d6a4c10
  y AF-9e420950589242d6, produjeron JSON incompleto por límite de
  generación/contexto. Están UNKNOWN y NO se deben repetir a ciegas.
- El modelo es pequeño y no siempre satisface una especificación a la primera.
  Estos resultados no demuestran fiabilidad general.

## Diseño

- CLI JSON: autofabricador.py (una IA externa puede invocarlo mediante su
  herramienta de terminal; no necesita todo el historial de MMC7).
- Intake y control: work/<AF-ID>/spec.json, control.json, state.json.
- Codificación: modelo llama.cpp local, Ollama opcional, prompts acotados.
- Verificador: Python WebAssembly/WASI sin directorios del anfitrión montados,
  sin red ni herramientas del anfitrión; límites de RAM, tiempo y combustible.
- Aceptación independiente: pruebas ancladas en examples/test_*.py copiadas a
  la carpeta acceptance del trabajo por SHA en el momento de crearlo.
- Cache y recibos: respuestas por SHA, archivos fuente por SHA, tests,
  manifiestos, journal encadenado, preimágenes CAS.
- Limitadores: máximos de intentos, tokens, bytes y tiempo. UNKNOWN no se
  repite automáticamente y PASS no se vuelve a ejecutar.
- Ciclo CLI: el comando run puede arrancar el modelo local bajo demanda y
  detener el proceso propio tras generar código, antes de probarlo en WASI.

## Instalación PORTABLE

Requiere Windows x64 y Python 3.12+; no requiere Docker ni WSL para el motor
de pruebas WASI actual. El ZIP del producto NO lleva el ejecutable de
llama.cpp, el modelo de 1,1 GB ni las ruedas WASI (120 MB). El manifiesto
DEPENDENCIES.lock.json fija versiones, SHA256, URLs y tamaños.

    cd C:\AUTOFABRICADOR
    python autofabricador.py init
    python autofabricador.py bootstrap
    python autofabricador.py doctor

El bootstrap descarga las cuatro dependencias SHA-pinned exclusivamente en
VENDOR/ e instala los dos wheels Python en VENDOR/wasi-runtime (sin pip global,
PATH persistente, registro, servicios ni virtualización). Verifica el
aislamiento con cinco casos negativos en WebAssembly. Si una descarga queda
incierta, mantiene el parcial para reconciliarlo; no reintenta a ciegas.
Respeta licencias de los componentes externos.

## Uso

    python autofabricador.py capabilities
    python autofabricador.py doctor
    python autofabricador.py create examples\calculadora_con_aceptacion.json
    python autofabricador.py run AF-<ID>
    python autofabricador.py verify AF-<ID>
    python autofabricador.py metrics
    python autofabricador.py list

Otras operaciones:

    python autofabricador.py draft AF-<ID>
    python autofabricador.py status AF-<ID>
    python autofabricador.py stop AF-<ID>
    python autofabricador.py resume AF-<ID>
    python autofabricador.py run-queued --limit 5
    python autofabricador.py serve-start
    python autofabricador.py serve-status
    python autofabricador.py serve-stop

run-queued recorre trabajos elegibles en una invocación, no es un demonio ni
una tarea recurrente. STOP se observa en las fronteras seguras; una llamada
en curso puede requerir llegar al límite de tiempo o finalizar.

## Pruebas y recuperación

    python -m unittest discover -s tests -v
    python autofabricador.py bundle
    python autofabricador.py verify-bundle DIST\AUTOFABRICADOR-0.4.0.zip

El empaquetador crea un ZIP con manifiesto SHA-256, restaura a una carpeta
temporal y ejecuta las pruebas de biblioteca antes de crear el recibo. RESCATE
se mantiene fuera de C:\AUTOFABRICADOR y se ensaya de forma independiente.
El protocolo para otra IA está en AGENTS.md.

## Seguridad

Las pruebas de código no confiable se ejecutan dentro de WASI sin acceso
declarado a la máquina anfitriona. Se verificaron cinco denegaciones reales:
rutas de proyecto/usuario/unidad, red y procesos. El aislamiento WebAssembly
no es una garantía absoluta contra vulnerabilidades del runtime. El modelo
local no es seguro para tareas que requieran credenciales o Host protegido.
El motor actualmente solo soporta Python estándar de un directorio y unittest;
la versión de Docker es una alternativa separada no instalada. Ejecuciones
arbitrarias de shell, compiladores C# y acceso privilegiado no están activados.

Los tests escritos por la IA no constituyen aceptación independiente. Los
encargos sin pruebas de aceptación propietarias solo verifican autopruebas del
candidato; el CLI identifica el recuento independiente como cero. No se
puede prometer coste cero de electricidad, hardware o almacenamiento.
No se han medido ahorros porcentuales generales.

## Estado y siguiente objetivo

M1 construcción: fuente 0.3.0 preparada.
M2 integración: llama.cpp, WASI, CLI y caché integrados; se observaron
dos trabajos PASS, pero la robustez para encargos diversos queda abierta.
M3 pruebas: suite interna, test real con aceptación independiente y
restauración física del paquete (ver recibos de DIST y CONTINUIDAD/R023).
M4 autorización Host: no aplica a esta entrega sin cambios protegidos.
M5 instalación Host: no realizada (distribución portable).
M6 verificación amplia: pendiente, no confundir con E2E acotado de Python.

NEXT_ACTION: endurecer manejo de resultados incompletos y la fiabilidad de
modelos pequeños; ampliar lenguajes, modelos, selección de coste y agentes
persistentes con evidencias independientes. La saturación interna de ChatGPT:
DESCONOCIDA.


## R031: Reutilización selectiva de agentes históricos y limpieza

La arquitectura original de MMC7 tenía agentes y adaptadores específicos para
Codex CLI, OpenCode y Aider. No eran intercambiables directamente con AUTOFABRICADOR:
dependían del controlador original de MMC7 y del acceso a sus archivos,
herramientas y modelos. **Sus ejecutores originales no se han importado**;
los adaptadores independientes cualificados se documentan en R032 más abajo.
Consulta `python autofabricador.py agents` para conocer las fases activas
y el estado de esas integraciones opcionales. No se crean agentes nuevos por
mostrar sus nombres. La evaluación detallada, con hashes de fuentes, está en
`CONTINUIDAD/R031/REUTILIZACION-LEGACY.json` si está disponible.

Se reutilizaron *patrones* comprobados, adaptándolos al producto independiente:
CAS antes de efectos, STOP/UNKNOWN sin replay, verificación por recibo,
aceptación separada y un guard de fuente repetida que impide volver a probar
código esencialmente idéntico que falló con evidencia determinista.
Para incorporar un editor externo se exige sandbox/alcance, binario fijado,
autoridad de edición y prueba E2E, no basta con haberlo usado antes.

### Higiene automática y verificable

Al terminar un `run` normal, AUTOFABRICADOR ejecuta mantenimiento
conservador de su espacio propio. Solo elimina archivos `__pycache__/*.pyc`
regenerables de rutas exactas de código/pruebas, y puede comprimir un log
`*.log` que exceda 2 MiB cuando **no hay lease de servidor**. El
log se vuelve a leer desde gzip y se comprueba SHA antes de reemplazar su
contenido; el histórico comprimido se conserva, no se borra.

No se borran modelos, binarios, ruedas offline, caché de WASI (evita recompilar),
respuestas útiles por SHA, trabajos PASS, trabajos UNKNOWN, pruebas, journals,
checkpoint, preimágenes, recibos ni backups. Las descargas parciales o
directores STAGE inciertos se señalan para reconciliación, nunca se destruyen
por edad sin evidencia.

    python autofabricador.py housekeeping
    python autofabricador.py housekeeping --apply

El primer comando es **DRY_RUN**, sin efectos. El segundo utiliza la política
restrictiva anterior y registra las acciones en continuidad. Para limpieza
del laboratorio antiguo MMC7 se debe realizar otra auditoría independiente;
este comando nunca toca D:\LABORATORIO ni C:\MMC7.


## Revisión R032: editores portables integrados, 0.4.0

La información anterior de R031 es histórica. La versión actual distingue **tres
capacidades comprobadas**, con restricciones distintas:

- **Aider 0.86.2**: editor de una sola fuente, modelo local llama.cpp, edición
  CAPTURADA SIN APLICAR por el propio editor. AUTOFABRICADOR comprueba SHA y
  ejecuta el candidato dentro de WASI; solo declara PASS al superar pruebas
  independientes fijadas desde la admisión. Trabajo real
  `AF-36984db99f214214`: 7 pruebas PASS, 6 del propietario
  y 1 prueba de importación de la fábrica, sin ejecución de código del modelo
  directamente en Windows. El primer intento
  `AF-9480031620264dc2` quedó UNKNOWN tras una solicitud contradictoria;
  no se reintentó con el mismo ID.
- **Codex CLI 0.167.0**: responde con un modelo local mediante interfaz Responses;
  modo read-only, sin herramientas de shell, sin autorización de cambios ni
  sesión persistente. Protocolo real y consulta como **asesor** verificados;
  NO edita código ni ha probado aceptación propia.
- **OpenCode 1.19.5**: responde con el modelo local usando un agente de
  permisos DENY-ALL y proveedor de red local. Consulta como asesor, recibo
  y reutilización SHA de respuesta verificados; NO edita código ni acepta
  candidatos por su cuenta.

La fábrica sigue siendo **un flujo determinista con especialidades**, no
un sistema de tres LLM distintos trabajando autónomamente en paralelo.

### Preparación privada en Windows

Las dependencias del motor se instalan con `bootstrap`.
Los **editores opcionales**, separados del núcleo, se instalan/verifican con:

    python autofabricador.py bootstrap-editors
    python autofabricador.py editors
    python autofabricador.py agents

Versiones y SHA de los ejecutables están fijados en `EDITORS.lock.json`.
El instalador utiliza npm con `--ignore-scripts` y `--prefix` dentro de
VENDOR/editors y un entorno Python privado para Aider. No instala servicios ni
cambia el PATH global. Los binarios de terceros se almacenan fuera del ZIP
pequeño del producto; su recuperación puede requerir acceso a npm/PyPI. Las
dependencias transitivas de Aider no están todavía congeladas byte a byte.

### Uso operativo

Para Aider, el ejemplo incluye un archivo inicial, un encargo concreto y
las pruebas de aceptación SHA fijadas:

    python autofabricador.py create examples\aider_normalize_con_aceptacion.json
    python autofabricador.py run-aider AF-<ID> slugger.py examples/slugger_seed.py
    python autofabricador.py verify AF-<ID>

Cada `run-aider` requiere un trabajo PENDING nuevo, con aceptación
independiente. Si la petición falla o queda incierta, no repite el intento
automáticamente. Un editor NO recibe acceso a la raíz C:\MMC7.

Para pedir asesoramiento sin efectos a un trabajo que no ha pasado:

    python autofabricador.py advise opencode AF-<ID>
    python autofabricador.py advise codex AF-<ID>

Las sugerencias no cambian estado, no escriben fuentes ni ejecutan comandos
del modelo. Consultas con el mismo prompt/modelo/herramienta reutilizan
el recibo por SHA y no hacen una segunda llamada.

### Higiene y límites

No se elimina automáticamente ningún checkpoint, prueba, archivo de modelo,
compilación WASI reutilizable, respaldo o trabajo UNKNOWN. El mantenimiento
solo retira bytecode regenerable y archiva logs grandes de forma reversible.
Las dependencias opcionales pueden ocupar bastante disco, pero se instalan
una sola vez y se verifican sin volverlas a descargar.
Revisión y recibos: `CONTINUIDAD/R032`.

Todavía NO hay integración autónoma de los mecanismos originales de edición
con Codex/OpenCode ni construcción general C#/.NET. M1–M3 se han demostrado
para el alcance acotado Python/Aider, M4 no aplica, M5 instalación del Host
no realizada y M6 autonomía general pendiente.


## R033 / 0.5.0: editor universal acotado y misiones multirol

**ESTADO CANDIDATE_NO_ACTIVE.** Este apartado actualiza las limitaciones
históricas de R031/R032 descritas arriba. Está demostrado para proyectos
Python pequeños, no para MMC7, C#, aplicaciones grandes o instalaciones Host.

### Qué se ha construido y probado

- **Aider 0.86.2**: entrega una propuesta completa de UNA fuente sin
  aplicarla. AUTOFABRICADOR fija su origen por SHA, ejecuta una prueba
  de importación de la fábrica y las pruebas independientes originales en WASI.
- **Codex CLI 0.167.0**: tanto consulta local como propuesta textual de código
  en modo read-only, comandos shell deshabilitados y sesión efímera. El código
  propuesto se incorpora solo al trabajo de prueba y se acepta por WASI.
  Un bloque Markdown envolviendo JSON se recuperó a partir de la salida
  ORIGINAL, con recibo de reconciliación, sin una nueva inferencia.
- **OpenCode 1.19.5**: tanto consulta como propuesta textual de código,
  herramientas DENY-ALL, modelo local y salida registrada. Mismo sistema
  de aceptación WASI; el editor nunca obtiene permiso para aplicar cambios
  al Host. En este alcance, Aider/Codex/OpenCode han completado cada uno
  un caso de propuesta real con siete pruebas independientes.
- **Controlador de misiones**: a partir de un job aceptado por intake,
  encadena cero, uno o dos revisores de texto con Aider/Codex/OpenCode como
  editor final, verificación original, journal propio y estados persistidos.
  STOP detiene en fronteras seguras; una inferencia ya iniciada no se cancela
  inmediatamente. UNKNOWN no se reenvía a ciegas. Los stages SUCCEEDED
  no se reejecutan. El servidor local permanece cargado solo durante
  la ejecución de la misión y se detiene al final si fue arrancado por ella.

### Operación en una sola llamada

    python autofabricador.py bootstrap
    python autofabricador.py bootstrap-editors
    python autofabricador.py doctor
    python autofabricador.py editors

Generar código con un editor, sin permisos de herramientas:

    python autofabricador.py create examples\codex_clamp_aceptacion.json
    python autofabricador.py run-source codex AF-ID bound.py examples/bound_seed.py
    python autofabricador.py verify AF-ID

La primera respuesta del modelo se almacena como recibo original. Solo
cuando el error ya es determinista, está completamente registrado y se
trata de un fallo del analizador corregible se permite:

    python autofabricador.py reconcile-source AF-ID

Este comando **nunca vuelve a consultar el modelo**. No repara UNKNOWN
ni intenta reconstruir respuestas parciales.

Secuencia multirol con control de parada/reanudación:

    python autofabricador.py create examples\mission_parity_aceptacion.json
    python autofabricador.py mission-create AF-ID aider parity.py examples/parity_seed.py --reviewers codex,opencode
    python autofabricador.py mission-run AM-ID
    python autofabricador.py mission-status AM-ID
    python autofabricador.py mission-stop AM-ID
    python autofabricador.py mission-resume AM-ID
    python autofabricador.py mission-reconcile AM-ID

Una interrupción incierta no autoriza nueva ejecución: `mission-reconcile`
únicamente avanza si encuentra el recibo original SHA de una etapa ya
SUCCEEDED, su journal y la evidencia del trabajo delegado. De otro modo
conserva UNKNOWN. Misiones y trabajos se diferencian por sus propios IDs.

### Seguridad y tamaño

El único intérprete que ejecuta código creado por el modelo es el
verificador WebAssembly/WASI, sin red, montaje de carpetas ni procesos de
Windows. Los editores externos siguen siendo programas confiados de terceros
ejecutados en espacio de usuario; la prohibición de herramientas se configura
y se comprueba mediante eventos de salida, **pero no equivale a un contenedor
OS completo** para sus propios binarios.

Se conservan los estados, recibos, cachés por SHA, modelos y el rescate.
El mantenimiento automático solo quita bytecode regenerable y comprime logs
grandes con verificación de recuperación. Los paquetes opcionales de
Aider/Codex/OpenCode se instalan fuera del ZIP de fuente: sus dependencias
aún no cuentan con cierre completo de hashes transitivos para reinstalación
bit a bit sin red.

**No se ha instalado un servicio de Windows** ni iniciado un ejecutor
recurrente. La misión corre durante la llamada al CLI; el estado persiste
entre llamadas. Los contadores reales separan llamadas a modelos, consultas
de asesores y reutilización SHA, pero no miden energía o coste de hardware.

**Evidencias y continuidad:** `CONTINUIDAD/R033/LEEME-PRIMERO.txt`,
manifest y originales en `work/` y `missions/`.
La autonomía general, los proyectos multilenguaje y la integración E2E
de botones de PARAR/temporizador todavía no están demostradas.


## R034 / AUTOFABRICADOR 0.6.0: JS/TS reales, C# compilación y supervisor

**ESTADO: CANDIDATE_NO_ACTIVE.** Esta sección sustituye los límites
históricos de R031–R033, sin declarar que MMC7 o AUTOFABRICADOR universal
estén instalados como servicios del Host.

### Programación real JS/TS con IA local

Los trabajos `AL-ID` tienen su contrato inmutable,
semillas de fuente y pruebas del propietario fijados ANTES de invocar al
modelo. El editor externo (Codex u OpenCode) devuelve únicamente un mapa
de fuentes. No se permite al modelo ejecutar comandos, instalar npm ni
editar los archivos del sistema.

El compilador Javy 9.1.0, fijado por SHA, transforma el JavaScript en un
módulo Wasm. Para TypeScript se usa primero tsc 5.9.3, también fijado
por SHA. **Solo el módulo Wasm generado se ejecuta**, en un nuevo guest
Wasmtime/WASI sin carpetas preabiertas, sockets ni red, con límites de
memoria/instrucciones. Se compara cada resultado con pruebas
independientes previas; nada se acepta por el mero éxito de la compilación.
El modelo no tiene acceso a los casos de aceptación por esta interfaz.
Los ejemplos probados incluyen una biblioteca de dos archivos JavaScript
(12 pruebas independientes) y una biblioteca de dos archivos TypeScript
(12 pruebas independientes), además de programas pequeños.

    python autofabricador.py language-create examples\js_bounded_sum.json
    python autofabricador.py language-run AL-ID codex
    python autofabricador.py language-verify AL-ID
    python autofabricador.py language-status AL-ID
    python autofabricador.py language-stop AL-ID
    python autofabricador.py language-resume AL-ID

La deduplicación devuelve el trabajo `AL-ID` ya aceptado al repetir
el mismo contrato y prueba sus recibos, sin volver a gastar inferencia.
Los trabajos FAILED/UNKNOWN no se rehacen a ciegas. Esta vía admite
scripts JS/TS estándar sin imports/exports ni Node/npm; NO ofrece una
fábrica general de aplicaciones Node, Express, frontends o TypeScript
con dependencias externas.

### C# y .NET sin ejecución peligrosa

Se usa Roslyn 10.0.401 y referencias del framework fijadas; se invoca
el compilador directamente, **sin MSBuild, NuGet, generadores de código
ni ejecutar DLLs**. Una biblioteca real de dos archivos se compiló,
tras una reconciliación de JSON sin nueva llamada y dos reparaciones
deterministas acotadas. Los recibos de los intentos fallidos se conservan.

    python autofabricador.py csharp-create examples\csharp_bounded_sum.json
    python autofabricador.py csharp-run AC-ID codex
    python autofabricador.py csharp-status AC-ID

Para los dos casos conocidos y solo cuando el recibo original demuestra
su causa, existen los comandos acotados `csharp-reconcile`,
`csharp-repair`, `csharp-reconcile-refs` y
`csharp-repair-using`. No reintentan inferencias; registran
preimágenes/errores y reparaciones. Si los intentos no resuelven la causa,
el trabajo queda FAILED sin perseguir parches indefinidamente.

**C# se clasifica como COMPILED_UNEXECUTED, no PASS funcional**, porque
esta máquina no dispone de un guest WASI/.NET ni Docker/WSL validado.
La compilación no es una prueba de comportamiento.

### Supervisor local persistente

El proceso `supervisor-worker` es un ejecutor local de usuario,
independiente de la conversación, NO un servicio Windows registrado.
Tiene PID y tiempo de creación del proceso comprobables (evita falsos
leases por reutilización de PID), cola persistente por operación SQ-ID,
journal original, control RUN/STOP y recibos de cada proceso hijo.
Solo ejecuta comandos de AUTOFABRICADOR expresamente permitidos.

    python autofabricador.py supervisor-queue language --ref AL-ID --editor opencode
    python autofabricador.py supervisor-start
    python autofabricador.py supervisor-status
    python autofabricador.py supervisor-stop

También permite `supervisor-queue mission --ref AM-ID`.
El supervisor fue probado con una tarea sintética realmente cancelada y
con una generación local de código real: recibió STOP en MODEL_PENDING,
registró stopRequestedDuringChild y terminó la etapa en una frontera
segura sin duplicarla. No mata indiscriminadamente los procesos,
porque ello podría producir UNKNOWN o perder evidencias. Si ya existía
SUCCEEDED, conserva el recibo y no vuelve a ejecutar.

### Estado de aislamiento y economía

Se mantiene una separación entre código generado y programas anfitriones.
Javy/tsc/Roslyn son herramientas de compilación nativas de confianza; el
WASM resultante corre aislado, pero no se ha demostrado una sandbox OS
completa para cada editor de terceros. No afirmar que la ejecución de
código Node/npm general es segura.

`python autofabricador.py metrics` muestra por separado
trabajos Python, JS, TS, C# sin aceptar y cola del supervisor. No contabiliza
dos veces las reparaciones deterministas. El coste nube conocido sigue
siendo cero para estos modelos locales, pero consumo eléctrico y coste
de hardware no están medidos.

El producto conserva los trabajos, caches útiles, modelos, verificaciones
WASI, archivos desconocidos, supervisión y rescate. La limpieza solo borra
bytecode regenerable propio y comprime logs voluminosos de forma reversible.
**No se han modificado C:\MMC, C:\MMC7 ni su BOOT/PROD/ROOT/CURRENT.**

Recuperación R034: `CONTINUIDAD/R034/LEEME-PRIMERO.txt`
y los ZIP de fuente/evidencia guardados en
`C:AUTOFABRICADOR-RESCATE` y `F:AUTOFABRICADOR-RESCATE`.

## R035 / AUTOFABRICADOR 0.7.0 — C# WASI real, npm fijado y recuperación de supervisor

**Estado: CANDIDATE_NO_ACTIVE.** Esta sección actualiza el estado histórico R031-R034. No hay una fábrica universal ni un servicio Windows instalado.

### C# con pruebas funcionales independientes

El SDK confiado componentize-dotnet 0.8.0-preview00011 compila C# a WebAssembly/WASI 0.2. Wasmtime CLI 50.0.1, fijado por SHA, ejecuta el componente en un proceso separado sin directorios, red, variables del anfitrión ni permisos para ejecutar comandos del Host, con límites de tiempo y memoria. Las fuentes del modelo jamás se ejecutan como DLL Windows ni pueden aportar proyectos MSBuild o scripts de instalación.

Los casos del propietario (class, method, parameterTypes, returnType, cases) se fijan ANTES de llamar a la IA. El harness independiente utiliza un testigo aleatorio. Tipos admitidos: int, int[], bool, string; 5 a 60 casos. Se rechazan fuentes mal formadas y salidas sin aceptación.

Trabajo original AC-7c5bac4a13774f1f, Codex: FAILED_WASI_OWNER (3/15). OpenCode creó una revisión hija AC-be5d9f5e81864328: PASS 15/15 sobre contrato previamente fijado y SHA del origen. La revisión hija no reejecutó ni reescribió la anterior. El trabajo antiguo R034 AC-aa1970e969314730 conserva su estado COMPILED_UNEXECUTED, aunque fue probado post-hoc; no atribuir aceptación original retroactiva.

    python autofabricador.py csharp-create examples\csharp_wasi_sum_doubles.json
    python autofabricador.py csharp-run AC-ID codex
    python autofabricador.py csharp-repair-create AC-ID-FAILED
    python autofabricador.py csharp-verify AC-ID-PASS

Máximo una revisión hija por fallo original. Si el modelo repite la fuente defectuosa o conserva una función anterior no corregida, marcar FAILED_STAGNATION y no generar infinitos reintentos.

### Dependencias npm sin scripts Windows

La librería JavaScript aislada admite dependencias UMD explícitamente permitidas: dayjs@1.11.13 y lodash@4.17.21. Las versiones, integridades npm SHA-512 y SHA-256 del archivo se comprueban por separado antes de ejecutar exclusivamente dentro de Javy/Wasmtime WASI, sin cargar scripts de npm o binarios Node en Host. AL-11447b7cc20e45da generó un programa que combina ambas bibliotecas: PASS 12/12 casos originales, manifest original y hashes preservados.

    python autofabricador.py language-create examples\js_pinned_dayjs_lodash.json
    python autofabricador.py language-run AL-ID opencode
    python autofabricador.py language-verify AL-ID

No se admiten dependencias npm arbitrarias ni proyectos completos Node/React/Express. Esa ampliación requeriría un bundler y una sandbox de paquetes más general, todavía sin E2E.

### Supervisor recuperable

SQ-5c331895c7f648cb comprobó una parada sin efectos, reanudación bajo el MISMO identificador y finalización SUCCEEDED; el worker terminó STOPPED. El supervisor verifica PID más nacimiento del proceso y conserva journal con SHA. En caso de lease huérfano, la reconciliación valida recibos originales o clasifica UNKNOWN. Jamás reproduce un SUCCEEDED ni una ejecución incierta a ciegas.

    python autofabricador.py supervisor-resume-task SQ-ID
    python autofabricador.py supervisor-reconcile
    python autofabricador.py supervisor-status

La parada se aplica en fronteras seguras, no es una interrupción instantánea del LLM. No hay servicio Windows ni autostart global.

### Bootstrap, espacio y recuperación

    python autofabricador.py bootstrap-extra

El bootstrap usa Wasmtime ZIP fijado por SHA, Day.js/Lodash npm verificados y el proyecto .NET fijo del laboratorio. Puede descargar toolchains grandes en la primera instalación; componentize-dotnet guarda un SDK WASI reutilizable en %USERPROFILE%\.wasi-sdk. Se conservan estos recursos útiles; no se incluyen pesos de modelo ni proveedores grandes en cada ZIP de fuente/evidencias.

El ZIP de código se restaura independientemente y puede ejecutar sus pruebas en modo sin dependencias opcionales (pruebas específicas omitidas); esto NO demuestra instalabilidad completamente offline. La cápsula de evidencias conserva journals, jobs, misiones y supervisor por SHA. Consultar CONTINUIDAD/R035/LEEME-PRIMERO.txt, checkpoints y MANIFEST.json antes de reanudar.

No se han autorizado modificaciones a C:\MMC ni C:\MMC7, Host/BOOT/PROD/ROOT/CURRENT. La autonomía universal, la cancelación inmediata de inferencias y el servicio Windows siguen pendientes.

## R036 / AUTOFABRICADOR 0.8.0 — app real, modelo directo, cancelación y respaldo

ESTADO: CANDIDATE_NO_ACTIVE. No hay servicio Windows ni fábrica universal de cualquier aplicación. Esta revisión no modifica MMC7 ni MMC5.5.

### Modelo directo y cancelación

El módulo autofab/direct_agent.py consulta por streaming al GGUF local fijado mediante SHA, en http://127.0.0.1:11435/v1/chat/completions. No ejecuta Aider/Codex/OpenCode ni acepta shell, herramientas, comandos o edición de archivos del modelo. La respuesta se almacena y verifica mediante contrato de pruebas del propietario fijado antes de preguntar a la IA. El JavaScript propuesto se ejecuta exclusivamente dentro de WASI.

Comandos:
    python autofabricador.py direct-create examples\direct_triple.json
    python autofabricador.py direct-run AD-ID
    python autofabricador.py direct-verify AD-ID
    python autofabricador.py direct-stop AD-ID
    python autofabricador.py direct-reconcile AD-ID
    python autofabricador.py direct-status AD-ID

El trabajo AD-d97a5e0f778944da pasó 11/11 pruebas funcionales WASI y no lanzó ningún editor nativo. La respuesta original era un mapa JSON directo; fue recuperada sin otra llamada al modelo. El supervisor ejecutó y aceptó otro trabajo directo en la cola SQ-003279882d2e4f5f.

La prueba de cancelación activa CP-6be9f4d5874c4405 observó is_processing=true ANTES de STOP, desconectó el transporte tras 383 fragmentos y verificó posteriormente que todas las ranuras del servidor estaban inactivas. Estado CANCELLED_VERIFIED y ningún código parcial aceptado. Esta cancelación se demuestra para la ruta HTTP directa; los editores nativos anteriores conservan parada por frontera segura.

    python autofabricador.py cancel-probe-create
    python autofabricador.py cancel-probe-run CP-ID
    python autofabricador.py cancel-probe-stop CP-ID
    python autofabricador.py cancel-probe-status CP-ID

### Dos aplicaciones web completas en el alcance de una SPA local

El exportador webapp-export combina la lógica original ya aceptada en WASI con plantillas propias de index.html, styles.css y controller.js. Se generan formularios interactivos y un ZIP portable en C:\AUTOFABRICADOR\apps. Un segundo test de interacción utiliza Chrome real con Playwright-core privado, contexto offline, permisos vacíos, CSP connect-src 'none' y bloqueo de peticiones externas.

La aplicación triple obtuvo 11/11 pruebas WASI + 11/11 de Chrome. La aplicación reportDate, con Day.js y Lodash autorizados por SHA, obtuvo 12/12 WASI + 12/12 Chrome.

    python autofabricador.py webapp-export AD-d97a5e0f778944da
    python autofabricador.py webapp-export AL-11447b7cc20e45da
    python autofabricador.py webapp-verify AD-d97a5e0f778944da

Los ZIP se abren en un navegador sin servidor y no requieren internet. Es una aplicación web estática con una función JavaScript comprobada; NO equivale a compatibilidad con proyectos arbitrarios de Node/React/Express, npm con scripts de instalación, bases de datos, aplicaciones de escritorio o Host.

### Rescate único de proveedores

Se ha generado F:\AUTOFABRICADOR-RESCATE\AUTOFABRICADOR-0.8.0-PRIVATE-VENDOR.zip, con el modelo, llama.cpp, Aider/Codex/OpenCode, compiladores, runtimes WASI, NuGet/componentize-dotnet, Playwright y la caché externa WASI de usuario. Cada archivo original tiene SHA-256. El ZIP de código NO replica esos gigabytes.

    python autofabricador.py offline-vendor-inspect
    python autofabricador.py offline-vendor-verify

La prueba de restauración física a un área temporal nueva y su recibo están en CONTINUIDAD\R036. Los paquetes del sistema Windows, Python 3.12, Node 24, SDK .NET 10.0.401 y Chrome no están incluidos: no declarar instalación completamente offline en un ordenador limpio aunque todos los proveedores privados se recuperen.

El código original, los logs probatorios, las entradas UNKNOWN, los LKG y los hashes se conservan. La limpieza solo elimina residuos regenerables propios, no modelos, caches útiles ni herramientas. Ninguna instalación Host/BOOT/PROD/CURRENT/ROOT de MMC7/MMC5.5 ha sido cambiada.

Reanudar: C:\AUTOFABRICADOR\CONTINUIDAD\R036\LEEME-PRIMERO.txt; contrastar checkpoint del chat, checkpoint del proyecto, manifest SHA y estados VIVOS de originales. Transcript FULL no está disponible.

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


## R043 / 0.9.4 - Windows Sandbox native demonstrator

Esta revision corrige el fallo original de Expand-Archive ausente en el invitado y
el problema de ExitCode no disponible con Start-Process: el invitado usa .NET
Process y drena stdout/stderr, con plazo por paso y tope de salida persistida.

En el Windows 11 Pro del propietario, la caracteristica de Windows Sandbox
fue habilitada por el usuario. Trabajo nativo SX-241b669dba4c4cc6:
cinco pasos de demostracion reportaron salida 0 y se correlacionaron con
hashes del propietario, journal y proceso original de Windows. El reporte
del invitado sigue siendo NO CONFIABLE; no hay atestacion criptografica ni
aceptacion independiente universal de software nativo.

AUTOFABRICADOR permanece como candidato portatil NO ACTIVE. No se instala
servicio Windows ni se modifica MMC7 o MMC5.5 por esta revision. Las
pruebas de Host, restauracion fisica y copias C+D se conservan por SHA.
Los intentos fallidos anteriores no se repiten ni se borran.
Relevo actual: CONTINUIDAD/R043-NATIVE-MANAGED-PROCESS-20261107.

## R044 / 0.9.5: verified model repo -> real Windows Sandbox

An original local-model generated ESM project must first pass owner-pinned WASI
tests in the original repo job. repo-native-stage RJ-ID verifies all original
model/source/compiler/owner receipts and bundles the same accepted JavaScript,
a SHA-pinned locally signed Node executable, and the immutable owner cases
into an input archive for a genuine Windows Sandbox VM. There is no execution
of model-authored JS on the Windows host. Source runtime Node 24.20.0 is copied
from the authenticated host only, and is NOT part of the portable release.
Then use sandbox-launch SX-ID and repo-native-verify SX-ID. The VM
runs owner cases in Node inside the disposable VM. Outputs are UNTRUSTED,
so the native result corroborates the already independent WASI acceptance
rather than replacing it. No Windows service or universal native project runner
is installed. Never blindly replay launch intents or model jobs.


## R045 / 0.9.6 bounded persistent native cycle
native-cycle-create RJ-ID pins an already independently owner-WASI-accepted
repo into a new NC-ID (one intent only). Queue via supervisor-queue native
--ref NC-ID, then supervisor-start. The original persistent supervisor worker
executes native-cycle-run through its exact first-party CLI, not a new factory.
Manual native-cycle-run NC-ID is the single-command synchronous equivalent.
STOP is durable and forwarded to the original guest's STOP.REQUEST at a
safe boundary. UNKNOWN, STOPPED and SUCCEEDED are never blindly replayed.
The VM guest's readable results only correlate with original WASI owner QA;
the original authenticated native owner and universal software are NOT proved.
Native Windows runtime is a separately pinned SHA copied ONLY into Sandbox.
No Windows service, ROOT/PROD changes, or privileged Host install here.


## R046 / 0.9.7 - single owner intent through model, WASI and native Sandbox

Use factory-submit examples/owner.json once. It validates a SHA-pinned owner
functional specification, creates FC-ID, enqueues original supervisor SQ-ID
and starts the persistent worker. The original first-party pipeline generates
a fresh repo with local Qwen 1.5B (max three separately receipted attempts),
requires original owner acceptance under WASI, then creates one original
NC-ID and launches isolated Windows Sandbox, checking owner cases there.
Every cross-stage reference is stored by SHA and CAS; STOP propagates to
the current original child. UNKNOWN is terminal for replay, not auto-retried.
Native guest output is UNTRUSTED and does not confer cryptographic owner
attestation. This supports bounded ESM projects with original user-provided
acceptance cases; it is not unrestricted native app installation or a service.
No privileged Windows/ROOT/MCC5.5/MMC7 changes.


## R047 / 0.9.8 - guarded Spanish and English owner intent catalog
One original command factory-request 'crea una calculadora de descuentos'
normalizes a CLOSED, audited natural-language alias to one of three
supported two-module ESM tasks (discounts, invoice totals, text cleanup).
A first-party deterministic Python owner acceptance matrix of 16 cases is
frozen and SHA verified BEFORE any model inference. The original first-party
factory_pipeline and persistent supervisor generate/correct the code, check
original independent WASI owner criteria, and execute the accepted source
inside real Windows Sandbox, subject to guest readback trust limitations.
Unlisted natural-language requirements are REJECTED, never interpreted
speculatively. This is not arbitrary natural-language-to-application AI.
Repeated requests are readback-only. UNKNOWN requires journal/lease
reconciliation rather than replay. Use factory-request-preview for a
side-effect-free analysis and factory-request-status for live readback.
No protected Host service installation or universal owner attestation.


## R047 Portable output from original owner-accepted projects
The original factory_pipeline generates an immutable static program ZIP
after successfully completing model + independent owner WASI + genuine
native Sandbox readback. The source ZIP contains trusted first-party
HTML/CSS/controller templates, original accepted compiled logic.js, both
model-generated source files, package.json with NO npm lifecycle scripts,
fixed owner cases, README, and SHA manifest. It runs NO untrusted model
code on the Host while packaging. The browser UI was NOT Chrome-tested
in this exported ZIP; guest output remains untrusted. A failed artifact
build is separately marked UNKNOWN without replaying the accepted model
job. Use factory-deliver-verify FC-ID for original SHA readback.


## R048 / 0.9.9 - genuine Windows SCM rehearsal ONLY within ephemeral guest

Native first-party C# ServiceBase sample (AFR048GuestProbe) is compiled from
qa/service_r048/AFR048GuestService.cs with the Windows .NET Framework compiler.
Its executable SHA is pinned before Windows Sandbox staging.
Original guest job SX-55a5a75a57944cdb reported six lifecycle phases:
service create, start, stop, restart, stop and final deletion; child worker
process identity checked and terminated on both stops. The separate first-
party verifier correlates staged input SHA, original guest nonce and source,
guest lifecycle output, diagnostic trace and receipt SHA but NEVER treats
guest bytes as independent signed owner acceptance. A first diagnostic
guest job and a second guest job timed out at 90s; both were reconciled and
their exact original Windows Sandbox VM processes closed. Final bounded
script succeeded without replaying either original job.

The SCM test is a FIRST-PARTY TEST SERVICE ONLY, not an installed or ACTIVE
AUTOFABRICADOR service. No Windows Host service was created or changed.
service-guest-verify SX-ID is read-only. Host installation M4-M6 still needs:
a real service wrapper for original Python supervisor worker, original signed
Host operationId/planSha/scope authorization, a rehearsed restorable full
Host preimage, install/readback/restart/STOP/uninstall and signed final
owner acceptance. No permission can be inferred from this guest rehearsal.


## R049 / 0.9.10 - real Windows ServiceBase adapter for ORIGINAL supervisor

The C# first-party Windows ServiceBase binary AFOriginalSupervisorService.exe
runs the authentic 'autofabricador.py service-worker' process, not a new
factory or dummy child. service-worker checks the original supervisor live
lease, control STOP and empty original queue, transitions the original STOP
to RUN through the original CAS/journal helper, then calls the ORIGINAL
supervisor.worker(root) unchanged. The service checks the Python, CLI and
service_worker.py SHA pins, validates its child PID against the ORIGINAL
live lease, and when stopped runs ORIGINAL supervisor-stop and checks that
original child exited and original lease/control read back STOPPED.

The sample service's executable enforces mode GUEST_ONLY and exact Windows
Sandbox mappings. It is NOT a Host-installed production service, and cannot
be enabled on Host by simply changing the config. The guest service rehearsal
is a distinct portable native E2E proof with original first-party Python
runtime, original queue/supervisor and real Windows SCM; output still remains
UNTRUSTED guest-generated, never original signed Windows owner acceptance.

No signed M4 Host authorization, original full OS restore point with tested
rollback or original production service installer is supplied. Never install
an unverified candidate or represent it as ACTIVE. The R048 first-party test
probe and all older LKG binaries remain preserved.


## R051 / 0.9.11 - integrated real-capability testing, independent of MMC

First-party source guard rejects Node process.exit/process.env and related
process members including bracket and optional chaining syntax. The original
WASI/no-Host-code and Windows Sandbox isolation remain mandatory; a static
filter alone does NOT certify arbitrary untrusted programs.

The actual original repo model-worker feedback now identifies bounded
failures using independently fixed owner acceptance input/expected/got
examples. This fixes the previous problem of only showing failed indices to
a local AI. It does NOT imply the local 1.5B model will correct every bug:
R051 new IPv4 TypeScript (47 owner cases) failed 34/47 after three distinct
model attempts; R051 JavaScript duration formatter (42 independent cases)
failed, though the second pass improved from 7/42 to 19/42. All original
failed projects remain rejected, and no failed source was installed.

Original supervisor successfully ran a NEW independent JavaScript code
project via its own repo queue, with original AI, WASI owner acceptance
44/44 at first attempt and safe STOP/lease readback. This is the real
original supervisor process (not an installed Windows service). A Python
temperature-band mission with original independent owner tests was also
run for model feedback measurement; see R051 continuation for original
result and limitations.

The earlier R049 Windows Sandbox service rehearsal was guest-only and did
not include a real-model job under an installed Windows Host service.
AUTOFABRICADOR is an independent product and requires no MMC component.
R051 remains CANDIDATE_NOT_ACTIVE until independent installation and
end-to-end owner attestation are proved. Do not replay original failed,
succeeded or unknown jobs. Previous 0.9.10 LKG remains untouched.


## R052 / 0.9.12 - genuine C# and bounded local-model failures

AUTOFABRICADOR remains independent of all MMC products, Hosts and tunnels.
Original local Codex CLI generated a NEW two-module C# library for distinct
positive integers, with 21/21 independent cases in original C# AOT WASI02.
The original source ZIP/owner receipts are archived in C:/AUTOFABRICADOR/DIST
and D:/AUTOFABRICADOR-RESCATE. That is a source-only artifact, not a
preinstalled Windows service or standalone .NET executable.

The original repo model loop now detects when TWO consecutive first-party
owner tests report the exact same failure pattern. It stops BEFORE a third
ineffective inference with STAGNATED_OWNER_NO_PROGRESS, preserving all intent
and test receipts. Do not replay old R051 failures or past SUCCEEDED jobs.

Python model source-generation default max_output_tokens is now 1900 for
NEW jobs (preimage of the original settings retained). Explicit
finish_reason=length produces FAILED_MODEL_OUTPUT_TRUNCATED in deterministic
unit tests, not fake PASS; however the REAL Python job
AF-78d5cb5776ac47a7 still ended UNKNOWN with provider output truncated,
so that real-world path is NOT declared fixed or accepted. The prior R051
Python job AF-d2afd9e87abd4ba9 is also UNKNOWN, untouched. NEVER replay
uncertain original model intents.

The 14B pinned local model is guarded by measured available physical memory
and will fail closed before model scan/lease/spawn if the OS has inadequate
headroom. Its existing original earlier 12-case acceptance remains preserved;
R052 did not re-run a 9 GB local model with only about 7 GB RAM available.

R051 real original supervisor JS 44/44 and Windows native Sandbox guest
readback remain preserved and accepted only within their tested boundaries.
R052 original source tests and physical independent D restore validate release
reproducibility. No model-authored code executes on Host.

M4/5/6: Windows Host service installation, rehearsed system rollback, startup
recovery and arbitrary-spec universal acceptance remain UNPROVEN. R052
CANDIDATE_NOT_ACTIVE, not ACTIVE; no MMC authority required. No F drive.


## R053 / 0.9.13 - adversarial MEGATEST and SHA-chained BLACKBOX

AUTOFABRICADOR remains fully independent of all MMC products. First-party
autofabricador.py blackbox-create examples/YOUR_FIRST_PARTY_PLAN.json
freezes explicit case contract and SHA before effects; the owner harness
calls autofab.blackbox.record with original receipts during execution.
Use blackbox-verify BB-... and blackbox-report BB-... for integrity and
bounded test outcomes. BLACKBOX does not execute model code or authorize
Windows service installation; it records original source paths, SHA, elapsed
time and measured physical RAM, not passwords or raw model prompts.

R053 controlled first-party adversarial matrix ran 2,812 negative / positive
deterministic checks with no failures AFTER fixing 2 optional-chaining
process API bypasses and 8 Windows path validation gaps, all with original
preimages and SHA. This does NOT prove arbitrary JS sandbox security; the
original no-network/no-filesystem WASI isolation is the boundary.

R053 novel original real-model challenges were deliberately hard:
JS 78 cases initially 0 EXECUTED because trusted Javy owner harness could
not compile a JavaScript string containing NUL; its independent source was
rejected. The harness has been fixed to transport original frozen JSON
owner cases as ASCII base64 and decode in WASI. Original 8 NUL+Unicode
cases then passed in actual Javy+Wasmtime. A NEW distinct JS job executed
79 real owner cases and the small model produced 21/79, rejected. These
original model failures remain immutable, not promoted.

TS three-module port validation failed first 36/76 repeated twice;
the original R052 stagnation guard triggered after two matching owner
receipts and safely skipped a third ineffective inference. A NEW TS goal
clarifying the invalid -1 sentinel passed independent 77/77 owner WASI
tests with original one model call. Compiled model code was also run in
REAL Windows Sandbox guest with 77/77 correlated readback and guest VM
closed; guest output is explicitly UNTRUSTED, not independent attestation.
Browser export was attempted but left only original APP_INTENT; no app ZIP
is claimed or installation accepted from that attempted workflow.

Python Codex CLI produced source with a literal string.replace regex
mistake; all 8 frozen owner test groups failed. A NEW repair operation
using the original failed source as SHA-pinned seed still failed; original
Python source never passed owner. Historical Python provider UNKNOWN jobs
remain quarantined (truncated output), never blind replayed.

C:/AUTOFABRICADOR/CONTINUIDAD/R053-MEGATEST-BLACKBOX-20261107
contains objective, original black-box session, errors, source preimages,
case receipts, SHA journals, diagnosis and recovery.
M4/M5/M6 are NOT ACTIVE: no protected Windows Host service, original OS
preimage with rehearsed rollback and full restart E2E. No MMC Host or
tunnel required; F drive forbidden. 0.9.13 is CANDIDATE_NOT_ACTIVE.


## R054 / 0.9.14 - autonomous bounded self-audit with independent owner evidence

AUTOFABRICADOR is wholly independent of MMC. The read-only
command: autofabricador.py audit-inventory
inspects original job states, SHA of original blackbox receipts, local
model, supervisor, measured RAM, pinned compiler, real Windows service
visibility, and known unresolved blockers. It NEVER claims a model-generated
score as a first-party functional acceptance result.

The command: autofabricador.py audit-create examples/self_audit_ts_r054.json
freezes original owner SHA, failed independent test receipts, maximum model
calls, a STOP control and a NEW SHA-chained blackbox BEFORE any AI call.
Then: autofabricador.py audit-run SA-...
One local pinned AI model diagnoses independent owner failures with a
separate complete original SSE stream receipt; it produces an untrusted
JSON repair goal. A distinct repo_factory job is created with the SAME
frozen owner tests, files and dependencies. The original code generator
may repair its own JS/TS candidate code in isolated no-network/no-filesystem
WASI, NOT the Host. If accepted, an optional independent Windows Sandbox
guest is correlated but marked UNTRUSTED. The system cannot change source
control-plane/trust/owner tests or install a Windows service.

The cycle stops on PASS, bounded budget, STOP, stagnation, invalid output,
uncertain original child or unsafe precondition; it does not infinitely
loop, blindly replay UNKNOWN or falsely claim universal correctness.
audit-status, audit-stop, audit-verify allow original evidence readback.
Python, browser exporter and Host installation currently remain classified
as uncovered/blocked: require new first-party owner-backed implementations.
0.9.14 remains CANDIDATE_NOT_ACTIVE. No MMC and no F drive.
Recovery evidence: C:/AUTOFABRICADOR/CONTINUIDAD/R054-AUTONOMOUS-AUDIT-20261107.


## R055 / 0.9.15 - ORIGINAL WASI owner-driven hybrid self-healing and web delivery

AUTOFABRICADOR remains a separate product; no MMC, MMC Host or F drive.

An original local model may incorrectly produce TypeScript three-module port
source or Python ASCII slug code. Trusted repair_bridge.py implements only TWO
narrow and SHA-pinned FIRST-PARTY transformations, with original model source,
original owner test bytes and original failure state anchored before effects.
The first-party TS bridge repairs numeric -1 -> text 'invalid' in entry module
only, retaining underlying module graph. The Python bridge replaces an exact
literal string.replace regex misuse with standard-library re.sub, and corrects
non-string behavior. The repaired source executes ONLY in first-party WASI with
no Host/network/tools; original tested owners are immutable. These are NOT
pure local-model successes or arbitrary language support.

Commands: repair-create SOURCE_JOB [--revision v2], repair-run AR-... and
repair-verify AR-.... Existing attempts are never replayed. Revisions create
distinct explicit original intents and preserve old UNKNOWN/rejected receipts.

The existing audit-run SA-... now automatically considers a trusted hybrid
repair after a real model-generated source fails ORIGINAL WASI acceptance.
A successful hybrid reports PASS_SCOPED_OWNER_TRUSTED_HYBRID (different from
pure model owner acceptance) and preserves the failed original source result.
To avoid stalled duplicate inference, original identical repository specs
are detected before any repeated local-model effect and safely terminalized.
The first-party owner invariant clarifies string-return sentinel/port
semantics without changing or weakening original acceptance cases.

The browser repo exporter returns an explicit readback-only
ORIGINAL_EXPORT_INCOMPLETE_INTENT_NO_REPLAY when a prior APP_INTENT has no
archive+original browser receipt; it NEVER repeats an uncertain old Chrome
execution. A NEW original 16-case offline browser export validates the
normal path and produces a SHA-checked ZIP with original Chrome receipt.
A previous 77-case incomplete APP_INTENT stays incomplete, not miscounted.

Self-repair is bounded and supported only for exact recognized patterns.
Python direct Codex model provider UNKNOWN truncation, general JS logic,
arbitrary project types, protected Windows Host OS restoration and SCM
installation remain open. M4/M5/M6 are NOT ACTIVE. All original data and
previous LKG versions remain preserved. Recovery is under
C:/AUTOFABRICADOR/CONTINUIDAD/R055-HYBRID-REPAIR-PYTHON-WEB-20261107
with physical D:/AUTOFABRICADOR-RESCATE packages and SHA/CAS readback.


## R056 / 0.9.16 - direct local Python SSE owner and safe STOP

Independent AUTOFABRICADOR, not MMC. NEW python-create first-party JSON
intent accepts only two previously frozen Python slug source failures
and original SHA-pinned 8 unittest owner groups. python-run submits ONE
new request to original pinned localhost llama.cpp using direct_agent SSE
transport, compact JSON source-only response, no Codex or cloud calls.

SSE receipt stores actual last finish_reason. HTTP [DONE] with reason
length, a missing DONE, thread uncertainty or STOP is never treated as a
complete model success. Historical UNKNOWN model effects are not replayed.
Model source is parsed as data on Host and executed only in first-party
Wasmtime Python guest with zero Host filesystem, network and tool grants.
Frozen owner tests are run independently inside the guest. If the code
fails with one of the two exactly recognized literal str.replace mistakes,
trusted first-party repair_bridge may correct it; now permits precisely
one unused import re and rejects all other arbitrary imports or code.
This follows a DIFFERENT independently verified source path; pure AI
success and trusted hybrid success are never conflated.

Actual original first Python SSE job PD-b09eaf3ecfbf47e4 returned a
normal complete model stream but FAILED all 8 owner groups. A separate
new original second Python SSE job PD-ca7673e34b6747a7 completed owner
8/8 using a trusted hybrid repair after the local model failed. Original
recorded blackboxes BB-dd4e9fc0f66f48a6 and BB-0457a1e3ee614b66
keep source, complete original stream and owner receipts in the project.

CLI: python-create, python-run, python-stop, python-status, python-verify.
STOP is valid before the original model intent and during direct SSE
stream; own socket shutdown and thread/idle status are verified.
No terminal or UNKNOWN job is replayed. No arbitrary Python agent
approval, no original owner test editing, no code execution on Host.
Older original web APP_INTENT without ZIP stays SUSPENDED/INCOMPLETE
with readback no replay; R055 new browser export passed 16/16.

R056 0.9.16 SOURCE ONLY CANDIDATE_NOT_ACTIVE. Native Windows SCM service
remains BLOCKED until original authenticated operationId+planSha,
complete OS-restorable preimage, rehearsed rollback and real restart/AI
original owner E2E. No MMC and no F drive. Physical D source recovery
and blackbox are under CONTINUIDAD/R056-PYTHON-DIRECT-PROVIDER-20261107.


## R057 / 0.9.17 - NEW Python task families and independent owner

Independent AUTOFABRICADOR no MMC and no F. First-party 12-case
strict-positive-int collection and 14-case inclusive interval merging
owner suites were frozen BEFORE local model inference. Reference code
ran only within WASI guest and passed all 26 original tests; reference
solutions and owner tests were NEVER given to local model. Model source
is parsed as data on Windows Host but executed only in guest WASI.

Two first new model jobs finished SSE, but failed source format because
of placeholder replication and doubly escaped newlines. In two new
owner-frozen goal-only revision jobs, strict-int source executed twelve
owner groups but failed Python bool/int semantics; exact trusted
first-party type guard repair GR-d0915fb3ba9f408e PASSED 12/12 original
WASI groups. Pure model did NOT pass. The other interval model's code
executed 14 original groups but failed owner. The original complete
stream was reconciled from saved SHA without a second model call.

New original local model server PID reuse caused an old receipt filename
collision: fixed by PID + original lease SHA; old stopped receipts are
preserved. The unfinished interval model result has original journal
reconciled and terminal FAILED owner. Python_general source includes
readback-only one-shot reconciliation and safe STOP before/during SSE.
The prior R053 browser RJ-f356 original APP_INTENT is now CLOSED as
INCOMPLETE by independent original SHA receipt
EC-415a98dca999406f. Not marked Browser PASS and no original replay.
Distinct R055 original Chrome offline web export passed 16/16.

Supported CLI commands: pygen-create, pygen-run, pygen-stop,
pygen-status, pygen-verify, pygen-reconcile, pygen-repair-create,
pygen-repair-run, pygen-repair-verify, browser-close,
browser-close-status, browser-close-verify. Only two fixed original
Python task domains supported at present. Full unrestricted general
coding/autorepair is NOT proven.

0.9.17 is CANDIDATE_NOT_ACTIVE. No Windows SCM service; Host protected
installation M4/M5/M6 requires signed operationId/planSha, complete
OS restorable preimage, rehearsed rollback and original persistent
native restart/STOP+AI acceptance E2E. D source/evidence/continuity
preserved, previous 0.9.16 source LKG retained.
