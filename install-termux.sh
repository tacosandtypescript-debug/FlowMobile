#!/bin/sh
set -eu

REPOSITORY="${1:-${FLOWMOBILE_REPOSITORY:-tacosandtypescript-debug/FlowMobile}}"
BRANCH="${FLOWMOBILE_BRANCH:-main}"
APP_DIR="${FLOWMOBILE_HOME:-$HOME/FlowMobile}"
DATA_BACKUP_DIR="$(dirname "$APP_DIR")/.flowmobile-data"
BIN_DIR="${PREFIX:-$HOME/../usr}/bin"
WORK_DIR="${TMPDIR:-${PREFIX:-$HOME/../usr}/tmp}/flowmobile-install-$$"
ARCHIVE="$WORK_DIR/flowmobile.tar.gz"
BACKUP_DIR="$WORK_DIR/previous"
SHARED_DOWNLOAD_ROOT="$HOME/storage/downloads"
PUBLIC_DOWNLOAD_DIR="$SHARED_DOWNLOAD_ROOT/FlowMobile"
OLD_BACKED_UP=0
NEW_INSTALLED=0

finish_installation() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$status" -ne 0 ]; then
        if [ "$NEW_INSTALLED" -eq 1 ]; then rm -rf "$APP_DIR"; fi
        if [ "$OLD_BACKED_UP" -eq 1 ] && [ -d "$BACKUP_DIR" ]; then
            mv "$BACKUP_DIR" "$APP_DIR"
            echo "La actualización falló; se restauró la versión anterior."
        fi
    fi
    rm -rf "$WORK_DIR"
    exit "$status"
}
trap finish_installation EXIT
trap 'exit 1' HUP INT TERM

echo "Preparando Termux…"
pkg update -y
pkg install -y python python-pip ffmpeg curl

shared_storage_ready() {
    probe="$SHARED_DOWNLOAD_ROOT/.flowmobile-write-test-$$"
    [ -d "$SHARED_DOWNLOAD_ROOT" ] || return 1
    if (umask 077; : > "$probe") 2>/dev/null; then
        rm -f "$probe"
        return 0
    fi
    rm -f "$probe"
    return 1
}

if ! shared_storage_ready; then
    echo "Android solicitará permiso para acceder a Descargas."
    termux-setup-storage || true
fi

attempt=0
while ! shared_storage_ready && [ "$attempt" -lt 15 ]; do
    sleep 1
    attempt=$((attempt + 1))
done
if ! shared_storage_ready; then
    echo "FlowMobile necesita acceso a Descargas para no ocultar los archivos."
    echo "Concede el permiso de archivos a Termux, ejecuta termux-setup-storage y repite la instalación."
    exit 1
fi
mkdir -p "$PUBLIC_DOWNLOAD_DIR/Videos" "$PUBLIC_DOWNLOAD_DIR/Audio" "$PUBLIC_DOWNLOAD_DIR/Lotes"

echo "Instalando FlowMobile para Termux…"
mkdir -p "$WORK_DIR" "$BIN_DIR"
cd "$HOME"
if ! curl -fL "https://github.com/$REPOSITORY/archive/refs/heads/$BRANCH.tar.gz" -o "$ARCHIVE"; then
    curl -fL "https://github.com/$REPOSITORY/archive/refs/tags/$BRANCH.tar.gz" -o "$ARCHIVE"
fi
tar -xzf "$ARCHIVE" -C "$WORK_DIR"

SOURCE_DIR=""
for candidate in "$WORK_DIR"/*; do
    if [ -d "$candidate/flow" ] && [ -f "$candidate/main.py" ]; then
        SOURCE_DIR="$candidate"
        break
    fi
done
[ -n "$SOURCE_DIR" ] || { echo "El paquete de FlowMobile no es válido."; exit 1; }

EXISTING_DIR=""
if [ -d "$APP_DIR" ]; then
    EXISTING_DIR="$APP_DIR"
else
    for legacy in "$HOME/FlowIOS" "$HOME/FlowApp"; do
        if [ -d "$legacy" ]; then EXISTING_DIR="$legacy"; break; fi
    done
fi
if [ -n "$EXISTING_DIR" ]; then
    mv "$EXISTING_DIR" "$BACKUP_DIR"
    OLD_BACKED_UP=1
fi
mv "$SOURCE_DIR" "$APP_DIR"
NEW_INSTALLED=1

restore_saved_item() {
    source=$1
    destination=$2
    if [ -d "$source" ]; then
        mkdir -p "$destination"
        cp -R "$source/." "$destination/"
    elif [ -f "$source" ]; then
        cp "$source" "$destination"
    fi
}

for saved in "$DATA_BACKUP_DIR" "$BACKUP_DIR"; do
    if [ -d "$saved/Downloads" ]; then
        echo "Migrando descargas anteriores a Android/Download/FlowMobile…"
        restore_saved_item "$saved/Downloads" "$PUBLIC_DOWNLOAD_DIR"
    fi
    for item in .flowmobile flow_settings.json; do
        if [ -e "$saved/$item" ]; then restore_saved_item "$saved/$item" "$APP_DIR/$item"; fi
    done
done

printf '%s\n' "$REPOSITORY" > "$APP_DIR/.flowmobile-source"
cp "$APP_DIR/scripts/flow" "$BIN_DIR/flow"
chmod +x "$BIN_DIR/flow"
python3 -m pip install --disable-pip-version-check --upgrade "yt-dlp[default]"
[ -f "$APP_DIR/main.py" ] && [ -d "$APP_DIR/flow" ] && [ -f "$APP_DIR/VERSION" ]
rm -rf "$DATA_BACKUP_DIR"

echo "FlowMobile instalado para Android."
echo "Descargas públicas: $PUBLIC_DOWNLOAD_DIR"
echo "Escribe: flow"
