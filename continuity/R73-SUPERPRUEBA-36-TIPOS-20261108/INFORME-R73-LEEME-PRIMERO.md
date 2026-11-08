# AUTOFABRICADOR R73 - superprueba de capacidades

**Estado: DIAGNOSTICO COMPLETADO, FABRICA GENERAL NO ACEPTADA.**

El laboratorio contiene 36 pruebas originales de admision de contratos, NO 36 aplicaciones terminadas. Ademas se intentaron tres encargos nuevos de programacion JS/WASI con 43 casos independientes, y un control de lenguaje natural con 34 casos. Un PASS de admision nunca se contabiliza como software construido.

## Matriz por familia

| Familia | Contratos admitidos | Parciales | Rechazados | Desconocidos |
|---|---:|---:|---:|---:|
| console_utilities | 1 | 0 | 2 | 0 |
| python_data | 1 | 0 | 2 | 0 |
| web_frontend | 0 | 1 | 2 | 0 |
| web_backend | 0 | 0 | 3 | 0 |
| windows_desktop | 1 | 0 | 1 | 1 |
| erp_business | 1 | 1 | 1 | 0 |
| database_systems | 1 | 0 | 2 | 0 |
| games_2d | 0 | 1 | 2 | 0 |
| games_3d | 0 | 1 | 2 | 0 |
| android_mobile | 0 | 0 | 3 | 0 |
| collaboration | 0 | 1 | 2 | 0 |
| ai_integrated | 1 | 0 | 2 | 0 |

## Fabricaciones reales con IA local

| Encargo | Cola | Codigo original | Intentos modelo | E2E aprobado |
|---|---|---|---:|---|
| new-shipping | UNKNOWN | STAGNATED_OWNER_NO_PROGRESS | 2 | False |
| new-reorder | UNKNOWN | FAILED_OWNER_ACCEPTANCE | 3 | False |
| new-normalizer | UNKNOWN | FAILED_OWNER_ACCEPTANCE | 3 | False |
| positive-triple | SUCCEEDED | PASS | 1 | True |

## Hallazgos y reparaciones

1. **P0 - GENERAL-OWNER-ORACLES**: 24 of 36 full app requests rejected at first-party intake; static recipes are closed. **Corregir**: Independent requirement+test synthesis for unseen app families, owner approval, bounded capabilities and contract-specific sandbox before generation.
2. **P0 - UNSEEN-JS-GENERALIZATION**: Three new ESM two-module owner jobs did not meet independent acceptance. **Corregir**: Improve model decomposition, syntax-aware ESM feedback and model escalation; replay requires NEW operation after root-cause revision, never UNKNOWN old queue.
3. **P0 - REPEATED-BAD-CODE-ADAPTATION**: Repeated disallowed mathjs import; repeated failing business rule cases; source stagnation. **Corregir**: Structured deterministic error attribution and package allowlist enforcement before prompt; store failed strategy fingerprint to prevent repeats.
4. **P1 - NEGATION-PARSER-GUI**: Inventory GUI rejects request containing 'sin Internet' with GUI_GOAL_UNSUPPORTED_PROTECTED_SCOPE. **Corregir**: Normalize semantic negation and distinguish 'sin internet' from requests for internet; add first-party regression cases.
5. **P1 - NATIVE-APPLICATION-FRAMEWORKS**: No accepted contract for Android build, 2D/3D engine, real-time server, distributed services. **Corregir**: Isolated pinned toolchains, runtime-specific E2E UI/physics/network owner oracles and portable package contracts.
6. **P1 - APP-UI-QUALITY-COVERAGE**: Current accepted GUI app is profile-limited inventory; not evidence of general UI or 3D physics. **Corregir**: Black-box visual geometry, event interaction, collision, localization and persistence tests per new app family.
7. **P2 - PHYSICAL-PORTABILITY**: Historical R72 passes two Windows Sandbox guests on same PC, not other physical PC. **Corregir**: Independent offline Windows machine, signed input SHA, isolated receipt and source/zip restoration test.
8. **P2 - MODEL-BUDGET-PROTECTION**: Current 16GB RAM machine works near CUDA memory thresholds; avoid parallel GPU VMs. **Corregir**: Per-family RAM/VRAM measured quota, sequential supervisor and reuse accepted SHA without model rerun.

## Evidencias

- Caja negra contractual: BB-49065b886e0548d0, 36 / 36 registrado, 34 coincidencias con contrato congelado.
- Caja negra E2E: BB-275f58c1026d45af, 1 de 4 criterios de entrega.
- Regresion original: 473 pruebas, 25 omitidas, estado PASS.
- R72 historico: 13/13 en dos invitados Windows Sandbox, ZIP SHA 9151f3c5c6ad79103e9ed6baa84e4ff8e517f22760007e42d8060759ca10497e.
- Estado operativo final: supervisor STOP, modelos locales STOP, Sandbox sin sesiones, arranque Windows deshabilitado.
- No hay segundo Windows fisico verificado ni prueba de fabrica universal.

## NEXT_ACTION

First fix P0 code generation on new bounded ESM tasks using held-out owner cases; then expand first-party contract+isolated toolchains by family (web full-stack, desktop, game2D/3D, Android, AI). Only run new original operations after SHA-pinned code revision; keep old UNKNOWN. Re-run R73 matrix and true cross-device portable factory acceptance before promoting product.
