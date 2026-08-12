#!/bin/sh
# FlowMobile / a-Shell: descarga TikTok con reintento mediante la API móvil.
# Uso: ./tiktok-download.sh URL [opciones adicionales de yt-dlp]

set -u

SCRIPT_NAME=$(basename "$0")
LOG_DIR=${FLOWMOBILE_LOG_DIR:-"$HOME/Documents/FlowMobile/logs"}
LOG_FILE="$LOG_DIR/tiktok-download.log"
API_HOSTS=${FLOW_TIKTOK_API_HOSTS:-"api22-normal-c-useast2a.tiktokv.com api16-normal-c-useast1a.tiktokv.com"}
DEVICE_ID=${FLOW_TIKTOK_DEVICE_ID:-7379690547022071302}
RUN_OUTPUT=${TMPDIR:-/tmp}/flowmobile-tiktok-$$.log

cleanup() {
    rm -f "$RUN_OUTPUT"
}
trap cleanup EXIT INT TERM

usage() {
    echo "Uso: $SCRIPT_NAME URL [opciones de yt-dlp]"
    echo "Ejemplo: $SCRIPT_NAME 'https://vt.tiktok.com/ZS477H1n3/'"
    echo ""
    echo "Variables opcionales:"
    echo "  FLOWMOBILE_LOG_DIR       Directorio de logs"
    echo "  FLOW_TIKTOK_API_HOSTS    Hostnames API separados por espacios"
}

if [ "$#" -lt 1 ]; then
    usage >&2
    exit 2
fi

URL=$1
shift

mkdir -p "$LOG_DIR" 2>/dev/null || {
    echo "ERROR: no se pudo crear el directorio de logs: $LOG_DIR" >&2
    exit 1
}

timestamp() {
    date '+%Y-%m-%dT%H:%M:%S%z'
}

log() {
    message="[$(timestamp)] $*"
    echo "$message" | tee -a "$LOG_FILE"
}

run_ytdlp() {
    if command -v yt-dlp >/dev/null 2>&1; then
        yt-dlp "$@"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m yt_dlp "$@"
    else
        echo "No se encontró yt-dlp ni el módulo yt_dlp de Python." >&2
        return 127
    fi
}

log "Inicio de descarga: $URL"
log "Intento 1/$(($(printf '%s\n' "$API_HOSTS" | wc -w) + 1)): extractor normal"

# Los argumentos del usuario se aplican en ambos intentos; URL va al final.
run_ytdlp "$@" "$URL" >"$RUN_OUTPUT" 2>&1
NORMAL_STATUS=$?
cat "$RUN_OUTPUT" | tee -a "$LOG_FILE"

if [ "$NORMAL_STATUS" -eq 0 ]; then
    log "ÉXITO: descarga completada con el extractor normal."
    exit 0
fi

log "Falló el extractor normal (código $NORMAL_STATUS). Se probará la API móvil de TikTok."

HOST_INDEX=0
for API_HOST in $API_HOSTS; do
    HOST_INDEX=$((HOST_INDEX + 1))
    log "Intento API $HOST_INDEX: $API_HOST"
    run_ytdlp "$@" \
        --extractor-args "tiktok:device_id=$DEVICE_ID;api_hostname=$API_HOST" \
        "$URL" >"$RUN_OUTPUT" 2>&1
    API_STATUS=$?
    cat "$RUN_OUTPUT" | tee -a "$LOG_FILE"

    if [ "$API_STATUS" -eq 0 ]; then
        log "ÉXITO: descarga completada con API móvil ($API_HOST)."
        exit 0
    fi
    log "Falló API móvil $API_HOST (código $API_STATUS)."
done

log "FALLO: TikTok rechazó el extractor web y los hostnames de API configurados."
log "El log completo está en: $LOG_FILE"
echo ""
echo "No se usaron cookies automáticas ni servicios externos."
echo "Prueba otra red o usa cookies.txt manualmente con yt-dlp si las tienes."
exit 1
