# Pruebas en dispositivos

Esta matriz debe completarse antes de crear una etiqueta estable.

## Preparación

- Probar en una instalación limpia de a-Shell en iOS.
- Probar en una instalación limpia de Termux procedente de F-Droid o GitHub.
- Ejecutar `python3 scripts/check_device.py` en a-Shell.
- Ejecutar `sh scripts/check-device.sh` en Termux.
- Confirmar que todas las pruebas automatizadas terminan correctamente.

## Matriz obligatoria

En cada plataforma comprobar:

- Instalación inicial mediante el enlace público.
- Apertura de `flow` desde una ventana nueva.
- Detección y confirmación de una URL del portapapeles.
- Vídeo 360p, 720p y 1080p.
- Audio M4A y MP3.
- Compartir o guardar el archivo mediante la hoja del sistema.
- Cancelación y reanudación de una descarga.
- Cola de varios enlaces y playlist.
- Importación y eliminación de cookies Netscape propias.
- Actualización conservando descargas, ajustes y cookies.
- Fallo simulado de actualización y restauración de la versión anterior.
- Desinstalación conservando datos y posterior reinstalación.
- Desinstalación total escribiendo `BORRAR`.

## Plataformas de contenido

La prueba completa admite enlaces públicos y autorizados de YouTube, TikTok,
Facebook, Instagram y X. No guardes los enlaces en incidencias ni informes.

Un bloqueo de IP, una cuenta privada o una limitación regional no demuestra un
fallo del archivo descargado. Registra por separado el mensaje presentado por
FlowMobile y evita reintentos repetidos.
