# LA LUZ DE BRUMA — R90C PANORAMICA 16:9
CANDIDATE (NO ACTIVE). Aventura grafica original Godot 4.6.3, 320x180 pixeles lógicos,
presentación 640x360 16:9. Tres escenarios: Puerto, Taller y Observatorio.
11 ilustraciones y hojas de sprites con 4-5 capas OpenRaster editables por separado.
14 fotogramas en cada personaje; caminar y hablar disponen de animaciones diferenciadas.
La narrativa del observatorio se generó mediante IA local GPU 7B, con validación
independiente del contrato JSON. NO significa que la IA construyera sola todo el juego.

## JUGAR
Extraer el paquete. Ejecutar el archivo INICIAR-JUEGO.cmd de la RAIZ DEL ZIP.
La carpeta tools contiene Godot oficial verificado por SHA, no requiere instalador.
Usar ratón, botones IR MIRAR COGER USAR HABLAR, inventario inferior.
F5 guardar, F9 recuperar. Hablar con el guardafaro, recoger lente y brújula,
reparar la maquinaria, consultar el telescopio y encender el faro.
No hay dependencia de red ni servicios al arrancar el juego.

## FUENTES Y AUTORÍA
El videojuego corre con adaptador Godot Node2D propio. Popochiu es un plugin opcional
de desarrollo (no se distribuye en el juego). Las fuentes OpenRaster pueden editarse
por componentes usando programas compatibles. Las ilustraciones se diseñaron con
generador determinista propio en art/r90_illustrate.py; requiere Pillow 12 SOLO
si se quieren reconstruir los recursos. Ejecutar ci_verify_art.py desde una
instalación Python con Pillow ya instalada. Los PNG y ORA originales incluidos en
el paquete NO requieren Pillow para jugar.
Los cuatro fotogramas de VISTA-PREVIA-R90C.png proceden realmente de Godot 4.6.3
OpenGL (RTX 3060) y no son imágenes conceptuales.

## LIMITACIONES
La calidad visual sigue pendiente de aprobación humana. No hay prueba sobre otro PC,
ni el AUTOFABRICADOR general ha demostrado fabricar cualquier app compleja de
principio a fin. R90C no se convierte en release ACTIVE.
