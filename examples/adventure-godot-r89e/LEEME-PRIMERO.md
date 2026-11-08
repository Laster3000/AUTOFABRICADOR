# LA LUZ DE BRUMA R89 — AVENTURA PANORAMICA PORTABLE
## Ejecucion
Extraer todo el ZIP a una carpeta normal en Windows. Ejecutar INICIAR-JUEGO.cmd para abrir
la aventura desde Godot 4.6.3 oficial incluido, SIN instalar nada ni iniciar servicios.
ABRIR-EDITOR.cmd permite editar escenas y assets. Sin internet.
Resolucion logica de pixel art 320x180, presentacion 640x360, relacion 16:9.
## Gameplay
Tres escenas originales: puerto, taller y observatorio. Elegir IR, MIRAR, COGER, USAR, HABLAR
en la banda inferior y pulsar un objeto de la escena. Recoger lente y brujula, hablar con
el anciano de barba blanca, colocar ambas en la maquinaria, subir al observatorio y usar
el telescopio para descubrir la carta celeste, volver al puerto y encender el faro.
F5 para guardar, F9 para cargar. Ninguna llamada a internet ni IA durante el juego.
## Origen y límites
Los 11 PNG y 11 fuentes OpenRaster de dos capas son originales, trazables por SHA.
El archivo ai/original_narrative.json se generó con IA GPU CUDA7B y superó un contrato
estructural independiente. El motor y el pixel art se construyeron de forma determinista.
No es una fábrica universal demostrada ni un juego con arte aprobado profesionalmente.
Popochiu 2.1.1 sí funciona como editor y singleton en el proyecto de desarrollo R89,
pero este paquete evita incluir el addon y sus recursos tipográficos de licencia no
reconfirmada. El funcionamiento jugable no depende de Popochiu.
Pixelorama 1.2.2 está disponible en el ordenador de desarrollo; su exportación automática
no fue verificada. Para redibujar, abrir fuentes OpenRaster con un editor compatible.
## QA
El directorio qa contiene el TESTER INDEPENDIENTE de Godot. El juego no depende de él.
La release solo es CANDIDATE, no ACTIVE. La aceptación visual humana sigue pendiente.

## R89E reproducibilidad
Los PNG y maestros OpenRaster de las 11 entidades se generan con metadatos de ZIP congelados; dos construcciones frescas han producido archivos SHA-256 idénticos. Para regenerarlos en una carpeta NUEVA vacía: Python art/generate_assets.py y luego Python art/generate_new_art.py; el proyecto fuente mantiene un manifiesto R89E congelado para comprobar la procedencia de lo generado. No regenerar sobre una instalación existente.
