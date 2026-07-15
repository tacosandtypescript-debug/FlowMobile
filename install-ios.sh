#!/bin/sh
set -eu

REPOSITORY="${1:-${FLOWMOBILE_REPOSITORY:-tacosandtypescript-debug/FlowMobile}}"
BRANCH="${FLOWMOBILE_BRANCH:-main}"
DOCUMENTS="$HOME"
case "$DOCUMENTS" in
    */Documents) ;;
    *) DOCUMENTS="$HOME/Documents" ;;
esac
APP_DIR="${FLOWMOBILE_HOME:-$DOCUMENTS/FlowMobile}"
BIN_DIR="$DOCUMENTS/bin"
WORK_DIR="${TMPDIR:-$DOCUMENTS/tmp}/flowmobile-install-$$"
ARCHIVE="$WORK_DIR/flowmobile.tar.gz"

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
    echo "Python no está disponible en este entorno."
    echo "FlowMobile requiere la aplicación a-Shell completa, no a-Shell mini."
    echo "Abre a-Shell directamente; no ejecutes el instalador desde una extensión de Atajos."
    exit 1
fi

echo "Instalando FlowMobile para a-Shell…"
mkdir -p "$WORK_DIR" "$BIN_DIR"
cd "$DOCUMENTS"
curl -fL "https://github.com/$REPOSITORY/archive/refs/heads/$BRANCH.tar.gz" -o "$ARCHIVE"
tar -xzf "$ARCHIVE" -C "$WORK_DIR"

SOURCE_DIR=""
for candidate in "$WORK_DIR"/*; do
    if [ -d "$candidate/flow" ] && [ -f "$candidate/main.py" ]; then
        SOURCE_DIR="$candidate"
        break
    fi
done
[ -n "$SOURCE_DIR" ] || { echo "El paquete de FlowMobile no es válido."; exit 1; }

BACKUP_DIR="$WORK_DIR/previous"
EXISTING_DIR=""
if [ -d "$APP_DIR" ]; then
    EXISTING_DIR="$APP_DIR"
else
    for legacy in "$DOCUMENTS/FlowIOS" "$DOCUMENTS/FlowApp"; do
        if [ -d "$legacy" ]; then EXISTING_DIR="$legacy"; break; fi
    done
fi
if [ -n "$EXISTING_DIR" ]; then mv "$EXISTING_DIR" "$BACKUP_DIR"; fi
if ! mv "$SOURCE_DIR" "$APP_DIR"; then
    if [ -d "$BACKUP_DIR" ]; then mv "$BACKUP_DIR" "$APP_DIR"; fi
    echo "No se pudo instalar; se restauró la versión anterior."
    exit 1
fi

for item in Downloads .flowmobile flow_settings.json; do
    if [ -e "$BACKUP_DIR/$item" ] && [ ! -e "$APP_DIR/$item" ]; then
        mv "$BACKUP_DIR/$item" "$APP_DIR/$item"
    fi
done

printf '%s\n' "$REPOSITORY" > "$APP_DIR/.flowmobile-source"
cp "$APP_DIR/scripts/flow" "$BIN_DIR/flow"
chmod +x "$BIN_DIR/flow"
"$PYTHON_COMMAND" -m pip install --disable-pip-version-check --no-deps --upgrade \
    yt-dlp yt-dlp-ejs
rm -rf "$WORK_DIR"

echo "FlowMobile instalado para iOS. Escribe: flow"
