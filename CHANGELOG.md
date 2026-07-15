# Historial de versiones

## 7.5.2 — 2026-07-15

- Detección específica del bloqueo de dirección IP informado por TikTok.
- Mensaje claro para cambiar entre Wi-Fi y datos móviles sin repetir intentos inútiles.
- Aclaración de que las cookies ayudan con sesiones y CAPTCHA, pero no eliminan un bloqueo directo de IP.
- Prueba de regresión para conservar esta orientación en futuras versiones.

## 7.5.1 — 2026-07-15

- Desinstalación segura accesible desde Herramientas y ajustes.
- Opción para eliminar el código conservando descargas y datos de reinstalación.
- Eliminación total protegida mediante la confirmación literal `BORRAR`.
- Limpieza del alias, `.profile` y lanzadores de a-Shell administrados por FlowMobile.
- Eliminación comprobada del lanzador `flow` de Termux sin tocar comandos ajenos.
- Borrado opcional de cookies, colas, historial, ajustes y descargas compartidas.
- Validación de rutas para impedir la eliminación de Home, Documents o la raíz.
- Tres pruebas nuevas para perfil, conservación de datos y eliminación completa.

## 7.5.0 — 2026-07-15

- Importación privada de cookies Netscape para sesiones, edad y contenido autorizado.
- Cookies aisladas en `.flowmobile/sessions` y nunca incluidas en informes o historial.
- Cancelación con `c` + Enter que conserva y protege los archivos `.part`.
- Reanudación automática al repetir el enlace o continuar una cola pausada.
- Descargas por lotes mediante varios enlaces o una playlist completa.
- Cola persistente con estados completada, pendiente, pausada y error.
- Carpetas independientes por lote dentro de `Downloads/Lotes`.
- Menú principal más corto y submenú Herramientas para reducir repintados en iOS.
- Doce pruebas nuevas para cookies, cancelación, playlists, colas y parciales protegidos.

## 7.4.2 — 2026-07-15

- Panel principal renderizado como un único fotograma de terminal en a-Shell.
- Eliminación del efecto de líneas dibujadas una por una en iPhone y iPad.
- FFmpeg y FFprobe dejan de bloquear la primera aparición del menú.
- Estado temporal «Verificando sistema» mientras termina la detección secundaria.
- La comprobación de herramientas funciona incluso con actualizaciones automáticas desactivadas.
- Pruebas para el renderizado agrupado y el arranque sin procesos multimedia.

## 7.4.1 — 2026-07-15

- El menú principal aparece inmediatamente sin esperar consultas de Internet.
- Revisión de FlowMobile y yt-dlp ejecutada de forma silenciosa en segundo plano.
- Estado visible «Revisando en segundo plano» mientras finaliza la comprobación.
- La revisión completa de Termux también continúa en segundo plano sin bloquear el panel.
- Limpieza de pantalla más ligera para reducir parpadeos y retrasos en a-Shell.
- Conteo de archivos y almacenamiento del panel realizado en una sola pasada.
- Prueba de regresión para impedir que el inicio ejecute `pkg update`.

## 7.4.0 — 2026-07-15

- Barra estable con velocidad suavizada, porcentaje y tiempo restante calculado.
- Aviso sonoro al terminar y notificación opcional en Termux con Termux:API.
- Buscador del historial por varias palabras y todos sus campos principales.
- Modo Reparar para Python, yt-dlp, EJS, FFmpeg y FFprobe sin borrar descargas.
- Limpieza segura de temporales antiguos y conversiones incompletas.
- Pruebas reales rápida y completa para cinco plataformas, cuatro calidades y dos formatos de audio.
- Validación mediante FFprobe de resolución, códecs, tamaño y preparación para compartir.
- Informes de diagnóstico privados que nunca almacenan los enlaces probados.

## 7.3.8 — 2026-07-15

- El instalador deja de abrir el menú dentro de la tubería de `curl`.
- Inicio interactivo fiable desde una ventana nueva mediante `flow`.
- Captura global de entrada cerrada para salir sin mostrar un traceback.
- Lectura segura aplicada al menú, las pausas y la entrada de enlaces.
- Prueba de regresión para `EOFError` en a-Shell.

## 7.3.7 — 2026-07-15

- Bootstrap de iOS que consulta GitHub API y evita instaladores antiguos en caché.
- Limpieza de código previo en `FlowMobile`, `FlowApp` y `FlowIOS`.
- Conservación y unión segura de descargas, historial y ajustes existentes.
- Eliminación de lanzadores y aliases heredados antes de registrar los nuevos.
- Inicio automático de FlowMobile después de una instalación correcta.
- Pruebas para la limpieza de instalaciones y el nuevo bootstrap estable.

## 7.3.6 — 2026-07-15

- Orden pública de a-Shell sin operadores `&&` incompatibles con su intérprete.
- Activación fiable de `flow` al abrir una ventana nueva y cargar `.profile`.
- Mensaje específico si se intenta añadir `&&` al instalador Python.
- Instrucciones de instalación limpia verificadas contra el comportamiento real.

## 7.3.5 — 2026-07-15

- Instalación limpia de iOS que recarga `.profile` en la misma orden pública.
- Comando `flow` disponible inmediatamente sin cerrar y volver a abrir a-Shell.
- Eliminación del lanzador sin extensión que ios_system no reconocía.
- Lanzador auxiliar guardado correctamente como `flow.py`.
- Mensajes de instalación específicos para el comportamiento real de a-Shell.

## 7.3.4 — 2026-07-15

- Limpieza automática de aliases `flow` que todavía apuntaban a `FlowApp`.
- Registro persistente del alias correcto hacia `FlowMobile/main.py`.
- Aviso para descargar el alias antiguo que siga activo en la ventana actual.
- Prueba de regresión para impedir que reaparezca la ruta heredada.

## 7.3.3 — 2026-07-15

- Instalador de a-Shell reescrito en Python para no depender de `sh`/`dash`.
- Lanzador `flow` de iOS ejecutado como script Python reconocido por ios_system.
- Actualizaciones de FlowMobile en a-Shell sin iniciar un proceso shell aislado.
- Diagnóstico de a-Shell ejecutado directamente con Python.
- Conservación de descargas, historial y ajustes desde el nuevo instalador.
- Pruebas específicas para el instalador y el lanzador nativos de iOS.

## 7.3.2 — 2026-07-15

- Instalador y lanzador sin dependencia del comando externo `grep`.
- Detección compatible con los comandos `python3` y `python`.
- Mensaje claro cuando se intenta usar a-Shell mini o la extensión de Atajos.
- Comprobaciones automatizadas para la compatibilidad de los instaladores.

## 7.3.1 — 2026-07-15

- `.gitignore` separado por datos privados, Python, temporales y editor.
- Protección adicional para cookies, sesiones, variables y secretos locales.
- Exclusión de carpetas locales de Codex y editores de código.
- Lista documentada de los archivos que sí deben publicarse en GitHub.
- Advertencia para retirar del índice cualquier archivo privado ya registrado.

## 7.3.0 — 2026-07-15

- Nueva sección Novedades dentro del menú principal.
- Aviso destacado cuando GitHub contiene una versión más reciente.
- Presentación de hasta cinco cambios publicados en `CHANGELOG.md`.
- La notificación permanece visible cuando la actualización se pospone.
- Las actualizaciones continúan requiriendo confirmación antes de instalarse.

## 7.2.0 — 2026-07-15

- Un único enlace de instalación para Android y iPhone/iPad.
- Detección del dispositivo con confirmación interactiva desde la terminal.
- Elección manual entre Termux y a-Shell cuando la detección no sea correcta.
- Descarga automática del instalador específico para la plataforma elegida.
- Modo `--auto` para actualizaciones e instalaciones sin preguntas.
- Limpieza automática del instalador temporal incluso cuando ocurre un error.

## 7.1.0 — 2026-07-15

- Menú principal agrupado en Descargas, Biblioteca y FlowMobile.
- Estado superior real de FFmpeg y FFprobe en lugar de mostrar siempre “listo”.
- Selector compacto que destaca la mejor calidad detectada y permite ver todas.
- Estimaciones de audio separadas del tamaño del vídeo y formatos DRM ocultos.
- Regreso directo desde la pantalla de enlace escribiendo `0`.
- Mensajes de actualización y reparación diferentes para a-Shell y Termux.
- Instalación ofrecida cuando FFmpeg falta en Termux.
- Prevención de bloqueos durante conversiones largas con FFmpeg.
- Recuperación automática en Termux si Android pierde el acceso compartido.
- Validación más segura de rutas descargadas y ajustes booleanos.

## 7.0.0 — 2026-07-15

- El proyecto pasa a llamarse FlowMobile.
- Compatibilidad oficial con a-Shell en iOS y Termux en Android.
- Detección automática de plataforma.
- Instaladores separados y un enlace de instalación común.
- Comando `flow` disponible en ambas plataformas.
- Descargas públicas de Android separadas del código privado.
- Compartir y reproducir mediante las herramientas nativas de cada sistema.
- Estado privado `.flowmobile` con migración de ajustes e historial anteriores.
- Comprobación de actualizaciones de FFmpeg mediante paquetes de Termux.
- Dependencias de yt-dlp adaptadas a cada entorno.

## 6.6.0 — 2026-07-15

- La aplicación adopta el nombre FlowIOS.
- Instalador de GitHub preparado para a-Shell.
- Nuevo comando global `flow` dentro de `Documents/bin`.
- Conservación de descargas y ajustes durante reinstalaciones.
- Verificación de FlowIOS y yt-dlp en cada inicio.
- Confirmación obligatoria antes de instalar actualizaciones.
- Verificación de disponibilidad de FFmpeg y FFprobe.
- Archivo `VERSION` para comprobar publicaciones remotas.
- Guía de publicación y enlace de instalación preparados.

## 6.5.0 iOS — 2026-07-14

- Nueva paleta visual con colores semánticos e iconos consistentes.
- Panel principal con espacio libre, videos, audios y última descarga.
- Estado conjunto de yt-dlp, FFmpeg y FFprobe.
- Actualización automática diaria de yt-dlp mediante pip.
- Actualización conjunta de los scripts EJS requeridos por yt-dlp y YouTube.
- Control para activar o desactivar actualizaciones automáticas.
- Registro del resultado de la última comprobación.
- FFmpeg y FFprobe identificados como herramientas gestionadas por a-Shell.

## 6.4.0 iOS — 2026-07-14

- Ajustes persistentes de formato, calidad de video y formato de audio.
- Selección oficial de la mejor fuente de video y audio mediante yt-dlp.
- Límites de resolución correctos para videos horizontales y verticales.
- Lista de calidades detectadas antes de descargar.
- Verificación con FFprobe de resolución, FPS y códec del archivo final.
- Mensajes específicos para restricciones, enlaces y errores de cada plataforma.

## 6.3.0 iOS — 2026-07-14

- Menú principal más claro, validado y adaptado a a-Shell.
- Opción de solo audio destacada como primera alternativa.
- Extracción de audio real a M4A o MP3 mediante FFmpeg.
- Detección de FFmpeg compatible con los comandos internos de a-Shell.
- Conservación del archivo original cuando una conversión falla.
- Opción final para compartir o guardar videos y audios desde iOS.
- Vista de archivos recientes y estado de herramientas.
- Escritura segura del historial y protección de datos privados.
- Mejor validación de enlaces, plataformas, tamaños y duraciones.
- Pruebas básicas para dominio y conversión de audio.

## 6.2 iOS

- Versión base de Flow Media para iOS.
