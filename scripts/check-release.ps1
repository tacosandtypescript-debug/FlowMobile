param(
    [switch]$SkipPython
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

try {
    $required = @(
        ".gitignore",
        ".gitattributes",
        "VERSION",
        "CHANGELOG.md",
        "README.md",
        "LICENSE",
        "NOTICE",
        "LICENSING.md",
        "TRADEMARKS.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/workflows/pages.yml",
        "docs/DEVICE_TESTING.md",
        "docs/COPIAR_IOS.md",
        "docs/COPIAR_ANDROID.md",
        "docs/GUIA_COMPLETA.md",
        "site/index.html",
        "main.py",
        "requirements.txt",
        "install.sh",
        "install-ios.sh",
        "bootstrap_ios.py",
        "install_ios.py",
        "uninstall_ios.py",
        "install-termux.sh",
        "scripts/flow",
        "scripts/flow_ios.py",
        "scripts/check-device.sh",
        "scripts/check_device.py",
        "flow/__init__.py"
    )

    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Falta un archivo obligatorio: $path"
        }
    }

    $version = (Get-Content -Raw -Encoding utf8 VERSION).Trim()
    $init = Get-Content -Raw -Encoding utf8 flow/__init__.py
    $readme = Get-Content -Raw -Encoding utf8 README.md
    $changelog = Get-Content -Raw -Encoding utf8 CHANGELOG.md
    $license = Get-Content -Raw -Encoding utf8 LICENSE
    $licensing = Get-Content -Raw -Encoding utf8 LICENSING.md

    if ($init -notmatch ('APP_VERSION\s*=\s*"' + [regex]::Escape($version) + '"')) {
        throw "APP_VERSION no coincide con VERSION ($version)."
    }
    if ($readme -notmatch ('Versi.n actual:\s*\*\*' + [regex]::Escape($version) + '\*\*')) {
        throw "README.md no muestra la version $version."
    }
    if ($changelog -notmatch ('(?m)^##\s+' + [regex]::Escape($version) + '(?:\s|$)')) {
        throw "CHANGELOG.md no contiene la version $version."
    }
    if (-not $license.StartsWith("# PolyForm Strict License 1.0.0")) {
        throw "LICENSE no contiene PolyForm Strict License 1.0.0."
    }
    if ($licensing -notmatch '7\.6\.0 a 7\.6\.13' -or $licensing -notmatch '7\.6\.14 y posteriores') {
        throw "LICENSING.md no documenta correctamente la transicion desde MIT."
    }

    $markerPattern = "TU_" + "USUARIO|TU_" + "REPOSITORIO"
    $searchFiles = Get-ChildItem -Recurse -File | Where-Object {
            $_.FullName -notmatch '[\\/](Downloads|\.git|\.codex|\.agents|\.flowmobile|\.flowmobile-data)[\\/]'
    }
    $placeholder = $searchFiles | Select-String -Pattern $markerPattern -Encoding utf8
    if ($placeholder) {
        throw "Quedan marcadores provisionales:`n$placeholder"
    }

    $textFiles = @()
    $textFiles += Get-ChildItem flow, tests -Recurse -File -Include *.py
    $textFiles += Get-Item main.py, install.sh, install-ios.sh, bootstrap_ios.py, install_ios.py, uninstall_ios.py, install-termux.sh, scripts/flow, scripts/flow_ios.py, scripts/check-device.sh, scripts/check_device.py
    foreach ($file in $textFiles) {
        $content = [IO.File]::ReadAllText($file.FullName)
        if ($content.Contains("`r`n")) {
            throw "El archivo debe usar finales LF: $($file.FullName)"
        }
    }

    $privatePatterns = @(
        "/Downloads/",
        "/.flowmobile/",
        "/.flowmobile-data/",
        "/.codex-remote-attachments/",
        "/.ssh/",
        "/.env",
        "/.git-credentials"
    )
    $ignore = Get-Content -Raw -Encoding utf8 .gitignore
    foreach ($pattern in $privatePatterns) {
        if (-not $ignore.Contains($pattern)) {
            throw ".gitignore no protege: $pattern"
        }
    }

    $publishing = Get-Content -Raw -Encoding utf8 PUBLISHING.md
    if ($publishing -notmatch 'git config user\.email "[^"\r\n]+@users\.noreply\.github\.com"') {
        throw "PUBLISHING.md debe recomendar un correo privado de GitHub."
    }

    Write-Host "Estructura, privacidad, version y finales de linea: OK" -ForegroundColor Green

    if (-not $SkipPython) {
        $python = $null
        $prefix = @()
        if ($env:pythonLocation) {
            $actionsPython = Join-Path $env:pythonLocation "python.exe"
            if (Test-Path -LiteralPath $actionsPython -PathType Leaf) {
                $python = $actionsPython
            }
        }
        if (-not $python) {
            foreach ($name in @("python3", "python")) {
                $candidate = Get-Command $name -ErrorAction SilentlyContinue
                if ($candidate -and $candidate.Source -notlike "*WindowsApps*") {
                    $python = $candidate.Source
                    break
                }
            }
        }
        if (-not $python) {
            $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
            if ($pyLauncher) {
                $python = $pyLauncher.Source
                $prefix = @("-3")
            }
        }

        if ($python) {
            & $python @prefix -m compileall -q flow main.py
            if ($LASTEXITCODE -ne 0) { throw "Python encontro un error de sintaxis." }
            & $python @prefix -m unittest discover -s tests -v
            if ($LASTEXITCODE -ne 0) { throw "Fallaron las pruebas de Python." }
        } else {
            Write-Warning "Python no esta instalado; las pruebas Python se ejecutaran en Termux/a-Shell."
        }
    }

    Write-Host "FlowMobile $version esta preparado para GitHub." -ForegroundColor Cyan
} finally {
    Pop-Location
}
