#!/bin/sh
set -eu

REPOSITORY="${1:-${FLOWMOBILE_REPOSITORY:-tacosandtypescript-debug/FlowMobile}}"
MODE="${2:-}"
BRANCH="${FLOWMOBILE_BRANCH:-}"

if [ -z "$BRANCH" ] && command -v curl >/dev/null 2>&1; then
    BRANCH=$(curl -fsSL "https://api.github.com/repos/$REPOSITORY/releases/latest" 2>/dev/null \
        | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
        | head -n 1) || BRANCH=""
fi
BRANCH="${BRANCH:-main}"

case "$REPOSITORY" in
    */*) ;;
    *) echo "Repositorio no válido. Usa USUARIO/FlowMobile."; exit 1 ;;
esac

case "${TERMUX_VERSION:-}:${PREFIX:-}" in
    *com.termux*)
        DETECTED_PLATFORM="termux"
        DETECTED_LABEL="Android con Termux"
        ;;
    *)
        DETECTED_PLATFORM="ashell"
        DETECTED_LABEL="iPhone/iPad con a-Shell"
        ;;
esac

SELECTED_PLATFORM="${FLOWMOBILE_PLATFORM:-}"
if [ "$MODE" = "--auto" ] || [ "${FLOWMOBILE_NONINTERACTIVE:-0}" = "1" ]; then
    SELECTED_PLATFORM="$DETECTED_PLATFORM"
fi

case "$SELECTED_PLATFORM" in
    android|termux) SELECTED_PLATFORM="termux" ;;
    ios|ashell|a-shell) SELECTED_PLATFORM="ashell" ;;
    "") ;;
    *)
        echo "Plataforma no válida: $SELECTED_PLATFORM"
        echo "Usa termux o ashell."
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
            printf "Selecciona 1 o 2 [Enter = usar lo detectado]: " > /dev/tty
            IFS= read -r ANSWER < /dev/tty || ANSWER=""
            case "$ANSWER" in
                "") SELECTED_PLATFORM="$DETECTED_PLATFORM"; break ;;
                1) SELECTED_PLATFORM="termux"; break ;;
                2) SELECTED_PLATFORM="ashell"; break ;;
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
esac

echo
echo "Preparando FlowMobile para $PLATFORM_LABEL…"

TEMP_SCRIPT="${TMPDIR:-$HOME/tmp}/flowmobile-installer-$$.sh"
TEMP_SUMS="$TEMP_SCRIPT.sha256sums"
mkdir -p "$(dirname "$TEMP_SCRIPT")"
trap 'rm -f "$TEMP_SCRIPT" "$TEMP_SUMS"' 0 HUP INT TERM
case "$BRANCH" in
    v[0-9]*|[0-9]*)
        RELEASE_URL="https://github.com/$REPOSITORY/releases/download/$BRANCH"
        curl -fL "$RELEASE_URL/SHA256SUMS" -o "$TEMP_SUMS"
        curl -fL "$RELEASE_URL/$PLATFORM_INSTALLER" -o "$TEMP_SCRIPT"
        EXPECTED=$(awk -v file="$PLATFORM_INSTALLER" '$2 == file || $2 == "*" file {print $1; exit}' "$TEMP_SUMS")
        ACTUAL=$(sha256sum "$TEMP_SCRIPT" | awk '{print $1}')
        [ -n "$EXPECTED" ] && [ "$ACTUAL" = "$EXPECTED" ] || {
            echo "Seguridad: el instalador no coincide con el SHA-256 oficial."
            exit 1
        }
        ;;
    *)
        [ "${FLOWMOBILE_ALLOW_UNVERIFIED:-0}" = "1" ] || {
            echo "Seguridad: no existe un release estable verificable."
            exit 1
        }
        curl -fL "https://raw.githubusercontent.com/$REPOSITORY/$BRANCH/$PLATFORM_INSTALLER" -o "$TEMP_SCRIPT"
        ;;
esac
FLOWMOBILE_BRANCH="$BRANCH" sh "$TEMP_SCRIPT" "$REPOSITORY"
