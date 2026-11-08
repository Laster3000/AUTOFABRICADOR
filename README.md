# AUTOFABRICADOR

Proyecto experimental de **factoría local de ingeniería de software asistida por IA**. Este repositorio es **público** para compartir código, documentación y facilitar la colaboración.

## Estado real

**R76: suite integrada de referencia, no fábrica autónoma universal.** Están demostrados un servidor local HTTP/SQLite con autenticación, una experiencia Canvas 2D, una escena WebGL2, integración puntual con Qwen 3.5 9B local y la compilación de un APK Android de depuración. La compilación del APK no prueba su funcionamiento en un dispositivo.

**R77: handoff de arquitectura.** Describe los seis motores que faltan para completar el ciclo de ingeniería: interpretar y diseñar, planificar, fabricar, verificar y reparar, entregar, mantener y evolucionar.

**R79: respaldo público del código y documentación seleccionados.** No se ha promovido ningún candidato como versión activa.

## Contenido

- `development/autofab/` y `development/tests/`: fuentes y pruebas del entorno de desarrollo.
- `portable/autofab/` y `portable/tests/`: fuentes y pruebas de la copia portable, **sin runtimes**.
- `reference/R76/`: aplicación de referencia y proyecto Android en código fuente.
- `continuity/`: documentación pública de hitos y estado verificable.
- `handoff/R77/`: arquitectura integral y relevo para otra IA.
- `PUBLIC-SNAPSHOT-SHA256.json`: manifiesto de los archivos publicados.

## Recuperación y limitaciones

Este repositorio **no es una copia integral del ordenador**. Se excluyen deliberadamente los modelos GGUF, SDK y herramientas binarias, distribuciones grandes, bases de datos, registros operativos, claves, datos privados y pruebas reservadas. La instalación de dependencias compatibles y la verificación de los entornos siguen siendo necesarias.

No ejecutar automáticamente con Windows ni ejecutar código generado por modelos con privilegios de anfitrión. Mantener la compilación, las pruebas adversariales y las instalaciones dentro de los límites y entornos autorizados.

## Colaboración y licencia

Repositorio público para que pueda estudiarse el trabajo. **Aún no se ha elegido licencia**; la visibilidad pública no concede por sí sola derechos generales de redistribución o uso comercial. Será necesario decidir una licencia antes de distribuirlo como software libre.

Si se descubre información sensible, avisar al propietario por un canal privado; no publicarla en un issue.

**Importante:** un `PASS` de un componente o una demostración no equivale a la aceptación de cualquier aplicación nueva por una IA autónoma.
