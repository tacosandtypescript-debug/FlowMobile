# Pruebas en dispositivos

Esta matriz debe completarse antes de crear una etiqueta estable.

## Preparación

- Probar en una instalación limpia de a-Shell en iOS.
- Probar en una instalación limpia de Termux procedente de F-Droid o GitHub.
- Probar en Windows 10/11 con PowerShell 5.1 y PowerShell 7.
- Probar al menos Ubuntu/Debian y una distribución con `dnf` o `pacman`.
- Ejecutar `python3 scripts/check_device.py` en a-Shell.
- Ejecutar `sh scripts/check-device.sh` en Termux.
- Confirmar que todas las pruebas automatizadas terminan correctamente.

## Matriz obligatoria

En cada plataforma comprobar:

- Instalación inicial mediante el enlace público.
- Apertura de `flow` desde una ventana nueva.
- Resultado correcto de `flow --health-check` y `flow --version`.
- Detección y confirmación de una URL del portapapeles.
- Vídeo 360p, 720p y 1080p.
- Audio M4A y MP3.
- Compartir o guardar el archivo mediante la hoja del sistema.
- Cancelación y reanudación de una descarga.
- Cola de varios enlaces y playlist.
- Importación y eliminación de cookies Netscape propias.
- Actualización conservando descargas, ajustes y cookies.
- Fallo simulado de actualización y restauración de la versión anterior.
- Instalación silenciosa: solo seis etapas y ningún bloque de salida de `pkg`,
  `pip` o `curl` en modo normal.
- Fallos simulados de DNS, HTTP 404/429, repositorio de paquetes, `pip`, hash,
  archivo dañado, falta de espacio y permiso de almacenamiento.
- Código, causa, detalle original, solución y ruta del registro presentes en
  cada fallo; salida completa visible con `FLOWMOBILE_VERBOSE=1`.
- Registro `~/.flowmobile-install.log` reemplazado en cada intento y protegido
  para el usuario actual.
- Desinstalación conservando datos y posterior reinstalación.
- Desinstalación total escribiendo `BORRAR`.

## Plataformas de contenido

La prueba completa admite enlaces públicos y autorizados de YouTube, TikTok,
Facebook, Instagram y X. No guardes los enlaces en incidencias ni informes.

Un bloqueo de IP, una cuenta privada o una limitación regional no demuestra un
fallo del archivo descargado. Registra por separado el mensaje presentado por
FlowMobile y evita reintentos repetidos.
