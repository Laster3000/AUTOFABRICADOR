# La Luz de Bruma R91B: aventura HD panorámica jugable

Estado: CANDIDATE (sin promoción a ACTIVE). Conservar R90C intacto.
Este paquete portátil para Windows incluye el Godot oficial 4.6.3; no instala
servicios, privilegios o controladores, ni se inicia con Windows.

## Qué mejora frente a R90C
- Escenarios 640x260 nativos y una interfaz 640x100: composición HD 640x360
  y ventana 1280x720, con relación 16:9 y pixel art sin deformación.
- Personajes con 14 fotogramas, 48x96 píxeles por fotograma, detalles añadidos
  y sombra suave; escala según profundidad con pies anclados al suelo.
- Zonas caminables diferenciadas por habitación, A* real, obstáculos y bloqueo
  del punto ocupado por el anciano. Los clics en cielo, mar, bordes o paredes
  se proyectan al suelo seguro más cercano y nunca desplazan la figura fuera.
- El anciano se dibuja delante o detrás del jugador según sus pies.
- Cada recurso tiene hojas OpenRaster editables por capa (6–7 capas) y origen
  reproducible. Los 22 PNG/ORA se generan dos veces con SHA-256 idénticos.
- Correcciones de información de objetos, límite de textos, F1 ayuda,
  F5 guardar, F9 recuperar, R reiniciar al terminar.

## Cómo jugar
1. Extraer todo el ZIP en una carpeta normal.
2. Ejecutar JUGAR-R91.cmd en la RAÍZ. El primer inicio realiza la importación
   de los PNG con Godot si falta la caché; los siguientes inicios son directos.
3. Elegir IR / MIRAR / COGER / USAR / HABLAR y pulsar en un objeto, o usar
   teclas 1–5. Para usar objetos, selecciónalos primero en el inventario.
4. Seguir la pista del anciano de barba blanca, recoger lente y brújula,
   reparar el mecanismo, visitar el observatorio y encender el faro.
5. F1 abre ayuda, F5 guarda, F9 recupera, ESC cierra diálogo.
   Tras el final, R vuelve a empezar sin borrar tu partida guardada.

## Reconstrucción y seguridad
El juego no necesita Python ni Pillow para funcionar.
Para reconstruir el arte, instalar Pillow 12 en un entorno independiente
y ejecutar: python ci_verify_art.py, que reconstruye dos veces los 22
archivos desde art/base_r90 y valida su identidad con SHA-256.
Para comprobar todos los walkboxes sin arrancar Godot:
python qa/adventure_navigation_r91.py audit .
La navegación es reusable, y en AUTOFABRICADOR:
python autofabricador.py adventure-nav-audit RUTA_PROYECTO.
PROBAR-R91.cmd ejecuta el test de Godot sin abrir ventana.

## Límites reales
Éste es un juego original de tres habitaciones construido con un adaptador
Godot propio, no una aplicación entera generada de manera autónoma por IA.
Popochiu no es dependencia de ejecución. Pixelorama export automático y
calidad ilustrativa profesional requieren validación adicional. La IA local
participó previamente con texto narrativo del observatorio, no dibujó
autónomamente todo este juego. Faltan prueba física independiente en otro
ordenador y aceptación humana del arte.
