# Instalar en Linux

Abre una terminal, copia el comando completo y pulsa Enter:

```sh
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install-linux.sh | sh -s -- tacosandtypescript-debug/FlowMobile
```

El instalador reconoce `apt`, `dnf`, `pacman` y `zypper`. Solo solicita `sudo`
si faltan Python 3.10, FFmpeg, FFprobe o certificados del sistema. FlowMobile
se instala para el usuario en `~/.local/share/flowmobile`.

Al terminar, recarga el perfil y abre FlowMobile:

```sh
. "$HOME/.profile"
flow
```

Registro técnico privado:

```sh
cat "$HOME/.flowmobile-install.log"
```

Modo con salida completa:

```sh
curl -fsSL https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install-linux.sh | FLOWMOBILE_VERBOSE=1 sh -s -- tacosandtypescript-debug/FlowMobile
```
