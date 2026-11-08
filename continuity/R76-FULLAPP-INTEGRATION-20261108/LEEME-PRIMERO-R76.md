# AUTOFABRICADOR R76 - LEEME PRIMERO

**PASS para suite de referencia acotada; NO es fabrica universal activa.**

## Que se ha realizado y por que
A partir de R75 se han construido aplicaciones que integran funciones originalmente generadas
y probadas por Qwen 9B (Canvas 2D y proyeccion 3D), HTML/CSS/JS de confianza,
un servidor Python HTTP con SQLite, autenticacion y CSRF, y un endpoint opcional
autenticado con Qwen 3.5 9B, probado con respuesta REAL (sin stub).
Android se ha compilado usando .NET/JDK/SDK existentes en Visual Studio sin instalacion global.
Un trabajo original R76 de API se estanco en 28/29; se conservo inmutable y
se reparo por delta determinista con 53 casos WASI, NO como exito del job original.

## Evidencia de aceptacion
- 24/24 HTTP y 27/27 Chromium en origen
- 24/24 HTTP y 27/27 Chromium desde ZIP restaurado
- Qwen3.5 9B modelo real: PASS HTTP autenticado, modelo detenido
- C# Android MazeLogic: 29/29; APK nativo firmado de depuracion: PASS de build
- JavaScript API modelo reparado: 53/53 tests WASI
- Regresion integral en C:\AF-PORTABLE: 507 PASS (salvo skipped originales)
- Regresion integral en C:\AUTOFABRICADOR: 490 PASS (salvo skipped originales)
- Archivo ZIP de la suite: 29 archivos restaurados, SHA por bytes
- CLI original en ambas raices: r76-suite-capabilities, r76-suite-verify, r76-suite-export

## Donde esta el paquete
D:\AUTOFABRICADOR-RESCATE\R76-FULLAPP-INTEGRATION-20261108\PACKAGES\AUTOFABRICADOR-R76-REFERENCE-SUITE-CANDIDATE.zip
SHA-256: 80a1eabc202926a1690df840732899bce2f015f65b0d86efe1e82e3413c359e6
APK Debug firmado: D:\AUTOFABRICADOR-RESCATE\R76-FULLAPP-INTEGRATION-20261108\ANDROID-R76\bin\Debug\net11.0-android\com.autofabricador.r76labyrinth-Signed.apk
SHA-256 APK: ce33408272e14db655cb3137b7f568755b5dc4c59e8a109b35b9f47020e0295a

## Lo que permanece bloqueado
No emulador ni telefono Android conectado para validar instalacion y uso reales.
No segundo PC Windows fisico para comprobar portabilidad intermaquina.
La suite ZIP requiere Python y modelo Qwen/llama.cpp aparte, no es autocontenida.
La fabrica de software open-domain universal NO esta construida/aceptada.
La firma Android es de DEPURACION, no una clave de distribucion.

## Continuidad segura
Leer MANIFEST-R76.json, R76-CHAT-CHECKPOINT.json, R76-PROJECT-CHECKPOINT.json
y recibos citados; consultar Journal/Lease original en la maquina antes de nuevas operaciones.
No repetir jobs UNKNOWN, FAILED ni STAGNATED anteriores.
Version activa de AUTOFABRICADOR no cambiada; no tocar BOOT/PROD MMC/F.

## NEXT_ACTION
E2E instalar y ejecutar APK en dispositivo o emulador Android autorizado; verificar la suite y restaurar el ZIP en segundo PC Windows fisico; crear motor first-party seguro para fabricar nuevos proyectos open-domain con pruebas independientes de un servidor, juegos y apps Android, evitando afirmar completitud universal sin evidencia.
