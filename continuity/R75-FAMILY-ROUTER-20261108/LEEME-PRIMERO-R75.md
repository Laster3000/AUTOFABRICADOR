# AUTOFABRICADOR R75 - enrutador por familias

**Resultado: PASS_BOUNDED_FOUR_FAMILIES. No es una fabrica universal instalada.**

Se han integrado ocho rutas de alcance limitado (logic, web offline y perfiles Windows acotados) y cinco denegaciones explicitas que no producen falsa aceptacion. Se mantienen los originales R74 y sus recibos.

## Matriz de las cuatro familias logicas (NO aplicaciones completas)

| Perfil acotado | Orden original | WASI + Chromium | Owner original | ZIP restaurado |
|---|---|---|---:|---|
| game-2d-rules | OJ-71709cc324f2011c | PASS | 22 | PASS |
| game-3d-math | OJ-61336a3a27449635 | PASS | 22 | PASS |
| api-route-logic | OJ-f4e785c61e47f9ec | PASS | 24 | PASS |
| agent-decision-logic | OJ-7d7a7ca9b80af961 | PASS | 24 | PASS |

## Pruebas adicionales y controles

- Regresion portable: 495 pruebas, 24 omitidas, 0 fallidas.
- Regresion desarrollo: 478 pruebas, salida 0, conservada sin replay.
- Casos no vistos por modelo: 76 PASS.
- Canvas2D / WebGL2, prueba de motor primero propietario: PASS_CANVAS2D_AND_WEBGL2_RENDERER_READINESS (NO juego completo).
- ZIP incremental SHA verificado: e93a4ff681e28afe00434791be3ce658ec62fcaf0c696e3dd4e18b7cb511d729, NO paquete completo.

## PENDIENTES QUE NO SON PASS

- P0 web-fullstack: AI-authored isolated HTTP+database+auth server, state/persistence/concurrency oracle and full deployment.
- P0 game-2d: AI-generated renderer with assets, full collision/physics, 2D visual acceptance and interactive scene.
- P0 game-3d: WebGL3D meshes/shaders/camera, physics, render/performance and native interaction owner QA.
- P0 android: original Android SDK, JDK/Gradle, APK signing, instrumented emulator/device owner acceptance.
- P0 ai-integrated: app-level local-model service, privacy policy, error handling, streaming/token budget and reproducible owner cases.
- P1 portable-physical-device: second physical Windows PC, independent graphics/driver/runtime SHA and app restore/readback.
- P1 additional-language-toolchains: pinned Java/Android, Rust, build system, dependency isolation and standalone E2E contracts.

## Estado y accion siguiente

Build first-party isolated HTTP/persistence owner contracts and truly interactive 2D/3D renderer+physics owner E2E, and Android SDK/device plus app-level LLM provider owner. Complete each platform as separate pinned ABI/recovery package and test on physical other PC before promoting general release. Do not replay UNKNOWN or STAGNATED original R75 jobs.
