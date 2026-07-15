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
test -f main.py
test -f install_ios.py
test -f install-termux.sh
test -f scripts/flow_ios.py
test ! -d "$(dirname "$PROJECT_DIR")/.flowmobile-rollback"
FILE_VERSION=$(tr -d '\r\n' < VERSION)
CODE_VERSION=$($PYTHON_COMMAND -c 'from flow import APP_VERSION; print(APP_VERSION)')
if [ "$FILE_VERSION" != "$CODE_VERSION" ]; then
    echo "ERROR: VERSION y el código no coinciden."
    exit 1
fi
echo "Comprobando sintaxis de Python…"
"$PYTHON_COMMAND" -m compileall -q flow main.py install_ios.py bootstrap_ios.py scripts/release_notes.py

echo "Comprobando plataforma y yt-dlp…"
"$PYTHON_COMMAND" -c 'from flow.infrastructure.platform import PLATFORM; import yt_dlp; print(f"{PLATFORM.mobile_os} / {PLATFORM.name} / yt-dlp {yt_dlp.version.__version__}")'

echo "Comprobando herramientas multimedia…"
ffmpeg -version >/dev/null
ffprobe -version >/dev/null

echo "Ejecutando pruebas…"
"$PYTHON_COMMAND" -m unittest discover -s tests -v

echo "FlowMobile está listo para una prueba real de audio y video."
