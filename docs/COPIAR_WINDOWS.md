# Instalar en Windows

Abre **PowerShell** o **Windows Terminal**, copia el bloque completo y pulsa
Enter:

```powershell
irm https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install-windows.ps1 | iex
```

El instalador comprueba Python 3.10 o posterior y FFmpeg. Si faltan, los
instala mediante `winget`, verifica el paquete con SHA-256 y registra `flow`
en el PATH del usuario. No necesita ejecutarse como administrador.

Cuando termine, abre una terminal nueva y escribe:

```powershell
flow
```

Registro técnico privado:

```powershell
Get-Content "$HOME\.flowmobile-install.log"
```

Para mostrar la salida completa durante la instalación:

```powershell
$env:FLOWMOBILE_VERBOSE=1; irm https://github.com/tacosandtypescript-debug/FlowMobile/releases/latest/download/install-windows.ps1 | iex
```
