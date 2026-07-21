# Guía completa de FlowMobile

Esta guía reúne los detalles de instalación, uso, privacidad y mantenimiento.
Para instalar rápidamente, vuelve a la [portada](../README.md).

## Requisitos

- iPhone/iPad: aplicación **a-Shell completa**; a-Shell mini no incluye Python.
- Android: una versión reciente de **Termux** procedente de GitHub o F-Droid.
- Windows 10/11: **PowerShell 5.1** o posterior y App Installer (`winget`).
- Linux: distribución con `apt`, `dnf`, `pacman` o `zypper`.
- Conexión a internet y espacio suficiente para los archivos elegidos.

## Instalación manual

En a-Shell:

```sh
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/bootstrap_ios.py | python3 - tacosandtypescript-debug/FlowMobile
```

En Termux:

```sh
umask 077; pkg install -y curl > "$HOME/.flowmobile-install.log" 2>&1 || { echo "No se pudo preparar curl:"; tail -n 1 "$HOME/.flowmobile-install.log"; exit 1; }
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install.sh | sh -s -- tacosandtypescript-debug/FlowMobile
```

En Windows PowerShell:

```powershell
irm https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install-windows.ps1 | iex
```

En Linux:

```sh
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install-linux.sh | sh -s -- tacosandtypescript-debug/FlowMobile && export PATH="$HOME/.local/bin:$PATH" && hash -r
```

El instalador prepara Python, yt-dlp, EJS y FFmpeg cuando el dispositivo lo
permite. En Android también solicita acceso al almacenamiento. Al finalizar,
abre una ventana nueva y ejecuta `flow`.

### Progreso y solución de errores

La instalación muestra únicamente seis etapas. La salida completa se guarda
con permisos privados en `~/.flowmobile-install.log` y se reemplaza en cada
intento. Si algo falla, FlowMobile indica la etapa, un código identificable,
el error original y la acción recomendada.

Para consultar el registro:

```sh
cat ~/.flowmobile-install.log
```

Para mostrar también la salida técnica durante una prueba:

```sh
# a-Shell
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/bootstrap_ios.py | FLOWMOBILE_VERBOSE=1 python3 - tacosandtypescript-debug/FlowMobile

# Termux
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install.sh | FLOWMOBILE_VERBOSE=1 sh -s -- tacosandtypescript-debug/FlowMobile
```

No desactives una comprobación SHA-256. Los errores `INTEGRITY` indican que el
archivo no coincide con el release oficial y la instalación debe detenerse.

## Descargas y galería

- a-Shell guarda los archivos dentro de `FlowMobile/Downloads`.
- Android guarda los vídeos en `Movies/FlowMobile` y los audios en
  `Music/FlowMobile`.
- Android registra los archivos terminados en el catálogo multimedia para que
  aparezcan en la galería.
- Windows y Linux guardan en `Downloads/FlowMobile/Videos` y
  `Downloads/FlowMobile/Audio` (o en `FLOWMOBILE_DOWNLOADS`).
- Desde Historial o Mis archivos se puede reproducir, localizar o compartir una
  descarga.

## Calidad y plataformas

FlowMobile analiza los formatos reales ofrecidos por yt-dlp. Permite elegir
vídeo desde 360p hasta 2160p, mejor calidad disponible, o audio automático,
M4A y MP3. Al terminar verifica resolución, FPS, códec y tamaño.

Reconoce 35 plataformas, incluidas YouTube, TikTok, Facebook, Instagram, X,
Vimeo, Dailymotion, Twitch, Reddit, Pinterest, Snapchat, SoundCloud, Bandcamp,
Mixcloud, Rumble, Bilibili, VK, Telegram, LinkedIn, Bluesky y otras. Algunos
contenidos pueden requerir una cuenta, cookies propias o estar limitados por
región.

## Cookies y privacidad

Desde **Ayuda y herramientas → Cookies y sesiones** se puede importar un
`cookies.txt` en formato Netscape. FlowMobile lo copia al almacenamiento
privado y nunca incluye cookies, enlaces, historial ni rutas personales en
diagnósticos o reportes.

Usa únicamente cookies propias. Las cookies pueden resolver un inicio de sesión,
pero no evitan bloqueos de IP, restricciones regionales ni reglas del sitio.

## Lotes, playlists y reanudación

El menú de lotes acepta varios enlaces y playlists, conserva una cola con
pendientes, completadas y errores, y separa sus archivos por fecha. Durante una
descarga escribe `c` y pulsa Enter, o usa `Ctrl+C`, para pausarla conservando
los archivos `.part`. Al repetir el enlace, yt-dlp intenta continuar.

## Actualizaciones y reparación

FlowMobile revisa en segundo plano si hay una versión nueva de la aplicación,
yt-dlp, EJS o FFmpeg. Siempre pregunta antes de actualizar. La instalación nueva
se valida antes de eliminar el respaldo anterior.

**Sistema y reparación** comprueba Python, yt-dlp, EJS, FFmpeg y FFprobe. Puede
reparar dependencias y limpiar temporales dañados sin borrar vídeos, audios,
historial, ajustes, cookies ni colas activas.

## Desinstalación

En **Ayuda y herramientas → Desinstalar FlowMobile** se puede:

- quitar la aplicación conservando datos para una instalación futura; o
- escribir `BORRAR` para eliminar programa, descargas, historial, cookies,
  colas y ajustes.

Para limpiar una instalación de a-Shell que no abre:

```sh
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/uninstall_ios.py | python3 - BORRAR
```

## Errores, sugerencias y seguridad

El menú **Ayuda y herramientas → Sugerencias y reportes** abre los formularios
del repositorio. Los errores normales pueden enviarse mediante
[GitHub Issues](https://github.com/tacosandtypescript-debug/FlowMobile/issues).
Las vulnerabilidades y datos sensibles deben enviarse de forma privada siguiendo
[la política de seguridad](../SECURITY.md).

## Desarrollo y pruebas autorizadas

Las modificaciones requieren autorización previa según
[CONTRIBUTING.md](../CONTRIBUTING.md). En un entorno autorizado:

```sh
python3 -m pip install -r requirements.txt
python3 main.py
python3 -m unittest discover -s tests -v
```
