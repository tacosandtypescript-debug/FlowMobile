#!/bin/sh
set -eu

REPOSITORY="${1:-${FLOWMOBILE_REPOSITORY:-tacosandtypescript-debug/FlowMobile}}"

echo "FlowMobile para iOS requiere la aplicación a-Shell completa y Python."
echo "Por seguridad, el instalador shell antiguo ya no descarga código sin verificar."
echo "Ejecuta directamente en a-Shell:"
echo "curl -fsSL https://github.com/$REPOSITORY/releases/latest/download/bootstrap_ios.py | python3 - $REPOSITORY"
exit 1
