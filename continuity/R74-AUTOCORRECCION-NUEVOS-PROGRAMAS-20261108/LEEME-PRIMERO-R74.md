# AUTOFABRICADOR R74 - Reparacion de encargos nuevos

Revision acotada del motor original. No equivale a capacidad universal ni instalacion del producto completo. La raiz activa de pruebas fue C:\AF-PORTABLE para reutilizar el modelo CUDA Qwen3.5-9B Q4_K_M ya verificado, sin duplicar GGUF.

## Comparativa con R73

- R73: 0/3 encargos ineditos de codigo aceptados.
- R74: 3/3 objetivos finales con nuevas pruebas independientes aceptados.
- Primeros trabajos R74 de portes y reposicion: FAILED_MODEL_FORMAT y STOPPED, sin replay.
- R74D portes UNKNOWN con salida CTRL_C_EXIT; R74E es un contrato nuevo.
- Bateria de fuente: 473 pruebas, 24 omitidas, PASS.
- Pruebas unitarias: 9/9 PASS.
- Pruebas independientes adicionales reservadas: 54/54 PASS en WASI, sin nuevas inferencias.

## Encargos originales

| Encargo | Estado cola | Estado fabrica | Intentos modelo | Owner | ZIP restaurado |
|---|---|---|---:|---|---|
| shipment | UNKNOWN | FAILED_REPO | 3 | FAILED/UNKNOWN | No |
| reorder | STOPPED | STOPPED_SAFE_BOUNDARY | 0 | FAILED/UNKNOWN | No |
| normalize | SUCCEEDED | PASS_SCOPED_WASI_BROWSER_OFFLINE | 1 | PASS | Si |
| r74d-shipping | UNKNOWN | REPO_MODEL_WASI_INTENT | 0 | FAILED/UNKNOWN | No |
| r74d-reorder | SUCCEEDED | PASS_SCOPED_WASI_BROWSER_OFFLINE | 1 | PASS | Si |
| r74e-shipping | SUCCEEDED | PASS_SCOPED_WASI_BROWSER_OFFLINE | 1 | PASS | Si |

## Persistencia y seguridad

- Preimagenes de los dos arboles y ejercicio de restauracion de bytes en D:.
- Seis archivos fuente actualizados en ambas raices, R74/R74B/R74C, con SHA.
- Los trabajos R73 fallidos no se han repetido.
- Modelo GPU cerrado, supervisor STOP, Windows Sandbox liberado y autoinicio deshabilitado.
- Ningun codigo generado se ejecuta en Host libre; la aceptacion original usa WASI/Chromium aislado.

## PENDIENTE

Expand original first-party owner contracts and isolated toolchains for other app families. Do not replay R73 failed/UNKNOWN jobs; use independently new owner operations after source revision. Verify on a second physical Windows PC before universal promotion.
