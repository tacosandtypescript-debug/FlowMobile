# FlowMobile

Descarga video o extrae audio desde una interfaz de terminal para **a-Shell en
iOS** y **Termux en Android**.

Versión actual: **7.3.6**. El comando de ejecución es `flow` en ambas
plataformas.

## Instalación en a-Shell

Enlace público del repositorio oficial:

```sh
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/install_ios.py | python3 - tacosandtypescript-debug/FlowMobile
```

Se requiere la aplicación **a-Shell completa** abierta directamente. El
instalador se ejecuta con Python para no abrir el entorno aislado `dash`, que no
puede acceder a los comandos internos de a-Shell. a-Shell mini y la extensión
ligera de Atajos no incluyen el entorno Python necesario.

El instalador reemplaza aliases antiguos que todavía apunten a `FlowApp` o
`FlowIOS`. Cuando termine, cierra esa ventana de a-Shell y abre una nueva para
que cargue `.profile`; después escribe `flow`. No añadas `&&` a la orden porque
a-Shell lo entrega a Python como texto. En la ventana actual también se puede
iniciar directamente con `python3 FlowMobile/main.py`.

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

## Desarrollo y pruebas

```sh
python3 -m pip install -r requirements.txt
python3 main.py
python3 -m unittest discover -s tests -v
```

Cada publicación debe actualizar `VERSION`, `APP_VERSION` y `CHANGELOG.md`.
