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
        "SECURITY.md",
        "CONTRIBUTING.md",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        "docs/DEVICE_TESTING.md",
        "main.py",
        "requirements.txt",
        "install.sh",
        "install-ios.sh",
        "bootstrap_ios.py",
        "install_ios.py",
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

    if ($init -notmatch ('APP_VERSION\s*=\s*"' + [regex]::Escape($version) + '"')) {
        throw "APP_VERSION no coincide con VERSION ($version)."
    }
    if ($readme -notmatch ('Versi.n actual:\s*\*\*' + [regex]::Escape($version) + '\*\*')) {
        throw "README.md no muestra la version $version."
    }
    if ($changelog -notmatch ('(?m)^##\s+' + [regex]::Escape($version) + '(?:\s|$)')) {
        throw "CHANGELOG.md no contiene la version $version."
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
    $textFiles += Get-Item main.py, install.sh, install-ios.sh, bootstrap_ios.py, install_ios.py, install-termux.sh, scripts/flow, scripts/flow_ios.py, scripts/check-device.sh, scripts/check_device.py
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

    Write-Host "Estructura, privacidad, version y finales de linea: OK" -ForegroundColor Green

    if (-not $SkipPython) {
        $python = $null
        $prefix = @()
        $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            $python = $pyLauncher.Source
            $prefix = @("-3")
        } else {
            foreach ($name in @("python3", "python")) {
                $candidate = Get-Command $name -ErrorAction SilentlyContinue
                if ($candidate -and $candidate.Source -notlike "*WindowsApps*") {
                    $python = $candidate.Source
                    break
                }
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
