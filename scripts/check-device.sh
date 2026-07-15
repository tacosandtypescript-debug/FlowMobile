#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(dirname "$SCRIPT_DIR")
cd "$PROJECT_DIR"

echo "FlowMobile $(cat VERSION)"
echo "Comprobando sintaxis de Python…"
python3 -m compileall -q flow main.py

echo "Comprobando plataforma y yt-dlp…"
python3 -c 'from flow.infrastructure.platform import PLATFORM; import yt_dlp; print(f"{PLATFORM.mobile_os} / {PLATFORM.name} / yt-dlp {yt_dlp.version.__version__}")'

echo "Comprobando herramientas multimedia…"
ffmpeg -version >/dev/null
ffprobe -version >/dev/null

echo "Ejecutando pruebas…"
python3 -m unittest discover -s tests -v

echo "FlowMobile está listo para una prueba real de audio y video."
