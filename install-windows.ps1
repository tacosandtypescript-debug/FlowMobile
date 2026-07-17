param(
    [string]$Repository = "tacosandtypescript-debug/FlowMobile",
    [switch]$Auto
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$VerboseInstall = $env:FLOWMOBILE_VERBOSE -eq "1"
$LogFile = if ($env:FLOWMOBILE_INSTALL_LOG) { $env:FLOWMOBILE_INSTALL_LOG } else { Join-Path $HOME ".flowmobile-install.log" }
$AppDir = if ($env:FLOWMOBILE_HOME) { $env:FLOWMOBILE_HOME } else { Join-Path $env:LOCALAPPDATA "FlowMobile" }
$BinDir = Join-Path $env:LOCALAPPDATA "FlowMobileBin"
$DownloadsRoot = if ($env:FLOWMOBILE_DOWNLOADS) { $env:FLOWMOBILE_DOWNLOADS } else { Join-Path $HOME "Downloads" }
$BackupDir = "$AppDir.rollback"
$PreservedDir = Join-Path (Split-Path $AppDir) ".flowmobile-data"
$WorkDir = Join-Path ([IO.Path]::GetTempPath()) ("flowmobile-windows-" + [guid]::NewGuid().ToString("N"))
$Stage = "Preparando"
$Code = "FM-WINDOWS-INSTALL"
$Step = 0
$BackupReady = $false
$NewInstalled = $false

try {
    [IO.File]::WriteAllText($LogFile, "FlowMobile installer log`r`n", [Text.UTF8Encoding]::new($false))
    & icacls.exe $LogFile /inheritance:r /grant:r "$($env:USERNAME):(F)" *> $null
    if ($LASTEXITCODE -ne 0) { throw "icacls no pudo proteger el registro." }
} catch {
    Write-Host "✕ No se pudo crear el registro privado: $LogFile" -ForegroundColor Red
    if ($Auto) { exit 1 }
    return
}

function Write-Log([string]$Text) {
    [IO.File]::AppendAllText($LogFile, $Text + "`r`n", [Text.UTF8Encoding]::new($false))
}

function Start-Stage([string]$Name, [string]$FailureCode) {
    $script:Step++
    $script:Stage = $Name
    $script:Code = $FailureCode
    Write-Host ""
    Write-Host "[$Step/6] $Name…"
    Write-Log "`r`n== $Name =="
}

function Complete-Stage([string]$Detail) {
    Write-Host "      ✓ Listo · $Detail" -ForegroundColor Green
}

function Invoke-Logged([scriptblock]$Action, [string]$Description) {
    Write-Log "+ $Description"
    try {
        $output = & $Action 2>&1 | Out-String
        if ($output) {
            [IO.File]::AppendAllText($LogFile, $output, [Text.UTF8Encoding]::new($false))
            if ($VerboseInstall) { Write-Host $output -NoNewline }
        }
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            throw "$Description devolvió el código $LASTEXITCODE. $($output.Trim())"
        }
        return $output
    } catch {
        Write-Log "$($_.Exception.GetType().Name): $($_.Exception.Message)"
        throw
    }
}

function Invoke-Download([string]$Uri, [string]$Destination) {
    for ($attempt = 0; $attempt -lt 2; $attempt++) {
        try {
            Write-Log "+ GET $Uri"
            Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Destination -TimeoutSec 180
            return
        } catch {
            Write-Log "$($_.Exception.GetType().Name): $($_.Exception.Message)"
            $status = try { [int]$_.Exception.Response.StatusCode } catch { 0 }
            $retryable = $status -eq 429 -or $status -ge 500 -or $status -eq 0
            if ($attempt -eq 0 -and $retryable) {
                Write-Host "      Red temporal; reintentando una vez…" -ForegroundColor Yellow
                Start-Sleep -Seconds 1
                continue
            }
            throw
        }
    }
}

function Find-Python {
    $commands = @("python.exe", "python3.exe")
    foreach ($name in $commands) {
        $found = Get-Command $name -ErrorAction SilentlyContinue
        if ($found) {
            try {
                & $found.Source -c "import sys; raise SystemExit(sys.version_info.major != 3 or sys.version_info.minor in range(10))" 2>$null
                if ($LASTEXITCODE -eq 0) { return $found.Source }
            } catch {}
        }
    }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $resolved = & $py.Source -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and (Test-Path $resolved)) { return $resolved.Trim() }
        } catch {}
    }
    $candidate = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Programs\Python") -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($candidate) { return $candidate.FullName }
    return $null
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Add-UserPath([string]$Directory) {
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @($current -split ";" | Where-Object { $_ })
    if ($parts -notcontains $Directory) {
        [Environment]::SetEnvironmentVariable("Path", (($parts + $Directory) -join ";"), "User")
    }
    if (($env:Path -split ";") -notcontains $Directory) { $env:Path = "$Directory;$env:Path" }
}

function Show-Failure([Exception]$Exception) {
    $detail = $Exception.Message -replace "[\r\n]+", " "
    $cause = "La operación no terminó correctamente."
    $hint = "Consulta el registro y repite la instalación."
    $failureCode = $Code
    switch -Regex ($detail) {
        "404|Not Found" { $failureCode = "FM-WINDOWS-HTTP-404"; $cause = "GitHub no encontró el release solicitado."; $hint = "Comprueba que la versión esté publicada."; break }
        "429|Too Many" { $failureCode = "FM-WINDOWS-HTTP-429"; $cause = "GitHub limitó temporalmente las solicitudes."; $hint = "Espera unos minutos y repite."; break }
        "name resolution|resolve|conexión|timed out" { $failureCode = "FM-WINDOWS-NETWORK"; $cause = "Windows no pudo conectarse a GitHub."; $hint = "Comprueba internet, DNS o VPN."; break }
        "space|espacio" { $failureCode = "FM-WINDOWS-SPACE"; $cause = "No hay espacio suficiente."; $hint = "Libera espacio y repite."; break }
        "SHA-256|hash|checksum" { $failureCode = "FM-WINDOWS-INTEGRITY"; $cause = "El paquete no coincide con su SHA-256."; $hint = "No lo ejecutes; vuelve a descargarlo."; break }
        "pip|distribution" { $failureCode = "FM-WINDOWS-PIP"; $cause = "Python no pudo preparar yt-dlp y EJS."; $hint = "Repara Python y repite."; break }
        "Access|acceso|denied|permiso" { $failureCode = "FM-WINDOWS-PERMISSION"; $cause = "Windows rechazó un permiso."; $hint = "Cierra FlowMobile y repite desde tu usuario normal."; break }
        "winget" { $failureCode = "FM-WINDOWS-WINGET"; $cause = "winget no pudo instalar una dependencia."; $hint = "Actualiza App Installer desde Microsoft Store y repite."; break }
    }
    Write-Host ""
    Write-Host "✕ Instalación detenida en: $Stage" -ForegroundColor Red
    Write-Host "Código: $failureCode"
    Write-Host "Causa: $cause"
    Write-Host "Detalle: $detail"
    Write-Host "Solución: $hint"
    Write-Host "Registro completo: $LogFile"
    Write-Host "Para verlo: Get-Content `"$LogFile`""
}

Write-Host ""
Write-Host "FlowMobile · Instalación para Windows"
Write-Host "La salida técnica se guardará en un registro privado."

try {
    Start-Stage "Preparando" "FM-WINDOWS-PREPARE"
    if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw "Repositorio inválido: $Repository" }
    New-Item -ItemType Directory -Force -Path $WorkDir, $BinDir, (Split-Path $AppDir) | Out-Null
    Complete-Stage "entorno Windows"

    Start-Stage "Dependencias" "FM-WINDOWS-WINGET"
    $Python = Find-Python
    $ffmpeg = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    $ffprobe = Get-Command ffprobe.exe -ErrorAction SilentlyContinue
    if (-not $Python -or -not $ffmpeg -or -not $ffprobe) {
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) { throw "winget no está disponible." }
        if (-not $Python) {
            Invoke-Logged { & $winget.Source install --id Python.Python.3.13 --exact --silent --accept-package-agreements --accept-source-agreements } "winget Python.Python.3.13" | Out-Null
        }
        if (-not $ffmpeg -or -not $ffprobe) {
            Invoke-Logged { & $winget.Source install --id Gyan.FFmpeg --exact --silent --accept-package-agreements --accept-source-agreements } "winget Gyan.FFmpeg" | Out-Null
        }
        Refresh-Path
        $Python = Find-Python
        $ffmpeg = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
        if (-not $ffmpeg) {
            $ffmpeg = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($ffmpeg) { Add-UserPath $ffmpeg.DirectoryName }
        }
    }
    if (-not $Python) { throw "Python 3.10 o posterior no quedó disponible." }
    if (-not (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe.exe -ErrorAction SilentlyContinue)) { throw "FFmpeg o FFprobe no quedó disponible después de winget." }
    Complete-Stage "Python y FFmpeg"

    Start-Stage "Descargando" "FM-WINDOWS-DOWNLOAD"
    $Reference = $env:FLOWMOBILE_BRANCH
    if (-not $Reference) {
        $latestFile = Join-Path $WorkDir "latest.json"
        Invoke-Download "https://api.github.com/repos/$Repository/releases/latest" $latestFile
        $latest = Get-Content -Raw -Encoding UTF8 $latestFile | ConvertFrom-Json
        $Reference = [string]$latest.tag_name
    }
    if ($Reference -notmatch '^v?\d+(\.\d+){1,3}$') { throw "Release estable inválido: $Reference" }
    $Version = $Reference.TrimStart("v")
    $baseUrl = "https://github.com/$Repository/releases/download/$Reference"
    $zipName = "FlowMobile-$Version.zip"
    $zipPath = Join-Path $WorkDir $zipName
    Invoke-Download "$baseUrl/SHA256SUMS" (Join-Path $WorkDir "SHA256SUMS")
    Invoke-Download "$baseUrl/$zipName" $zipPath
    Complete-Stage "release oficial v$Version"

    Start-Stage "Verificando" "FM-WINDOWS-INTEGRITY"
    $checksumLine = Get-Content (Join-Path $WorkDir "SHA256SUMS") | Where-Object { $_ -match "\s\*?$([regex]::Escape($zipName))$" } | Select-Object -First 1
    if (-not $checksumLine) { throw "SHA-256 de $zipName ausente." }
    $expected = ($checksumLine -split '\s+')[0].ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLowerInvariant()
    if ($expected -ne $actual) { throw "SHA-256 incorrecto: esperado $expected, obtenido $actual" }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $root = [IO.Path]::GetFullPath($WorkDir) + [IO.Path]::DirectorySeparatorChar
        foreach ($entry in $zip.Entries) {
            $target = [IO.Path]::GetFullPath((Join-Path $WorkDir $entry.FullName))
            if (-not $target.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw "El ZIP contiene una ruta insegura." }
        }
    } finally { $zip.Dispose() }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $WorkDir -Force
    $Source = Join-Path $WorkDir "FlowMobile-$Version"
    if (-not (Test-Path (Join-Path $Source "main.py")) -or -not (Test-Path (Join-Path $Source "flow")) -or -not (Test-Path (Join-Path $Source "SECURITY_MANIFEST.sha256"))) { throw "Paquete incompleto." }
    Invoke-Logged { & $Python (Join-Path $Source "scripts\security_manifest.py") --check $Source } "verificar manifiesto" | Out-Null
    Complete-Stage "SHA-256 y manifiesto"

    Start-Stage "Instalando" "FM-WINDOWS-PIP"
    if (Test-Path $BackupDir) { Remove-Item -Recurse -Force $BackupDir }
    if (Test-Path $AppDir) { Move-Item $AppDir $BackupDir; $BackupReady = $true }
    Move-Item $Source $AppDir
    $NewInstalled = $true
    foreach ($item in @(".flowmobile", "flow_settings.json", "Downloads")) {
        $old = Join-Path $BackupDir $item
        if (-not (Test-Path $old)) { $old = Join-Path $PreservedDir $item }
        if (Test-Path $old) { Copy-Item -Recurse -Force $old (Join-Path $AppDir $item) }
    }
    [IO.File]::WriteAllText((Join-Path $AppDir ".flowmobile-source"), "$Repository`n", [Text.UTF8Encoding]::new($false))
    Invoke-Logged { & $Python -m venv (Join-Path $AppDir ".venv") } "crear entorno Python" | Out-Null
    $VenvPython = Join-Path $AppDir ".venv\Scripts\python.exe"
    Invoke-Logged { & $VenvPython -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --no-deps --upgrade --quiet --progress-bar=off --retries 1 --timeout 30 -r (Join-Path $AppDir "requirements.lock") } "pip requirements.lock" | Out-Null
    Invoke-Logged { & $VenvPython -c "import sys; sys.path.insert(0, r'$AppDir'); import yt_dlp; from flow import APP_VERSION; assert APP_VERSION == '$Version'" } "prueba interna" | Out-Null
    Complete-Stage "aplicación y dependencias"

    Start-Stage "Activando flow" "FM-WINDOWS-LAUNCHER"
    $launcher = Join-Path $BinDir "flow.cmd"
    [IO.File]::WriteAllText($launcher, "@echo off`r`n`"$VenvPython`" `"$AppDir\main.py`" %*`r`n", [Text.ASCIIEncoding]::new())
    Add-UserPath $BinDir
    Invoke-Logged { & $launcher --health-check } "flow --health-check" | Out-Null
    if ($BackupReady) { Remove-Item -Recurse -Force $BackupDir; $BackupReady = $false }
    if (Test-Path $PreservedDir) { Remove-Item -Recurse -Force $PreservedDir }
    Complete-Stage "comando registrado"

    Write-Host ""
    Write-Host "✓ FlowMobile $Version instalado correctamente." -ForegroundColor Green
    Write-Host "Comando: flow"
    Write-Host "Vídeos: $DownloadsRoot\FlowMobile\Videos"
    Write-Host "Audios: $DownloadsRoot\FlowMobile\Audio"
    Write-Host "Registro: $LogFile"
} catch {
    Write-Log "$($_.Exception.GetType().Name): $($_.Exception.Message)"
    if ($NewInstalled -and (Test-Path $AppDir)) { Remove-Item -Recurse -Force $AppDir -ErrorAction SilentlyContinue }
    if ($BackupReady -and (Test-Path $BackupDir)) {
        Move-Item $BackupDir $AppDir -Force
        Write-Host "Se restauró la versión anterior." -ForegroundColor Yellow
    }
    Show-Failure $_.Exception
    if ($Auto) { exit 1 }
    return
} finally {
    if (Test-Path $WorkDir) { Remove-Item -Recurse -Force $WorkDir -ErrorAction SilentlyContinue }
}
