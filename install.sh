#!/bin/sh
set -eu

REPOSITORY="${1:-${FLOWMOBILE_REPOSITORY:-tacosandtypescript-debug/FlowMobile}}"
MODE="${2:-}"
BRANCH="${FLOWMOBILE_BRANCH:-}"
LOG_FILE="${FLOWMOBILE_INSTALL_LOG:-$HOME/.flowmobile-install.log}"
umask 077
if ! : 2>/dev/null > "$LOG_FILE"; then
    echo "✕ No se pudo crear el registro privado: $LOG_FILE" >&2
    echo "Revisa el espacio y los permisos de la terminal." >&2
    exit 1
fi
chmod 600 "$LOG_FILE" 2>/dev/null || true

bootstrap_failure() {
    code=$1
    cause=$2
    hint=$3
    detail=$(awk 'NF {line=$0} END {if (line) print substr(line, 1, 300)}' "$LOG_FILE")
    [ -n "$detail" ] || detail="Sin detalle adicional"
    case "$detail" in
        *" 404"*|*"error: 404"*)
            code="FM-INSTALL-HTTP-404"
            cause="GitHub no encontró uno de los archivos del release."
            hint="Confirma que exista una versión estable o espera unos minutos."
            ;;
        *" 403"*|*"error: 403"*)
            code="FM-INSTALL-HTTP-403"
            cause="GitHub rechazó temporalmente la descarga."
            hint="Cambia de red o espera unos minutos antes de repetir."
            ;;
        *" 429"*|*"error: 429"*|*"Too Many Requests"*)
            code="FM-INSTALL-HTTP-429"
            cause="GitHub limitó temporalmente las descargas."
            hint="Espera unos minutos o cambia de red antes de repetir."
            ;;
        *"Could not resolve"*|*"Failed to connect"*|*"timed out"*)
            code="FM-INSTALL-NETWORK"
            cause="La terminal no pudo conectarse a GitHub."
            hint="Comprueba internet, DNS o VPN y repite el mismo comando."
            ;;
    esac
    printf '\n✕ No se pudo preparar el instalador.\n' >&2
    printf 'Código: %s\n' "$code" >&2
    printf 'Causa: %s\n' "$cause" >&2
    printf 'Detalle: %s\n' "$detail" >&2
    printf 'Solución: %s\n' "$hint" >&2
    printf 'Registro completo: %s\n' "$LOG_FILE" >&2
    exit 1
}

case "$REPOSITORY" in
    ""|/*|*/|*/*/*|*[!A-Za-z0-9_./-]*)
        printf '%s\n' "Repositorio no válido: $REPOSITORY" >> "$LOG_FILE"
        bootstrap_failure "FM-INSTALL-REPOSITORY" \
            "El repositorio no usa el formato USUARIO/REPOSITORIO." \
            "Vuelve a copiar el enlace oficial de FlowMobile."
        ;;
    */*) ;;
    *)
        bootstrap_failure "FM-INSTALL-REPOSITORY" \
            "El repositorio no usa el formato USUARIO/REPOSITORIO." \
            "Vuelve a copiar el enlace oficial de FlowMobile."
        ;;
esac

if [ -z "$BRANCH" ] && command -v curl >/dev/null 2>&1; then
    BRANCH=$(curl -fsSL --retry 1 --retry-all-errors --connect-timeout 15 --max-time 60 \
        "https://api.github.com/repos/$REPOSITORY/releases/latest" 2>>"$LOG_FILE" \
        | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
        | head -n 1) || BRANCH=""
fi
[ -n "$BRANCH" ] || bootstrap_failure \
    "FM-INSTALL-NETWORK" \
    "No se pudo consultar el release estable de GitHub." \
    "Comprueba internet, DNS o VPN y repite el mismo comando."

case "${TERMUX_VERSION:-}:${PREFIX:-}" in
    *com.termux*)
        DETECTED_PLATFORM="termux"
        DETECTED_LABEL="Android con Termux"
        ;;
    *)
        if [ "$(uname -s 2>/dev/null || true)" = "Linux" ]; then
            DETECTED_PLATFORM="linux"
            DETECTED_LABEL="Linux"
        else
            DETECTED_PLATFORM="ashell"
            DETECTED_LABEL="iPhone/iPad con a-Shell"
        fi
        ;;
esac

SELECTED_PLATFORM="${FLOWMOBILE_PLATFORM:-}"
if [ "$MODE" = "--auto" ] || [ "${FLOWMOBILE_NONINTERACTIVE:-0}" = "1" ]; then
    SELECTED_PLATFORM="$DETECTED_PLATFORM"
fi

case "$SELECTED_PLATFORM" in
    android|termux) SELECTED_PLATFORM="termux" ;;
    ios|ashell|a-shell) SELECTED_PLATFORM="ashell" ;;
    linux|desktop-linux) SELECTED_PLATFORM="linux" ;;
    "") ;;
    *)
        echo "Plataforma no válida: $SELECTED_PLATFORM"
        echo "Usa termux, ashell o linux."
        exit 1
        ;;
esac

if [ -z "$SELECTED_PLATFORM" ]; then
    echo
    echo "FlowMobile detectó: $DETECTED_LABEL"
    if [ -r /dev/tty ]; then
        while :; do
            echo "¿Dónde quieres instalar FlowMobile?"
            echo "  [1] Android — Termux"
            echo "  [2] iPhone/iPad — a-Shell"
            echo "  [3] Linux — Terminal"
            printf "Selecciona 1, 2 o 3 [Enter = usar lo detectado]: " > /dev/tty
            IFS= read -r ANSWER < /dev/tty || ANSWER=""
            case "$ANSWER" in
                "") SELECTED_PLATFORM="$DETECTED_PLATFORM"; break ;;
                1) SELECTED_PLATFORM="termux"; break ;;
                2) SELECTED_PLATFORM="ashell"; break ;;
                3) SELECTED_PLATFORM="linux"; break ;;
                *) echo "Opción no válida." ;;
            esac
        done
    else
        echo "No hay una terminal interactiva; se usará la detección automática."
        SELECTED_PLATFORM="$DETECTED_PLATFORM"
    fi
fi

if [ "$SELECTED_PLATFORM" != "$DETECTED_PLATFORM" ] && [ -r /dev/tty ]; then
    echo "Aviso: la opción elegida no coincide con $DETECTED_LABEL."
    printf "¿Continuar de todos modos? [s/N]: " > /dev/tty
    IFS= read -r CONFIRM < /dev/tty || CONFIRM=""
    case "$CONFIRM" in
        s|S|si|SI|sí|SÍ) ;;
        *) echo "Instalación cancelada."; exit 1 ;;
    esac
fi

case "$SELECTED_PLATFORM" in
    termux)
        PLATFORM_INSTALLER="install-termux.sh"
        PLATFORM_LABEL="Android con Termux"
        ;;
    ashell)
        echo
        echo "a-Shell no puede instalar FlowMobile dentro de sh/dash."
        echo "Ejecuta directamente en a-Shell:"
        echo "curl -fsSL https://github.com/$REPOSITORY/releases/latest/download/bootstrap_ios.py | python3 - $REPOSITORY"
        echo "Después cierra esa ventana, abre una nueva y escribe: flow"
        exit 1
        ;;
    linux)
        PLATFORM_INSTALLER="install-linux.sh"
        PLATFORM_LABEL="Linux"
        ;;
esac

TEMP_SCRIPT="${TMPDIR:-$HOME/tmp}/flowmobile-installer-$$.sh"
TEMP_SUMS="$TEMP_SCRIPT.sha256sums"
mkdir -p "$(dirname "$TEMP_SCRIPT")"
trap 'rm -f "$TEMP_SCRIPT" "$TEMP_SUMS"' 0 HUP INT TERM
case "$BRANCH" in
    v[0-9]*|[0-9]*)
        RELEASE_URL="https://github.com/$REPOSITORY/releases/download/$BRANCH"
        curl -fsSL --retry 1 --retry-all-errors --connect-timeout 15 --max-time 120 \
            "$RELEASE_URL/SHA256SUMS" -o "$TEMP_SUMS" 2>>"$LOG_FILE" || bootstrap_failure \
            "FM-INSTALL-DOWNLOAD" "No se descargó SHA256SUMS." "Comprueba internet y vuelve a intentarlo."
        curl -fsSL --retry 1 --retry-all-errors --connect-timeout 15 --max-time 120 \
            "$RELEASE_URL/$PLATFORM_INSTALLER" -o "$TEMP_SCRIPT" 2>>"$LOG_FILE" || bootstrap_failure \
            "FM-INSTALL-DOWNLOAD" "No se descargó el instalador de $PLATFORM_LABEL." "Espera unos minutos y vuelve a intentarlo."
        EXPECTED=$(awk -v file="$PLATFORM_INSTALLER" '$2 == file || $2 == "*" file {print $1; exit}' "$TEMP_SUMS")
        ACTUAL=$(sha256sum "$TEMP_SCRIPT" | awk '{print $1}')
        [ -n "$EXPECTED" ] && [ "$ACTUAL" = "$EXPECTED" ] || {
            printf '%s\n' "El instalador no coincide con el SHA-256 oficial." >> "$LOG_FILE"
            bootstrap_failure "FM-INSTALL-INTEGRITY" \
                "La verificación de seguridad no coincide." \
                "No continúes; vuelve a copiar el enlace desde el repositorio oficial."
        }
        ;;
    *)
        [ "${FLOWMOBILE_ALLOW_UNVERIFIED:-0}" = "1" ] || {
            echo "Seguridad: no existe un release estable verificable."
            exit 1
        }
        curl -fsSL --retry 1 --retry-all-errors --connect-timeout 15 --max-time 120 \
            "https://raw.githubusercontent.com/$REPOSITORY/$BRANCH/$PLATFORM_INSTALLER" \
            -o "$TEMP_SCRIPT" 2>>"$LOG_FILE" || bootstrap_failure \
            "FM-INSTALL-DOWNLOAD" "No se descargó el instalador de desarrollo." "Comprueba la referencia solicitada."
        ;;
esac
FLOWMOBILE_BRANCH="$BRANCH" FLOWMOBILE_INSTALL_LOG="$LOG_FILE" sh "$TEMP_SCRIPT" "$REPOSITORY"
