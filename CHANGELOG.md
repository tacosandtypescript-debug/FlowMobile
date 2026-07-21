# Historial de versiones

## 8.0.3 — 2026-07-17

- El enlace Linux activa `~/.local/bin` directamente en la terminal actual.
- Ya no depende de que Pop!_OS, Ubuntu u otra distribución recargue `.profile`.
- Se limpia la caché de comandos del shell antes de que el usuario ejecute `flow`.

## 8.0.2 — 2026-07-17

- El instalador Linux activa `flow` en la terminal actual desde el comando público.
- El PATH queda registrado también en Bash o Zsh para las siguientes terminales.
- La desinstalación limpia de forma segura los bloques añadidos a todos los perfiles.
- Mensaje de activación más visible cuando la terminal todavía conserva el PATH anterior.

## 8.0.1 — 2026-07-17

- Nueva identidad visual con portada e icono originales para FlowMobile.
- Portada del repositorio más clara, con insignia de la última versión estable.
- Página de instalación con marca visual, favicon y vista previa al compartir enlaces.
- Mensajes posteriores a copiar adaptados correctamente a cada plataforma.

## 8.0.0 — 2026-07-17

- Soporte nativo para ejecutar FlowMobile desde Windows Terminal y terminales Linux.
- Instaladores oficiales de un solo enlace para PowerShell y Linux, con seis etapas y salida silenciosa.
- Instalación automática de Python y FFmpeg mediante winget, apt, dnf, pacman o zypper.
- Descargas de escritorio en la carpeta personal, portapapeles nativo y apertura de archivos o ubicaciones.
- Actualizaciones con SHA-256, prueba `flow --health-check` y rollback antes de retirar la versión anterior.

## 7.6.19 — 2026-07-17

- Instalación silenciosa en seis etapas para a-Shell y Termux, sin bloques técnicos innecesarios.
- Registro privado reemplazable con la salida completa de pkg, pip, curl y Python.
- Errores con código, causa exacta, detalle original y solución específica para cada etapa.
- Un reintento automático ante fallos temporales de red y tiempos límite para evitar bloqueos.
- Modo `FLOWMOBILE_VERBOSE=1`, rollback conservado y resumen final con comando y carpetas.

## 7.6.18 — 2026-07-17

- Instalaciones y actualizaciones estables verificadas con SHA-256 antes de ejecutarse.
- Manifiesto de integridad para detectar código modificado, rutas inseguras y archivos ejecutables no registrados.
- Centro de seguridad visible con origen oficial, integridad del código y privacidad de cookies.
- Dependencias Python bloqueadas por versión y hash; acciones de GitHub fijadas a commits inmutables.
- Releases con atestación de procedencia y activos de instalación verificables para a-Shell y Termux.

## 7.6.17 — 2026-07-17

- Portada reducida y enfocada en instalar FlowMobile desde el móvil.
- Botones de Apple y Android colocados antes de la información secundaria.
- Instalación explicada en tres pasos breves y ubicaciones mostradas en una tabla.
- Detalles técnicos, privacidad y mantenimiento trasladados a una guía completa.
- Prueba automática para impedir que el README vuelva a crecer excesivamente.

## 7.6.16 — 2026-07-17

- Botones móviles iguales a los de SpaceFlow mediante una página de copia directa.
- Copia real al portapapeles con un toque y confirmación visible de «¡Copiado!».
- Selección automática de Apple o Android desde el botón pulsado en GitHub.
- Diseño adaptable, accesible y compatible con navegadores móviles antiguos.
- Páginas Markdown conservadas como respaldo si GitHub Pages no está disponible.

## 7.6.15 — 2026-07-17

- Botones visibles para abrir la instalación de iPhone/iPad o Android desde el móvil.
- Páginas mínimas con el comando completo y el control nativo de copia de GitHub.
- Alternativa mediante pulsación prolongada para versiones de la app que oculten el icono.
- Instrucciones separadas para pegar en a-Shell y Termux sin cortar accidentalmente el enlace.

## 7.6.14 — 2026-07-17

- PolyForm Strict License 1.0.0 aplicada a esta versión y las posteriores.
- Uso personal no comercial permitido sin autorizar redistribución ni modificaciones.
- Transición documentada: las versiones 7.6.0 a 7.6.13 conservan su licencia MIT.
- Nombre e identidad de FlowMobile reservados para distinguir el proyecto oficial.
- Aviso visible del repositorio oficial y verificaciones automáticas de licencia.

## 7.6.13 — 2026-07-17

- Adjuntos locales de Codex protegidos para impedir que `git add .` pueda publicarlos.
- Correo personal retirado de la guía de publicación y sustituido por una dirección privada de GitHub.
- Comprobaciones automáticas para conservar ambas protecciones en futuras versiones.

## 7.6.12 — 2026-07-17

- Treinta plataformas nuevas reconocidas por nombre en análisis, errores e historial.
- Catálogo visible de 35 plataformas dentro de Herramientas y ajustes.
- Dominios cortos y móviles identificados sin aceptar dominios impostores.
- Separación clara entre compatibilidad técnica y contenidos que requieren cuenta, cookies o región.
- Buzón de sugerencias y reportes de errores conectado a GitHub Issues.
- Reportes de seguridad dirigidos al canal privado de GitHub.
- Formularios revisables que solo añaden versión y dispositivo, sin datos personales.
- Submenú reorganizado por ayuda, privacidad y mantenimiento.
- Sugerencias y reportes visibles como primera opción de Ayuda y herramientas.
- Sistema y Modo Reparar unificados; diagnóstico y pruebas reunidos sin perder funciones.

## 7.6.11 — 2026-07-16

- Aviso inmediato cuando GitHub responde después de que el menú ya fue dibujado.
- Caché persistente de la versión disponible y sus novedades.
- Aviso conservado entre inicios aunque una comprobación posterior falle por conexión.
- Actualización visible desde el primer menú sin hacer más lento el arranque.
- Timbre y mensaje directo para entrar en `[5] Actualizaciones` cuando se descubre una versión nueva.

## 7.6.10 — 2026-07-16

- Registro automático de cada descarga en el catálogo multimedia de Android.
- Uso de `termux-media-scan` cuando Termux:API está disponible.
- Respaldo mediante el broadcast nativo `MEDIA_SCANNER_SCAN_FILE` sin complementos.
- Compatibilidad con perfiles secundarios de Android mediante `TERMUX__USER_ID`.
- Prueba de regresión para impedir que vuelva a ser necesario mover o pegar el vídeo manualmente.

## 7.6.9 — 2026-07-16

- Selector de aplicaciones Android forzado al compartir desde Termux.
- Instalación y actualización explícita de `termux-tools`, que proporciona `termux-open`.
- Tipo MIME explícito para vídeos, audios y otros archivos.
- Respaldo opcional mediante `termux-share` cuando Termux:API ya está disponible.
- Tiempo máximo para impedir que una integración Android bloquee el menú.
- Ruta humana de Movies o Music mostrada después de cada descarga.
- Instrucciones para localizar y compartir manualmente desde la aplicación Archivos.

## 7.6.8 — 2026-07-16

- Vídeos de Termux guardados en `Android/Movies/FlowMobile` para que aparezcan en la galería.
- Audios guardados en la carpeta multimedia estándar `Android/Music/FlowMobile`.
- Lotes nuevos separados entre Movies y Music según el tipo de descarga.
- Migración sin duplicados de los archivos creados por la versión 7.6.7.
- Compatibilidad para reanudar las colas antiguas que continúen en Download.
- Desinstalación completa ampliada a Download, Movies y Music.

## 7.6.7 — 2026-07-16

- Descargas de Termux fijadas en la carpeta pública `Android/Download/FlowMobile`.
- Verificación de escritura real después de solicitar el permiso de Android.
- Bloqueo seguro de las descargas cuando falta el permiso, sin crear archivos ocultos.
- Migración automática de descargas antiguas desde los datos privados de Termux.
- Compartir mediante `termux-open` sin exigir Termux:API.
- Escaneo opcional de los archivos terminados para mostrarlos antes en la galería.
- Estado del almacenamiento y ruta de descargas visibles en el menú Sistema.

## 7.6.5 — 2026-07-16

- Normalización de rutas equivalentes antes de aplicar las protecciones del borrado.
- Compatibilidad con los alias `/var` y `/private/var` usados por iOS y a-Shell.
- Compatibilidad de la regresión de seguridad con nombres cortos y largos de Windows.

## 7.6.4 — 2026-07-16

- Desinstalador independiente para borrar FlowMobile incluso cuando la aplicación está abierta desde su propia carpeta.
- Renombrado temporal de la instalación antes de eliminarla para que desaparezca inmediatamente de Documents.
- Limpieza verificada de código, datos, descargas, reservas, lanzadores, alias y restos de instalaciones antiguas.
- Opción adicional para retirar `yt-dlp` y `yt-dlp-ejs` y dejar a-Shell preparado para una instalación desde cero.
- Rutas limitadas estrictamente a Documents y conservación de archivos ajenos al proyecto.
- Tres pruebas de regresión para confirmación, limpieza completa y protección de rutas externas.

## 7.6.3 — 2026-07-15

- Activación inmediata del alias `flow` en la sesión actual de a-Shell mediante `ios_system`.
- El `.profile` se mantiene como registro permanente para todas las ventanas futuras.
- Respaldo explícito mediante carga manual del perfil cuando la API nativa no esté disponible.
- Prueba de regresión que verifica la orden exacta enviada al sistema de alias de a-Shell.

## 7.6.2 — 2026-07-15

- El instalador de a-Shell verifica el archivo lanzador y el alias antes de informar éxito.
- Instrucción explícita para activar `flow` en la misma ventana después de finalizar `curl`.
- Mensaje diferenciado entre continuar en la ventana actual y abrir una ventana nueva.
- Pruebas de regresión para impedir instalaciones que no registren el comando `flow`.

## 7.6.1 — 2026-07-15

- La comprobación de publicación usa exactamente el Python preparado por GitHub Actions.
- Compatibilidad de la prueba de desinstalación con rutas cortas y largas equivalentes de Windows.
- Regresión de CI corregida sin cambiar el comportamiento de a-Shell ni Termux.

## 7.6.0 — 2026-07-15

- Detección confirmada de enlaces del portapapeles mediante `pbpaste` en a-Shell y Termux:API en Android.
- Lectura del portapapeles limitada a las pantallas de descarga y sin iniciar acciones automáticamente.
- Reintentos de yt-dlp con espera exponencial y pausa entre solicitudes para reducir bloqueos por exceso de peticiones.
- Actualizaciones transaccionales con respaldo y restauración automática de la versión anterior.
- Canal estable basado en GitHub Releases con paquetes ZIP, TAR.GZ y checksums SHA-256.
- GitHub Actions para Python 3.10, 3.12 y 3.13, instaladores y validación de publicación.
- Licencia MIT, política de seguridad, guía de contribución e incidencias sin datos privados.
- Informe de diagnóstico compartible que excluye enlaces, cookies y rutas personales.
- Interfaz accesible sin limpieza de pantalla, colores opcionales y menú de herramientas separado internamente.
- Matriz documentada de pruebas reales para instalación, actualización, descarga, compartir y desinstalación.

## 7.5.3 — 2026-07-15

- La desinstalación con conservación elimina ahora toda la carpeta del programa.
- Descargas, historial, ajustes, cookies y colas se trasladan a una reserva privada separada.
- El instalador de a-Shell y Termux restaura automáticamente esa reserva al reinstalar.
- El borrado total elimina también cualquier reserva creada por una desinstalación anterior.
- Verificación posterior para no informar éxito cuando el sistema no eliminó una ruta.
- Protección de `.flowmobile-data` en Git y en la comprobación de publicación.

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
