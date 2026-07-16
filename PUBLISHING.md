# Publicar FlowMobile

## Qué se sube a GitHub

- `.gitignore`, `.gitattributes`, `VERSION`, `requirements.txt` y `main.py`.
- Las carpetas `flow/`, `scripts/` y `tests/` completas.
- `install.sh`, `install-ios.sh`, `bootstrap_ios.py`, `install_ios.py`,
  `uninstall_ios.py` e `install-termux.sh`.
- `README.md`, `CHANGELOG.md` y `PUBLISHING.md`.
- `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/` y `.github/`.

## Qué no se sube

- `Downloads/`, el historial, los ajustes, `.flowmobile/` y `.flowmobile-data/`.
- `.flowmobile-source` y `.flowios-source`, porque se crean al instalar.
- Cookies, sesiones de yt-dlp, archivos `.env`, tokens o secretos.
- Entornos Python, cachés, cobertura, registros y archivos temporales.
- Las carpetas locales `.codex/`, `.agents/`, `.vscode/` o `.idea/`.
- Claves SSH, credenciales, certificados privados y paquetes ZIP locales.

Estas reglas están separadas y documentadas dentro de `.gitignore`. Si algún
archivo privado ya se había añadido a Git antes de ignorarlo, hay que retirarlo
del índice antes de publicar; añadirlo a `.gitignore` no borra versiones
anteriores del historial.

1. Crea un repositorio público llamado `FlowMobile` con rama `main`.
2. Confirma que el repositorio configurado sea
   `tacosandtypescript-debug/FlowMobile`.
3. Añade una licencia apropiada antes de anunciar el proyecto.
4. Confirma que Git solo incluya los elementos de la sección “Qué se sube”.
5. Ejecuta las pruebas.
6. Prueba instalaciones limpias tanto en a-Shell como en Termux.

## Comprobación y publicación desde Windows

Abre PowerShell dentro de la carpeta `FlowApp` y ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-release.ps1
git init -b main
git config user.name "tacosandtypescript-debug"
git config user.email "tacosandtypescript@gmail.com"
git add .
git status
git commit -m "Integrar videos de Termux con la galería 7.6.8"
git remote add origin https://github.com/tacosandtypescript-debug/FlowMobile.git
git push -u origin main
```

Antes del `commit`, `git status` no debe mostrar `Downloads`, `.flowmobile`,
cookies, claves ni configuraciones locales. Si `origin` ya existe, usa:

```powershell
git remote set-url origin https://github.com/tacosandtypescript-debug/FlowMobile.git
```

## Pruebas en los dispositivos

En Termux, dentro del proyecto instalado:

```sh
sh scripts/check-device.sh
```

En a-Shell:

```sh
python3 scripts/check_device.py
```

El diagnóstico comprueba Python, yt-dlp, FFmpeg, FFprobe, la plataforma y las 102
pruebas automatizadas. Después abre `flow` y comprueba una descarga de audio,
una de vídeo, compartir, la calidad final y la sección de actualizaciones. Haz
primero la prueba completa en Termux y después repítela en a-Shell.

## Crear una versión estable

Cuando `main` esté verde y la matriz de `docs/DEVICE_TESTING.md` esté completa:

```powershell
git tag -a v7.6.8 -m "FlowMobile 7.6.8"
git push origin v7.6.8
```

La acción `Release` comprueba que la etiqueta coincida con `VERSION`, ejecuta
las pruebas y publica ZIP, TAR.GZ y `SHA256SUMS`. FlowMobile consulta primero el
Release estable más reciente; solo usa `main` mientras el repositorio todavía
no tenga ningún Release.

## Órdenes públicas

En a-Shell se usa el instalador Python nativo para evitar `dash`:

```sh
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/bootstrap_ios.py | python3 - tacosandtypescript-debug/FlowMobile
```

Al terminar, abre una ventana nueva de a-Shell y ejecuta `flow`. El menú no debe
abrirse desde el proceso conectado a `curl`, porque esa entrada no es interactiva.

En Termux se usa el instalador de shell:

```sh
curl -fsSL https://raw.githubusercontent.com/tacosandtypescript-debug/FlowMobile/main/install.sh | sh -s -- tacosandtypescript-debug/FlowMobile
```

En Termux puede ser necesario instalar primero `curl`:

```sh
pkg install -y curl
```

## Publicar una versión

1. Incrementa `VERSION` y `flow/__init__.py`.
2. Añade la entrega a `CHANGELOG.md`.
3. Ejecuta todas las pruebas.
4. Sube los cambios a `main` y crea una etiqueta y Release.
5. Abre una instalación anterior en cada plataforma y confirma que FlowMobile
   ofrece la actualización antes de modificar archivos.

Al subir una actualización a `main`, es obligatorio cambiar `VERSION`,
`flow/__init__.py` y añadir una sección con el mismo número en `CHANGELOG.md`.
Las instalaciones existentes detectarán la versión al abrir `flow`, mostrarán
esas novedades y preguntarán si desean actualizar.
