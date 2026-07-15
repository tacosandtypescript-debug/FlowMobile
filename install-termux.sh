#!/bin/sh
set -eu

REPOSITORY="${1:-${FLOWMOBILE_REPOSITORY:-tacosandtypescript-debug/FlowMobile}}"
BRANCH="${FLOWMOBILE_BRANCH:-main}"
APP_DIR="${FLOWMOBILE_HOME:-$HOME/FlowMobile}"
DATA_BACKUP_DIR="$(dirname "$APP_DIR")/.flowmobile-data"
BIN_DIR="${PREFIX:-$HOME/../usr}/bin"
WORK_DIR="${TMPDIR:-${PREFIX:-$HOME/../usr}/tmp}/flowmobile-install-$$"
ARCHIVE="$WORK_DIR/flowmobile.tar.gz"

echo "Preparando Termux…"
pkg update -y
pkg install -y python python-pip ffmpeg curl

if [ ! -d "$HOME/storage/downloads" ]; then
    echo "Android solicitará permiso para acceder a Descargas."
    termux-setup-storage || true
fi

echo "Instalando FlowMobile para Termux…"
mkdir -p "$WORK_DIR" "$BIN_DIR"
cd "$HOME"
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
    for legacy in "$HOME/FlowIOS" "$HOME/FlowApp"; do
        if [ -d "$legacy" ]; then EXISTING_DIR="$legacy"; break; fi
    done
fi
if [ -n "$EXISTING_DIR" ]; then mv "$EXISTING_DIR" "$BACKUP_DIR"; fi
if ! mv "$SOURCE_DIR" "$APP_DIR"; then
    if [ -d "$BACKUP_DIR" ]; then mv "$BACKUP_DIR" "$APP_DIR"; fi
    echo "No se pudo instalar; se restauró la versión anterior."
    exit 1
fi

for saved in "$DATA_BACKUP_DIR" "$BACKUP_DIR"; do
    for item in Downloads .flowmobile flow_settings.json; do
        if [ -e "$saved/$item" ] && [ ! -e "$APP_DIR/$item" ]; then
            mv "$saved/$item" "$APP_DIR/$item"
        fi
    done
done
rmdir "$DATA_BACKUP_DIR" 2>/dev/null || true

printf '%s\n' "$REPOSITORY" > "$APP_DIR/.flowmobile-source"
cp "$APP_DIR/scripts/flow" "$BIN_DIR/flow"
chmod +x "$BIN_DIR/flow"
python3 -m pip install --disable-pip-version-check --upgrade "yt-dlp[default]"
rm -rf "$WORK_DIR"

echo "FlowMobile instalado para Android. Escribe: flow"
