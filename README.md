# FlowMobile

Descarga video o extrae audio desde una interfaz de terminal para **a-Shell en
iOS** y **Termux en Android**.

Versión actual: **7.6.4**. El comando de ejecución es `flow` en ambas
plataformas.

[![CI](https://github.com/tacosandtypescript-debug/FlowMobile/actions/workflows/ci.yml/badge.svg)](https://github.com/tacosandtypescript-debug/FlowMobile/actions/workflows/ci.yml)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE)

## Instalación en a-Shell

Enlace público del repositorio oficial:

```sh
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/bootstrap_ios.py | python3 - tacosandtypescript-debug/FlowMobile
```

Se requiere la aplicación **a-Shell completa** abierta directamente. El
instalador se ejecuta con Python para no abrir el entorno aislado `dash`, que no
puede acceder a los comandos internos de a-Shell. a-Shell mini y la extensión
ligera de Atajos no incluyen el entorno Python necesario.

El bootstrap consulta la API de GitHub para evitar copias antiguas de caché. El
instalador elimina el código previo de `FlowMobile`, `FlowApp` y `FlowIOS`, pero
conserva descargas, historial y ajustes. Al terminar, abre una ventana nueva de
a-Shell y escribe `flow`. El instalador no abre el menú dentro de la tubería de
`curl`, porque esa entrada ya está cerrada. No añadas `sh`, `&&` ni otros
comandos al enlace.

El instalador registra `flow` en la sesión actual mediante `ios_system` y lo
conserva en `.profile` para las ventanas futuras. Si una versión de a-Shell no
permite la activación inmediata, el propio instalador muestra el respaldo
`cd && . ./.profile && flow` como una orden separada.

## Instalación en Termux

Usa una versión actual de Termux procedente de GitHub o F-Droid. Después ejecuta:

```sh
pkg install -y curl
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/install.sh | sh -s -- tacosandtypescript-debug/FlowMobile
```

El instalador de Termux detecta Android y prepara automáticamente Python,
FFmpeg y `yt-dlp`. En Android también solicita acceso a Descargas. a-Shell usa
su instalador Python específico porque iOS no permite ejecutar sus comandos
internos desde un proceso `sh` secundario.

Para instalaciones automáticas sin preguntas se puede añadir `--auto`:

```sh
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/install.sh | sh -s -- tacosandtypescript-debug/FlowMobile --auto
```

Después se puede iniciar desde cualquier carpeta:

```sh
flow
```

## Archivos y privacidad

- a-Shell guarda las descargas dentro de `FlowMobile/Downloads`.
- Termux guarda el programa en `$HOME/FlowMobile`.
- En Android, si se concedió el permiso, los archivos se guardan en
  `Download/FlowMobile`; de lo contrario se usa una carpeta privada.
- Historial y ajustes se guardan en `.flowmobile`, fuera de las descargas
  públicas.
- El instalador conserva descargas, historial y ajustes durante actualizaciones.

## Actualizaciones

En cada inicio, FlowMobile comprueba:

- la versión de FlowMobile publicada en GitHub;
- la versión estable de `yt-dlp` y sus componentes EJS;
- disponibilidad de FFmpeg y FFprobe;
- en Termux, actualizaciones del paquete FFmpeg.

Si encuentra cambios, muestra las versiones y pregunta antes de instalarlos.
En a-Shell, FFmpeg se actualiza junto con la aplicación; en Termux se administra
mediante `pkg`.

Cuando se publica una versión nueva, el menú muestra una sección **Novedades**
con el número de versión y hasta cinco cambios tomados de `CHANGELOG.md`. Si la
persona decide esperar, el aviso permanece disponible y vuelve a mostrarse en
el siguiente inicio.

## Funciones

- Mejor fuente de video y audio detectada por `yt-dlp`.
- Calidades desde 360p hasta 2160p.
- Audio automático, M4A o MP3.
- Verificación final de resolución, FPS y códec.
- Historial, archivos recientes y menú para compartir.
- Rutas, reproducción y compartir adaptados a iOS o Android.
- Panel de almacenamiento, preferencias y mensajes por plataforma.
- Menú agrupado por tareas y selector compacto con acceso a todas las calidades.
- Instalador y lanzador Python nativos para los comandos internos de a-Shell.
- Barra de progreso suavizada con porcentaje, velocidad y tiempo restante.
- Aviso sonoro al terminar y notificación nativa opcional mediante Termux:API.
- Buscador del historial por título, sitio, tipo, calidad o fecha.
- Modo Reparar para revisar dependencias y retirar únicamente temporales dañados.
- Pruebas reales guiadas para 360p, 720p, 1080p, máxima calidad, M4A y MP3.
- Informes privados con resolución, códecs, tamaño y disponibilidad para compartir.
- Apertura inmediata del menú mientras las actualizaciones se revisan en segundo plano.
- Renderizado del panel en un solo bloque para evitar tirones visuales en a-Shell.
- Detección inicial de FFmpeg y FFprobe fuera del hilo de interfaz de iOS.
- Cookies Netscape importadas en almacenamiento privado y aplicadas automáticamente.
- Cancelación limpia mediante `c` + Enter, conservando los `.part` para continuar.
- Colas persistentes para varios enlaces y playlists, con reanudación tras cerrar la app.
- Archivos de cada lote separados dentro de `Downloads/Lotes/<fecha>`.
- Menú principal compacto; diagnóstico, sesiones y reparación viven en Herramientas.
- Detección confirmada de enlaces copiados, sin descargar nada sin permiso.
- Actualización con respaldo automático y restauración si la versión nueva falla.
- Interfaz accesible sin borrado de pantalla y opción para desactivar colores.
- Informe de diagnóstico privado preparado para compartir.

## Portapapeles

Al abrir **Nueva descarga**, FlowMobile consulta una sola vez el portapapeles. En
a-Shell utiliza `pbpaste`; en Termux utiliza `termux-clipboard-get` cuando
Termux:API está instalado. Si encuentra un enlace muestra únicamente la
plataforma y pregunta si se quiere usar. Presionar Enter confirma; nunca inicia
la descarga automáticamente. Se puede desactivar desde **Ajustes → Portapapeles**.

## Cookies y sesiones privadas

Desde **Herramientas y ajustes → Cookies y sesiones** se puede importar un
archivo `cookies.txt` en formato Netscape. FlowMobile lo copia a
`.flowmobile/sessions`, aplica permisos privados y lo utiliza automáticamente
al analizar o descargar. La ruta original no se guarda. Las cookies nunca se
incluyen en el historial, los diagnósticos, las colas ni GitHub.

Las cookies permiten que yt-dlp use una sesión ya iniciada, pero no evitan las
reglas del sitio. Solo deben importarse cookies propias y no deben compartirse.

Si TikTok indica que la dirección IP está bloqueada, abre primero el enlace en
Safari desde la misma red y resuelve cualquier inicio de sesión o CAPTCHA. Si el
bloqueo continúa, cambia entre Wi-Fi y datos móviles antes de volver a intentar.
Importar cookies recientes puede resolver una sesión, pero no un bloqueo directo
de la dirección IP.

## Cancelar, continuar y descargar por lotes

Durante una transferencia escribe `c` y presiona Enter, o utiliza `Ctrl+C`.
FlowMobile pausa la
descarga y protege los archivos `.part`; al pegar el mismo enlace, yt-dlp
continúa automáticamente. El Modo Reparar no elimina parciales registrados para
reanudación.

La opción **Lotes y playlists** acepta varios enlaces, extrae los elementos de
una playlist y muestra completadas, pendientes y errores. Cada cola se guarda
privadamente en `.flowmobile/queues` y puede reanudarse desde el mismo menú. Los
medios terminados se organizan en:

```text
Downloads/Lotes/AAAAMMDD-HHMMSS/Videos
Downloads/Lotes/AAAAMMDD-HHMMSS/Audio
```

## Actualizar, reinstalar o desinstalar

Las actualizaciones normales reemplazan el código y conservan descargas,
historial, ajustes, cookies y colas. En **Herramientas y ajustes → Desinstalar
FlowMobile** existen dos opciones:

- **Conservar datos:** elimina el programa y el comando `flow`, pero deja los
  datos en una reserva privada `.flowmobile-data`, fuera de la carpeta del
  programa. El instalador los restaura automáticamente en una instalación futura.
- **Borrar absolutamente todo:** elimina programa, lanzadores, descargas,
  cookies, colas, historial y ajustes. Requiere escribir `BORRAR` exactamente.

En a-Shell también se limpia el bloque administrado dentro de `.profile` y los
lanzadores antiguos de `Documents/bin`. En Termux solo se elimina el ejecutable
`flow` cuando se comprueba que pertenece a FlowMobile.

Si una instalación anterior no puede borrarse desde el menú, este limpiador se
ejecuta fuera de la carpeta del programa, elimina también los datos y verifica
que no quede ningún residuo de FlowMobile:

```sh
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/uninstall_ios.py | python3 - BORRAR
```

Para volver completamente a cero, incluida la copia de `yt-dlp` y `yt-dlp-ejs`
instalada por FlowMobile, añade `--dependencies` al final. Python, FFmpeg y
FFprobe forman parte de a-Shell y no se eliminan. Después cierra la ventana.

Antes de actualizar se conserva una copia completa de la versión instalada. La
copia solo se elimina después de validar el código, el lanzador y las
dependencias nuevas. Si cualquier paso falla, el instalador restaura la versión
anterior. Las versiones estables se publican en GitHub Releases junto con
`SHA256SUMS`.

## Diagnóstico y accesibilidad

**Herramientas → Informe de diagnóstico** crea un JSON con versión, plataforma,
Python, yt-dlp, EJS, FFmpeg, FFprobe y espacio libre. No contiene enlaces,
cookies, historial ni rutas personales y puede compartirse desde el sistema.

En **Ajustes → Interfaz** se puede elegir el modo accesible, que evita limpiar
la pantalla y anuncia el progreso por intervalos. Los colores pueden
desactivarse desde Ajustes o iniciando con `NO_COLOR=1 flow`.

## Modo Reparar y pruebas reales

La opción **7 · Modo Reparar** comprueba Python, yt-dlp, EJS, FFmpeg y
FFprobe. Puede reinstalar las dependencias compatibles con el dispositivo y
limpiar archivos `.part`, `.ytdl`, `.tmp` o conversiones incompletas con más de
cinco minutos. No elimina vídeos, audios, historial ni ajustes.

La opción **8 · Pruebas reales** ofrece una prueba rápida y una matriz completa.
La completa admite un enlace de YouTube, TikTok, Facebook, Instagram y X, y
prueba vídeo 360p, 720p, 1080p, máxima calidad, audio M4A y MP3. Los enlaces no
se escriben en el informe. La comprobación final de Compartir siempre requiere
confirmación de la persona, porque abre la interfaz del sistema.

## Desarrollo y pruebas

```sh
python3 -m pip install -r requirements.txt
python3 main.py
python3 -m unittest discover -s tests -v
```

Cada publicación debe actualizar `VERSION`, `APP_VERSION` y `CHANGELOG.md`.
