#!/bin/sh
set -eu

REPOSITORY="${1:-${FLOWMOBILE_REPOSITORY:-tacosandtypescript-debug/FlowMobile}}"
BRANCH="${FLOWMOBILE_BRANCH:-main}"
APP_DIR="${FLOWMOBILE_HOME:-$HOME/FlowMobile}"
DATA_BACKUP_DIR="$(dirname "$APP_DIR")/.flowmobile-data"
BIN_DIR="${PREFIX:-$HOME/../usr}/bin"
WORK_DIR="${TMPDIR:-${PREFIX:-$HOME/../usr}/tmp}/flowmobile-install-$$"
ARCHIVE="$WORK_DIR/flowmobile.tar.gz"
CHECKSUMS="$WORK_DIR/SHA256SUMS"
BACKUP_DIR="$WORK_DIR/previous"
SHARED_DOWNLOAD_ROOT="$HOME/storage/downloads"
SHARED_MOVIE_ROOT="$HOME/storage/movies"
SHARED_MUSIC_ROOT="$HOME/storage/music"
PUBLIC_DOWNLOAD_DIR="$SHARED_DOWNLOAD_ROOT/FlowMobile"
PUBLIC_VIDEO_DIR="$SHARED_MOVIE_ROOT/FlowMobile"
PUBLIC_AUDIO_DIR="$SHARED_MUSIC_ROOT/FlowMobile"
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
pkg install -y python python-pip ffmpeg curl termux-tools

directory_ready() {
    directory=$1
    probe="$directory/.flowmobile-write-test-$$"
    [ -d "$directory" ] || return 1
    if (umask 077; : > "$probe") 2>/dev/null; then
        rm -f "$probe"
        return 0
    fi
    rm -f "$probe"
    return 1
}

shared_storage_ready() {
    directory_ready "$SHARED_DOWNLOAD_ROOT" &&
        directory_ready "$SHARED_MOVIE_ROOT" &&
        directory_ready "$SHARED_MUSIC_ROOT"
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
mkdir -p "$PUBLIC_DOWNLOAD_DIR/Lotes" "$PUBLIC_VIDEO_DIR/Lotes" "$PUBLIC_AUDIO_DIR/Lotes"

echo "Instalando FlowMobile para Termux…"
mkdir -p "$WORK_DIR" "$BIN_DIR"
cd "$HOME"
case "$BRANCH" in
    v[0-9]*|[0-9]*) ;;
    *)
        if [ "${FLOWMOBILE_ALLOW_UNVERIFIED:-0}" != "1" ]; then
            echo "Seguridad: solo se permiten releases estables verificados."
            exit 1
        fi
        echo "Aviso: instalación de desarrollo sin verificación de release."
        curl -fL "https://github.com/$REPOSITORY/archive/refs/heads/$BRANCH.tar.gz" -o "$ARCHIVE"
        ;;
esac
if [ ! -s "$ARCHIVE" ]; then
    VERSION=${BRANCH#v}
    ASSET="FlowMobile-$VERSION.tar.gz"
    RELEASE_URL="https://github.com/$REPOSITORY/releases/download/$BRANCH"
    curl -fL "$RELEASE_URL/SHA256SUMS" -o "$CHECKSUMS"
    curl -fL "$RELEASE_URL/$ASSET" -o "$ARCHIVE"
    EXPECTED=$(awk -v file="$ASSET" '$2 == file || $2 == "*" file {print $1; exit}' "$CHECKSUMS")
    ACTUAL=$(sha256sum "$ARCHIVE" | awk '{print $1}')
    [ -n "$EXPECTED" ] && [ "$ACTUAL" = "$EXPECTED" ] || {
        echo "Seguridad: el paquete no coincide con el SHA-256 oficial."
        exit 1
    }
    echo "SHA-256 del release: verificado."
fi
tar -tzf "$ARCHIVE" | awk '
    /^\// || /(^|\/)\.\.($|\/)/ { unsafe=1 }
    END { exit unsafe ? 1 : 0 }
' || { echo "Seguridad: el paquete contiene rutas no seguras."; exit 1; }
tar -xzf "$ARCHIVE" -C "$WORK_DIR"

SOURCE_DIR=""
for candidate in "$WORK_DIR"/*; do
    if [ -d "$candidate/flow" ] && [ -f "$candidate/main.py" ]; then
        SOURCE_DIR="$candidate"
        break
    fi
done
[ -n "$SOURCE_DIR" ] || { echo "El paquete de FlowMobile no es válido."; exit 1; }
python3 "$SOURCE_DIR/scripts/security_manifest.py" --check "$SOURCE_DIR" || {
    echo "Seguridad: el código instalado no coincide con el manifiesto oficial."
    exit 1
}

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

move_saved_media() {
    source=$1
    destination=$2
    [ -d "$source" ] || return 0
    mkdir -p "$destination"
    for media in "$source"/*; do
        [ -e "$media" ] || continue
        name=$(basename "$media")
        if [ -e "$destination/$name" ]; then
            echo "Se conservó un archivo repetido en: $media"
        else
            mv "$media" "$destination/$name"
        fi
    done
    rmdir "$source" 2>/dev/null || true
}

migrate_saved_downloads() {
    source=$1
    [ -d "$source" ] || return 0
    restore_saved_item "$source/Videos" "$PUBLIC_VIDEO_DIR"
    restore_saved_item "$source/Audio" "$PUBLIC_AUDIO_DIR"
    restore_saved_item "$source/Lotes" "$PUBLIC_DOWNLOAD_DIR/Lotes"
    for item in "$source"/*; do
        [ -e "$item" ] || continue
        name=$(basename "$item")
        case "$name" in Videos|Audio|Lotes) continue ;; esac
        restore_saved_item "$item" "$PUBLIC_DOWNLOAD_DIR/$name"
    done
}

# La 7.6.7 guardaba estos archivos en Download; se recolocan sin duplicarlos.
move_saved_media "$PUBLIC_DOWNLOAD_DIR/Videos" "$PUBLIC_VIDEO_DIR"
move_saved_media "$PUBLIC_DOWNLOAD_DIR/Audio" "$PUBLIC_AUDIO_DIR"

for saved in "$DATA_BACKUP_DIR" "$BACKUP_DIR"; do
    if [ -d "$saved/Downloads" ]; then
        echo "Migrando descargas anteriores a las carpetas multimedia de Android…"
        migrate_saved_downloads "$saved/Downloads"
    fi
    for item in .flowmobile flow_settings.json; do
        if [ -e "$saved/$item" ]; then restore_saved_item "$saved/$item" "$APP_DIR/$item"; fi
    done
done

printf '%s\n' "$REPOSITORY" > "$APP_DIR/.flowmobile-source"
cp "$APP_DIR/scripts/flow" "$BIN_DIR/flow"
chmod +x "$BIN_DIR/flow"
python3 -m pip install --disable-pip-version-check --require-hashes \
    --only-binary=:all: --no-deps --upgrade -r "$APP_DIR/requirements.lock"
[ -f "$APP_DIR/main.py" ] && [ -d "$APP_DIR/flow" ] && [ -f "$APP_DIR/VERSION" ]
rm -rf "$DATA_BACKUP_DIR"

echo "FlowMobile instalado para Android."
echo "Videos para la galería: $PUBLIC_VIDEO_DIR"
echo "Audios: $PUBLIC_AUDIO_DIR"
echo "Escribe: flow"
