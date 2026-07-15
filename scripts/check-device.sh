#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(dirname "$SCRIPT_DIR")
cd "$PROJECT_DIR"

PYTHON_COMMAND="${FLOWMOBILE_PYTHON:-}"
if [ -z "$PYTHON_COMMAND" ]; then
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            PYTHON_COMMAND="$candidate"
            break
        fi
    done
fi
if [ -z "$PYTHON_COMMAND" ]; then
    echo "ERROR: Python no está disponible."
    echo "En iOS usa a-Shell completo, no a-Shell mini ni la extensión de Atajos."
    exit 1
fi

echo "FlowMobile $(cat VERSION)"
echo "Comprobando sintaxis de Python…"
"$PYTHON_COMMAND" -m compileall -q flow main.py

echo "Comprobando plataforma y yt-dlp…"
"$PYTHON_COMMAND" -c 'from flow.infrastructure.platform import PLATFORM; import yt_dlp; print(f"{PLATFORM.mobile_os} / {PLATFORM.name} / yt-dlp {yt_dlp.version.__version__}")'

echo "Comprobando herramientas multimedia…"
ffmpeg -version >/dev/null
ffprobe -version >/dev/null

echo "Ejecutando pruebas…"
"$PYTHON_COMMAND" -m unittest discover -s tests -v

echo "FlowMobile está listo para una prueba real de audio y video."
