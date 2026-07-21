#!/bin/sh
set -u

REPOSITORY=${1:-tacosandtypescript-debug/FlowMobile}
LOG_FILE=${FLOWMOBILE_INSTALL_LOG:-$HOME/.flowmobile-install.log}
APP_DIR=${FLOWMOBILE_HOME:-$HOME/.local/share/flowmobile}
BIN_DIR=${FLOWMOBILE_BIN:-$HOME/.local/bin}
DOWNLOAD_ROOT=${FLOWMOBILE_DOWNLOADS:-${XDG_DOWNLOAD_DIR:-}}
if [ -z "$DOWNLOAD_ROOT" ] && [ -f "$HOME/.config/user-dirs.dirs" ]; then
    DOWNLOAD_ROOT=$(sed -n 's/^XDG_DOWNLOAD_DIR="\(.*\)"/\1/p' "$HOME/.config/user-dirs.dirs" | head -n 1)
fi
[ -n "$DOWNLOAD_ROOT" ] || DOWNLOAD_ROOT="$HOME/Downloads"
case "$DOWNLOAD_ROOT" in '$HOME'/*) DOWNLOAD_ROOT="$HOME/${DOWNLOAD_ROOT#\$HOME/}" ;; esac
BACKUP_DIR="$APP_DIR.rollback"
PRESERVED_DIR="$(dirname "$APP_DIR")/.flowmobile-data"
WORK_DIR="${TMPDIR:-/tmp}/flowmobile-linux-$$"
VERBOSE=${FLOWMOBILE_VERBOSE:-0}
CURRENT_STAGE=Preparando
CURRENT_CODE=FM-LINUX-INSTALL
FAILURE_REPORTED=0
STEP=0

umask 077
if ! : > "$LOG_FILE" 2>/dev/null; then
    echo "✕ No se pudo crear el registro privado: $LOG_FILE" >&2
    exit 1
fi
chmod 600 "$LOG_FILE" 2>/dev/null || true
exec 3>&2 2>>"$LOG_FILE"

print_step() {
    STEP=$((STEP + 1))
    CURRENT_STAGE=$1
    CURRENT_CODE=$2
    printf '\n[%s/6] %s…\n' "$STEP" "$CURRENT_STAGE"
    printf '\n== %s ==\n' "$CURRENT_STAGE" >> "$LOG_FILE"
}

step_done() { printf '      ✓ Listo · %s\n' "$1"; }

run_logged() {
    printf '+ ' >> "$LOG_FILE"
    printf '%s ' "$@" >> "$LOG_FILE"
    printf '\n' >> "$LOG_FILE"
    command_log="$WORK_DIR/command.log"
    "$@" > "$command_log" 2>&1
    status=$?
    cat "$command_log" >> "$LOG_FILE"
    if [ "$VERBOSE" = 1 ]; then cat "$command_log" >&3; fi
    rm -f "$command_log"
    return "$status"
}

last_error() {
    tail -n 25 "$LOG_FILE" | sed '/^[[:space:]]*$/d' | tail -n 1
}

report_failure() {
    status=${1:-1}
    [ "$FAILURE_REPORTED" = 0 ] || return "$status"
    FAILURE_REPORTED=1
    detail=$(last_error)
    cause="La operación no terminó correctamente."
    hint="Revisa el registro y repite la instalación."
    code=$CURRENT_CODE
    case "$detail" in
        *"No space left"*|*"espacio insuficiente"*)
            code=FM-LINUX-SPACE; cause="No hay espacio suficiente."; hint="Libera espacio en tu carpeta personal y repite." ;;
        *"Could not resolve"*|*"Temporary failure"*|*"Connection timed out"*)
            code=FM-LINUX-NETWORK; cause="Linux no pudo conectarse a GitHub."; hint="Comprueba internet, DNS o VPN y repite." ;;
        *"404"*) code=FM-LINUX-HTTP-404; cause="GitHub no encontró el release solicitado."; hint="Comprueba que la versión esté publicada." ;;
        *"429"*) code=FM-LINUX-HTTP-429; cause="GitHub limitó temporalmente las solicitudes."; hint="Espera unos minutos y repite." ;;
        *"hash"*|*"SHA-256"*|*"checksum"*)
            code=FM-LINUX-INTEGRITY; cause="El archivo descargado no coincide con su SHA-256."; hint="No lo ejecutes; cambia de red y vuelve a descargar." ;;
        *"Permission denied"*|*"permiso denegado"*)
            code=FM-LINUX-PERMISSION; cause="Linux rechazó un permiso de escritura."; hint="Comprueba permisos de HOME y evita ejecutar como otro usuario." ;;
        *"pip"*|*"No matching distribution"*)
            code=FM-LINUX-PIP; cause="Python no pudo preparar yt-dlp y EJS."; hint="Actualiza Python/pip y repite." ;;
    esac
    printf '\n✕ Instalación detenida en: %s\n' "$CURRENT_STAGE" >&3
    printf 'Código: %s\nCausa: %s\n' "$code" "$cause" >&3
    printf 'Detalle: %s\nSolución: %s\n' "${detail:-código $status}" "$hint" >&3
    printf 'Registro completo: %s\nPara verlo: cat %s\n' "$LOG_FILE" "$LOG_FILE" >&3
    return "$status"
}

cleanup() { rm -rf "$WORK_DIR" 2>/dev/null || true; }

rollback() {
    if [ -d "$BACKUP_DIR" ]; then
        rm -rf "$APP_DIR" 2>/dev/null || true
        mv "$BACKUP_DIR" "$APP_DIR" 2>/dev/null || true
        printf 'Se restauró la versión anterior.\n' >&3
    fi
}

finish() {
    status=$?
    if [ "$status" -ne 0 ]; then rollback; report_failure "$status" || true; fi
    cleanup
    exit "$status"
}
trap finish EXIT HUP INT TERM

fail() { return "${1:-1}"; }

run_network() {
    run_logged "$@" && return 0
    recent=$(tail -n 12 "$LOG_FILE")
    case "$recent" in
        *"Could not resolve"*|*"Temporary failure"*|*"Connection timed out"*|*"429"*|*" 5"??*)
            printf '      Red temporal; reintentando una vez…\n'
            sleep 1
            run_logged "$@"
            return $?
            ;;
    esac
    return 1
}

as_root() {
    if [ "$(id -u)" = 0 ]; then run_logged "$@"; return $?; fi
    if command -v sudo >/dev/null 2>&1; then run_logged sudo "$@"; return $?; fi
    echo "Se necesita sudo para instalar dependencias del sistema." >> "$LOG_FILE"
    return 1
}

install_dependencies() {
    command -v python3 >/dev/null 2>&1 && command -v ffmpeg >/dev/null 2>&1 && \
        command -v ffprobe >/dev/null 2>&1 && command -v curl >/dev/null 2>&1 && return 0
    if command -v apt-get >/dev/null 2>&1; then
        as_root apt-get update -y && as_root apt-get install -y python3 python3-venv python3-pip ffmpeg curl ca-certificates
    elif command -v dnf >/dev/null 2>&1; then
        as_root dnf install -y python3 python3-pip ffmpeg curl ca-certificates || \
            as_root dnf install -y python3 python3-pip ffmpeg-free curl ca-certificates
    elif command -v pacman >/dev/null 2>&1; then
        as_root pacman -Sy --needed --noconfirm python python-pip ffmpeg curl ca-certificates
    elif command -v zypper >/dev/null 2>&1; then
        as_root zypper --non-interactive install python3 python3-pip ffmpeg curl ca-certificates
    else
        echo "No se reconoció apt, dnf, pacman ni zypper." >> "$LOG_FILE"
        return 1
    fi
}

echo ""
echo "FlowMobile · Instalación para Linux"
echo "La salida técnica se guardará en un registro privado."

print_step Preparando FM-LINUX-PREPARE
case "$REPOSITORY" in
    *[!A-Za-z0-9_.\/-]*|/*|*/|*/*/*) echo "Repositorio inválido: $REPOSITORY" >> "$LOG_FILE"; fail 1; exit $? ;;
esac
case "$REPOSITORY" in
    */*) ;;
    *) echo "Repositorio inválido: $REPOSITORY" >> "$LOG_FILE"; fail 1; exit $? ;;
esac
mkdir -p "$WORK_DIR" "$BIN_DIR" "$(dirname "$APP_DIR")" || { fail 1; exit $?; }
step_done "entorno Linux"

print_step Dependencias FM-LINUX-PKG
install_dependencies || { fail 1; exit $?; }
python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >> "$LOG_FILE" 2>&1 || {
    echo "FlowMobile requiere Python 3.10 o posterior." >> "$LOG_FILE"; fail 1; exit $?;
}
step_done "Python y FFmpeg"

print_step Descargando FM-LINUX-DOWNLOAD
REFERENCE=${FLOWMOBILE_BRANCH:-}
if [ -z "$REFERENCE" ]; then
    API="$WORK_DIR/latest.json"
    run_network curl -fsSL --connect-timeout 15 --max-time 60 \
        "https://api.github.com/repos/$REPOSITORY/releases/latest" -o "$API" || { fail 1; exit $?; }
    REFERENCE=$(sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$API" | head -n 1)
fi
SAFE_REFERENCE=$(printf '%s\n' "$REFERENCE" | sed -n '/^v\{0,1\}[0-9][0-9]*\(\.[0-9][0-9]*\)\{1,3\}$/p')
[ "$SAFE_REFERENCE" = "$REFERENCE" ] || { echo "Release estable inválido: $REFERENCE" >> "$LOG_FILE"; fail 1; exit $?; }
VERSION=${REFERENCE#v}
BASE_URL="https://github.com/$REPOSITORY/releases/download/$REFERENCE"
ARCHIVE="$WORK_DIR/FlowMobile-$VERSION.tar.gz"
run_network curl -fsSL --connect-timeout 15 --max-time 180 "$BASE_URL/SHA256SUMS" -o "$WORK_DIR/SHA256SUMS" || { fail 1; exit $?; }
run_network curl -fsSL --connect-timeout 15 --max-time 300 "$BASE_URL/FlowMobile-$VERSION.tar.gz" -o "$ARCHIVE" || { fail 1; exit $?; }
step_done "release oficial v$VERSION"

print_step Verificando FM-LINUX-INTEGRITY
EXPECTED=$(awk -v name="FlowMobile-$VERSION.tar.gz" '$2 == name || $2 == "*" name {print $1; exit}' "$WORK_DIR/SHA256SUMS")
if command -v sha256sum >/dev/null 2>&1; then ACTUAL=$(sha256sum "$ARCHIVE" | awk '{print $1}'); else ACTUAL=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}'); fi
[ -n "$EXPECTED" ] && [ "$EXPECTED" = "$ACTUAL" ] || { echo "SHA-256 incorrecto: esperado $EXPECTED, obtenido $ACTUAL" >> "$LOG_FILE"; fail 1; exit $?; }
LISTING=$(tar -tzf "$ARCHIVE") || { echo "Paquete tar corrupto" >> "$LOG_FILE"; fail 1; exit $?; }
echo "$LISTING" | while IFS= read -r name; do case "$name" in /*|*../*) exit 9 ;; esac; done
[ "$?" -eq 0 ] || { echo "Paquete con ruta insegura" >> "$LOG_FILE"; fail 1; exit $?; }
run_logged tar -xzf "$ARCHIVE" -C "$WORK_DIR" || { fail 1; exit $?; }
SOURCE="$WORK_DIR/FlowMobile-$VERSION"
[ -f "$SOURCE/main.py" ] && [ -d "$SOURCE/flow" ] && [ -f "$SOURCE/SECURITY_MANIFEST.sha256" ] || { echo "Paquete incompleto" >> "$LOG_FILE"; fail 1; exit $?; }
run_logged python3 "$SOURCE/scripts/security_manifest.py" --check "$SOURCE" || { fail 1; exit $?; }
step_done "SHA-256 y manifiesto"

print_step Instalando FM-LINUX-PIP
rm -rf "$BACKUP_DIR"
if [ -d "$APP_DIR" ]; then mv "$APP_DIR" "$BACKUP_DIR" || { fail 1; exit $?; }; fi
mv "$SOURCE" "$APP_DIR" || { fail 1; exit $?; }
for item in .flowmobile flow_settings.json Downloads; do
    if [ -e "$BACKUP_DIR/$item" ]; then
        cp -R "$BACKUP_DIR/$item" "$APP_DIR/$item" || { fail 1; exit $?; }
    elif [ -e "$PRESERVED_DIR/$item" ]; then
        cp -R "$PRESERVED_DIR/$item" "$APP_DIR/$item" || { fail 1; exit $?; }
    fi
done
printf '%s\n' "$REPOSITORY" > "$APP_DIR/.flowmobile-source"
run_logged python3 -m venv "$APP_DIR/.venv" || { fail 1; exit $?; }
run_network "$APP_DIR/.venv/bin/python" -m pip install --disable-pip-version-check \
    --require-hashes --only-binary=:all: --no-deps --upgrade --quiet --progress-bar=off \
    --retries 1 --timeout 30 -r "$APP_DIR/requirements.lock" || { fail 1; exit $?; }
run_logged "$APP_DIR/.venv/bin/python" -c "import sys; sys.path.insert(0, '$APP_DIR'); import yt_dlp; from flow import APP_VERSION; assert APP_VERSION == '$VERSION'" || { fail 1; exit $?; }
step_done "aplicación y dependencias"

print_step "Activando flow" FM-LINUX-LAUNCHER
cat > "$BIN_DIR/flow" <<EOF
#!/bin/sh
exec "$APP_DIR/.venv/bin/python" "$APP_DIR/main.py" "\$@"
EOF
chmod 755 "$BIN_DIR/flow" || { fail 1; exit $?; }
register_path() {
    PROFILE_FILE=$1
    touch "$PROFILE_FILE" || return 1
    if grep -F '# >>> FlowMobile desktop >>>' "$PROFILE_FILE" >/dev/null 2>&1; then
        return 0
    fi
    cat >> "$PROFILE_FILE" <<'EOF'
# >>> FlowMobile desktop >>>
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH" ;; esac
export PATH
# <<< FlowMobile desktop <<<
EOF
}
register_path "$HOME/.profile" || { fail 1; exit $?; }
LOGIN_SHELL=${SHELL:-}
case "${LOGIN_SHELL##*/}" in
    bash) register_path "$HOME/.bashrc" || { fail 1; exit $?; } ;;
    zsh) register_path "$HOME/.zshrc" || { fail 1; exit $?; } ;;
esac
"$BIN_DIR/flow" --health-check >> "$LOG_FILE" 2>&1 || { fail 1; exit $?; }
rm -rf "$BACKUP_DIR"
rm -rf "$PRESERVED_DIR"
step_done "comando registrado"

trap - EXIT HUP INT TERM
cleanup
echo ""
echo "✓ FlowMobile $VERSION instalado correctamente."
echo "Comando: flow"
echo "Vídeos: $DOWNLOAD_ROOT/FlowMobile/Videos"
echo "Audios: $DOWNLOAD_ROOT/FlowMobile/Audio"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "IMPORTANTE · Actívalo ahora con: export PATH=\"$BIN_DIR:\$PATH\" && hash -r" ;;
esac
echo "Registro: $LOG_FILE"
