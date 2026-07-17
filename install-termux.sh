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
LOG_FILE="${FLOWMOBILE_INSTALL_LOG:-$HOME/.flowmobile-install.log}"
COMMAND_LOG="$LOG_FILE.command-$$"
VERBOSE="${FLOWMOBILE_VERBOSE:-0}"
CURRENT_STAGE="Preparando"
CURRENT_CODE="FM-TERMUX-INSTALL"
STEP_NUMBER=0
FAILURE_REPORTED=0

umask 077
if ! : 2>/dev/null > "$LOG_FILE"; then
    echo "✕ Termux no pudo crear el registro privado." >&2
    echo "Código: FM-TERMUX-PERMISSION" >&2
    echo "Causa: no se puede escribir en $LOG_FILE" >&2
    echo "Solución: revisa el espacio y los permisos de Termux." >&2
    exit 1
fi
chmod 600 "$LOG_FILE" 2>/dev/null || true
printf '%s\n' "FlowMobile installer log" >> "$LOG_FILE"
exec 3>&2
exec 2>> "$LOG_FILE"

step_start() {
    STEP_NUMBER=$((STEP_NUMBER + 1))
    CURRENT_STAGE=$1
    CURRENT_CODE=$2
    printf '[%s/6] %s…\n' "$STEP_NUMBER" "$CURRENT_STAGE"
    printf '\n== %s ==\n' "$CURRENT_STAGE" >> "$LOG_FILE"
}

step_done() {
    if [ -n "${1:-}" ]; then
        printf '      ✓ Listo · %s\n' "$1"
    else
        echo "      ✓ Listo"
    fi
}

run_logged() {
    : > "$COMMAND_LOG"
    printf '+ %s\n' "$*" >> "$LOG_FILE"
    if "$@" > "$COMMAND_LOG" 2>&1; then
        status=0
    else
        status=$?
    fi
    cat "$COMMAND_LOG" >> "$LOG_FILE"
    if [ "$VERBOSE" = "1" ]; then cat "$COMMAND_LOG"; fi
    rm -f "$COMMAND_LOG"
    return "$status"
}

run_network() {
    if run_logged "$@"; then return 0; else status=$?; fi
    if ! tail -n 30 "$LOG_FILE" | grep -Eqi \
        'Could not resolve|Name or service not known|Connection timed out|Failed to connect|Network is unreachable|Temporary failure|Too Many Requests|HTTP[^0-9]*429|HTTP[^0-9]*50[0-9]'; then
        return "$status"
    fi
    echo "      • La red falló; reintentando una vez…"
    sleep 1
    run_logged "$@"
}

last_log_line() {
    awk 'NF {line=$0} END {if (line) print substr(line, 1, 300)}' "$LOG_FILE"
}

report_failure() {
    status=${1:-1}
    code=$CURRENT_CODE
    cause="La instalación falló durante «$CURRENT_STAGE»."
    hint="Consulta el registro y repite el comando de instalación."
    if grep -Eqi 'No space left|not enough space|ENOSPC' "$LOG_FILE"; then
        code="FM-TERMUX-SPACE"
        cause="No queda espacio suficiente en el dispositivo."
        hint="Libera espacio en Android y vuelve a ejecutar el instalador."
    elif grep -Eqi 'requested URL returned error: 404|HTTP[^0-9]*404' "$LOG_FILE"; then
        code="FM-TERMUX-HTTP-404"
        cause="GitHub no encontró uno de los archivos del release."
        hint="Confirma que exista una versión estable o espera unos minutos y repite."
    elif grep -Eqi 'requested URL returned error: 403|HTTP[^0-9]*403' "$LOG_FILE"; then
        code="FM-TERMUX-HTTP-403"
        cause="GitHub rechazó temporalmente la descarga."
        hint="Cambia de red o espera unos minutos antes de repetir."
    elif grep -Eqi 'requested URL returned error: 429|HTTP[^0-9]*429|Too Many Requests' "$LOG_FILE"; then
        code="FM-TERMUX-HTTP-429"
        cause="GitHub limitó temporalmente las descargas."
        hint="Espera unos minutos o cambia de red antes de repetir."
    elif grep -Eqi 'Could not resolve|Name or service not known|Connection timed out|Failed to connect|Network is unreachable' "$LOG_FILE"; then
        code="FM-TERMUX-NETWORK"
        cause="Termux no pudo conectarse a internet."
        hint="Comprueba Wi-Fi, datos, DNS o VPN y repite el mismo comando."
    elif grep -Eqi 'THESE PACKAGES DO NOT MATCH THE HASHES|HashMismatch|hashes.*do not match' "$LOG_FILE"; then
        code="FM-TERMUX-INTEGRITY"
        cause="Una dependencia no coincide con su hash de seguridad."
        hint="No fuerces la instalación; vuelve a copiar el enlace del repositorio oficial."
    elif grep -Eqi 'incompleto o dañado|not a gzip file|Unexpected EOF|unexpected end of file' "$LOG_FILE"; then
        code="FM-TERMUX-ARCHIVE"
        cause="El paquete descargado está incompleto o dañado."
        hint="Repite la instalación con una conexión estable."
    elif [ "$CURRENT_CODE" = "FM-TERMUX-PKG" ]; then
        cause="Termux no pudo preparar Python, FFmpeg o sus herramientas."
        hint="Ejecuta termux-change-repo, elige otro servidor y repite la instalación."
    elif [ "$CURRENT_CODE" = "FM-TERMUX-PIP" ]; then
        cause="pip no pudo instalar yt-dlp y EJS."
        hint="Actualiza Termux, comprueba internet y repite la instalación."
    elif [ "$CURRENT_CODE" = "FM-TERMUX-STORAGE" ]; then
        cause="Android no concedió acceso al almacenamiento compartido."
        hint="Concede Archivos y contenido multimedia a Termux y ejecuta termux-setup-storage."
    elif [ "$CURRENT_CODE" = "FM-TERMUX-INTEGRITY" ]; then
        cause="La verificación de seguridad no coincide."
        hint="No omitas esta comprobación; reinstala desde el repositorio oficial."
    elif [ "$CURRENT_CODE" = "FM-TERMUX-DOWNLOAD" ]; then
        cause="No se pudo descargar el release oficial de GitHub."
        hint="Comprueba internet o espera unos minutos si GitHub está limitando descargas."
    elif [ "$CURRENT_CODE" = "FM-TERMUX-LAUNCHER" ]; then
        cause="No se pudo registrar el comando flow."
        hint="Cierra Termux, ábrelo de nuevo y repite la instalación."
    elif grep -Eqi 'Permission denied|Operation not permitted' "$LOG_FILE"; then
        code="FM-TERMUX-PERMISSION"
        cause="Termux no tiene permiso para escribir uno de los archivos."
        hint="Revisa los permisos de Termux y vuelve a ejecutar el instalador."
    fi
    detail=$(last_log_line)
    [ -n "$detail" ] || detail="El comando terminó con código $status"
    printf '\n✕ Instalación detenida en: %s\n' "$CURRENT_STAGE" >&3
    printf 'Código: %s\n' "$code" >&3
    printf 'Causa: %s\n' "$cause" >&3
    printf 'Detalle: %s\n' "$detail" >&3
    printf 'Solución: %s\n' "$hint" >&3
    printf 'Registro completo: %s\n' "$LOG_FILE" >&3
    printf 'Para verlo: cat %s\n' "$LOG_FILE" >&3
    FAILURE_REPORTED=1
}

fail_install() {
    status=${1:-1}
    report_failure "$status"
    exit "$status"
}

finish_installation() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$status" -ne 0 ]; then
        if [ "$NEW_INSTALLED" -eq 1 ]; then rm -rf "$APP_DIR"; fi
        if [ "$OLD_BACKED_UP" -eq 1 ] && [ -d "$BACKUP_DIR" ]; then
            mv "$BACKUP_DIR" "$APP_DIR"
            echo "La actualización falló; se restauró la versión anterior."
        fi
        if [ "$FAILURE_REPORTED" -eq 0 ]; then report_failure "$status"; fi
    fi
    rm -rf "$WORK_DIR"
    rm -f "$COMMAND_LOG"
    exit "$status"
}
trap finish_installation EXIT
trap 'exit 1' HUP INT TERM

echo
echo "FlowMobile · Instalación para Termux"
echo "La salida técnica se guardará en un registro privado."
echo

step_start "Preparando" "FM-TERMUX-PREPARE"
mkdir -p "$WORK_DIR" "$BIN_DIR"
step_done "entorno listo"

step_start "Dependencias" "FM-TERMUX-PKG"
run_network pkg update -y || fail_install $?
run_network pkg install -y python python-pip ffmpeg curl termux-tools || fail_install $?

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
    run_logged termux-setup-storage || true
fi

attempt=0
while ! shared_storage_ready && [ "$attempt" -lt 15 ]; do
    sleep 1
    attempt=$((attempt + 1))
done
if ! shared_storage_ready; then
    CURRENT_CODE="FM-TERMUX-STORAGE"
    printf '%s\n' "Android no concedió acceso a $SHARED_DOWNLOAD_ROOT" >> "$LOG_FILE"
    fail_install 1
fi
mkdir -p "$PUBLIC_DOWNLOAD_DIR/Lotes" "$PUBLIC_VIDEO_DIR/Lotes" "$PUBLIC_AUDIO_DIR/Lotes"
step_done "Python, FFmpeg y almacenamiento"

step_start "Descargando" "FM-TERMUX-DOWNLOAD"
cd "$HOME"
case "$BRANCH" in
    v[0-9]*|[0-9]*) ;;
    *)
        if [ "${FLOWMOBILE_ALLOW_UNVERIFIED:-0}" != "1" ]; then
            echo "Seguridad: solo se permiten releases estables verificados."
            exit 1
        fi
        echo "Aviso: instalación de desarrollo sin verificación de release."
        run_network curl -fsSL --connect-timeout 15 --max-time 180 \
            "https://github.com/$REPOSITORY/archive/refs/heads/$BRANCH.tar.gz" -o "$ARCHIVE" || fail_install $?
        ;;
esac
if [ ! -s "$ARCHIVE" ]; then
    VERSION=${BRANCH#v}
    ASSET="FlowMobile-$VERSION.tar.gz"
    RELEASE_URL="https://github.com/$REPOSITORY/releases/download/$BRANCH"
    run_network curl -fsSL --connect-timeout 15 --max-time 180 \
        "$RELEASE_URL/SHA256SUMS" -o "$CHECKSUMS" || fail_install $?
    run_network curl -fsSL --connect-timeout 15 --max-time 180 \
        "$RELEASE_URL/$ASSET" -o "$ARCHIVE" || fail_install $?
    step_done "release oficial"

    step_start "Verificando" "FM-TERMUX-INTEGRITY"
    EXPECTED=$(awk -v file="$ASSET" '$2 == file || $2 == "*" file {print $1; exit}' "$CHECKSUMS")
    ACTUAL=$(sha256sum "$ARCHIVE" | awk '{print $1}')
    ACTUAL=${ACTUAL#\\}
    [ -n "$EXPECTED" ] && [ "$ACTUAL" = "$EXPECTED" ] || {
        printf 'SHA esperado: %s\nSHA obtenido: %s\n' "$EXPECTED" "$ACTUAL" >> "$LOG_FILE"
        printf '%s\n' "El paquete no coincide con el SHA-256 oficial." >> "$LOG_FILE"
        fail_install 1
    }
fi
if [ "$STEP_NUMBER" -eq 3 ]; then
    step_done "archivo descargado"
    step_start "Verificando" "FM-TERMUX-INTEGRITY"
fi
TAR_LIST="$WORK_DIR/archive.list"
if ! tar -tzf "$ARCHIVE" > "$TAR_LIST"; then
    printf '%s\n' "El paquete descargado está incompleto o dañado." >> "$LOG_FILE"
    fail_install 1
fi
awk '
    /^\// || /(^|\/)\.\.($|\/)/ { unsafe=1 }
    END { exit unsafe ? 1 : 0 }
' "$TAR_LIST" >> "$LOG_FILE" 2>&1 || { printf '%s\n' "El paquete contiene rutas no seguras." >> "$LOG_FILE"; fail_install 1; }
run_logged tar -xzf "$ARCHIVE" -C "$WORK_DIR" || fail_install $?

SOURCE_DIR=""
for candidate in "$WORK_DIR"/*; do
    if [ -d "$candidate/flow" ] && [ -f "$candidate/main.py" ]; then
        SOURCE_DIR="$candidate"
        break
    fi
done
[ -n "$SOURCE_DIR" ] || { printf '%s\n' "El paquete de FlowMobile no es válido." >> "$LOG_FILE"; fail_install 1; }
run_logged python3 "$SOURCE_DIR/scripts/security_manifest.py" --check "$SOURCE_DIR" || {
    printf '%s\n' "El código instalado no coincide con el manifiesto oficial." >> "$LOG_FILE"
    fail_install 1
}
VERSION=$(tr -d '\r\n' < "$SOURCE_DIR/VERSION")
step_done "SHA-256 · v$VERSION"

step_start "Instalando" "FM-TERMUX-INSTALL"

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
CURRENT_CODE="FM-TERMUX-PIP"
run_network python3 -m pip install --disable-pip-version-check --require-hashes \
    --only-binary=:all: --no-deps --upgrade --quiet --progress-bar=off \
    --retries 1 --timeout 30 -r "$APP_DIR/requirements.lock" || fail_install $?
CURRENT_CODE="FM-TERMUX-INSTALL"
[ -f "$APP_DIR/main.py" ] && [ -d "$APP_DIR/flow" ] && [ -f "$APP_DIR/VERSION" ] || fail_install 1
step_done "aplicación y datos preparados"

step_start "Activando flow" "FM-TERMUX-LAUNCHER"
run_logged cp "$APP_DIR/scripts/flow" "$BIN_DIR/flow" || fail_install $?
run_logged chmod +x "$BIN_DIR/flow" || fail_install $?
[ -x "$BIN_DIR/flow" ] || fail_install 1
step_done "comando registrado"
rm -rf "$DATA_BACKUP_DIR"

echo
echo "✓ FlowMobile $VERSION instalado correctamente."
echo "Abre ahora con: flow"
echo "Videos para la galería: $PUBLIC_VIDEO_DIR"
echo "Audios: $PUBLIC_AUDIO_DIR"
echo "Registro: $LOG_FILE"
