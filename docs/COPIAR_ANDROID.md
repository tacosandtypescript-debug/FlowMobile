# Copiar instalación para Android

Abre **Termux**. Pulsa el icono de copiar situado en la esquina del bloque y
pega las dos líneas juntas en la terminal:

```sh
umask 077; pkg install -y curl > "$HOME/.flowmobile-install.log" 2>&1 || { echo "No se pudo preparar curl:"; tail -n 1 "$HOME/.flowmobile-install.log"; exit 1; }
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install.sh | sh -s -- tacosandtypescript-debug/FlowMobile
```

Si la aplicación de GitHub no muestra el icono, mantén pulsado el bloque y elige
**Copiar**. Termux ejecutará primero la instalación de `curl` y después
FlowMobile.
