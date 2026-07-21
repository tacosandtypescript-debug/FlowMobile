from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
import hashlib
import os
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen

from flow.infrastructure.paths import BASE_DIR
from flow.infrastructure.platform import PLATFORM


@dataclass(slots=True)
class UpdateResult:
    ok: bool
    changed: bool = False
    detail: str = ""


@dataclass(slots=True)
class UpdateCheck:
    flow_latest: str | None = None
    ytdlp_latest: str | None = None
    ytdlp_locked: str | None = None
    repository: str | None = None
    flow_ref: str | None = None
    release_notes: tuple[str, ...] = ()
    ffmpeg_pending: bool = False
    error: str = ""


DEFAULT_REPOSITORY = "tacosandtypescript-debug/FlowMobile"


def _version_parts(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value))


def is_newer(candidate: str | None, current: str) -> bool:
    return bool(candidate) and _version_parts(candidate or "") > _version_parts(current)


def locked_dependency_version(distribution: str) -> str | None:
    lockfile = BASE_DIR / "requirements.lock"
    try:
        content = lockfile.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    pattern = rf"(?mi)^{re.escape(distribution)}==([^\s\\]+)"
    match = re.search(pattern, content)
    return match.group(1) if match else None


def release_notes_for_version(changelog: str, target_version: str) -> tuple[str, ...]:
    """Extrae las novedades de una versión publicada en CHANGELOG.md."""
    notes: list[str] = []
    inside_target = False
    for raw_line in changelog.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if inside_target:
                break
            heading = line[3:].strip()
            inside_target = heading == target_version or heading.startswith(
                target_version + " "
            )
            continue
        if inside_target and line.startswith("- "):
            notes.append(line[2:].strip())
            if len(notes) == 5:
                break
    return tuple(notes)


def release_notes_from_body(body: str) -> tuple[str, ...]:
    notes: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith(("- ", "* ")):
            notes.append(line[2:].strip())
        if len(notes) == 5:
            break
    return tuple(note for note in notes if note)


def configured_repository() -> str | None:
    environment = (
        os.environ.get("FLOWMOBILE_REPOSITORY", "")
        or os.environ.get("FLOWIOS_REPOSITORY", "")
    ).strip()
    if not environment:
        source_file = BASE_DIR / ".flowmobile-source"
        try:
            environment = source_file.read_text(encoding="utf-8").strip()
        except OSError:
            legacy_source = BASE_DIR / ".flowios-source"
            try:
                environment = legacy_source.read_text(encoding="utf-8").strip()
            except OSError:
                environment = DEFAULT_REPOSITORY
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", environment):
        return None
    return environment


def _read_url(url: str, timeout: int = 5) -> str:
    request = Request(url, headers={"User-Agent": "FlowMobile-update-check"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8").strip()


def _expected_checksum(checksums: str, filename: str) -> str | None:
    for line in checksums.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].lstrip("*") == filename:
            return parts[0].lower()
    return None


def _verified_release_asset(repository: str, reference: str, filename: str) -> bytes:
    if not re.fullmatch(r"v?\d+(?:\.\d+){1,3}", reference):
        raise ValueError("La actualización no corresponde a una versión publicada.")
    base = f"https://github.com/{repository}/releases/download/{reference}"
    checksums = _read_url(f"{base}/SHA256SUMS", timeout=15)
    expected = _expected_checksum(checksums, filename)
    if not expected:
        raise ValueError(f"La versión no publica la firma SHA-256 de {filename}.")
    request = Request(
        f"{base}/{filename}", headers={"User-Agent": "FlowMobile-secure-update"}
    )
    with urlopen(request, timeout=20) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError(f"La verificación de seguridad de {filename} falló.")
    return payload


def check_available_updates(include_package_manager: bool = True) -> UpdateCheck:
    repository = configured_repository()
    check = UpdateCheck(repository=repository)
    errors: list[str] = []
    check.ytdlp_locked = locked_dependency_version("yt-dlp")
    try:
        data = json.loads(_read_url("https://pypi.org/pypi/yt-dlp/json"))
        check.ytdlp_latest = str(data.get("info", {}).get("version") or "") or None
    except (OSError, ValueError, URLError) as exc:
        errors.append(f"yt-dlp: {exc}")

    if repository:
        try:
            release = json.loads(
                _read_url(f"https://api.github.com/repos/{repository}/releases/latest")
            )
            tag = str(release.get("tag_name") or "").strip()
            version_from_tag = tag.removeprefix("v")
            if tag and _version_parts(version_from_tag):
                check.flow_latest = version_from_tag
                check.flow_ref = tag
                check.release_notes = release_notes_from_body(
                    str(release.get("body") or "")
                )
        except (OSError, UnicodeError, ValueError, URLError):
            # Repositorios nuevos todavía pueden no tener Releases.
            pass
        if not check.flow_latest:
            errors.append("FlowMobile: no hay una versión estable publicada")
        if check.flow_latest and not check.release_notes:
            try:
                changelog = _read_url(
                    f"https://raw.githubusercontent.com/{repository}/{check.flow_ref or 'main'}/CHANGELOG.md"
                )
                check.release_notes = release_notes_for_version(changelog, check.flow_latest)
            except (OSError, UnicodeError, URLError):
                # La versión sigue siendo válida aunque GitHub no entregue las notas.
                pass
    if PLATFORM.is_termux and include_package_manager:
        try:
            refreshed = subprocess.run(
                ["pkg", "update", "-y"],
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
            )
            if refreshed.returncode != 0:
                errors.append("Termux: no se pudo actualizar el catálogo de paquetes")
            listed = subprocess.run(
                ["apt", "list", "--upgradable"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            check.ffmpeg_pending = any(
                line.lower().startswith("ffmpeg/") for line in listed.stdout.splitlines()
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"Termux: {exc}")
    check.error = " · ".join(errors)
    return check


def update_ytdlp() -> UpdateResult:
    """Actualiza yt-dlp mediante la instalación de Python que usa FlowMobile."""
    try:
        before = version("yt-dlp")
    except PackageNotFoundError:
        before = None
    lockfile = BASE_DIR / "requirements.lock"
    if not lockfile.is_file():
        return UpdateResult(False, detail="Falta requirements.lock; actualiza FlowMobile primero.")
    command = [
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
        "--require-hashes", "--only-binary=:all:", "--no-deps", "--upgrade",
        "--quiet", "--retries", "1", "--timeout", "15", "-r", str(lockfile),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return UpdateResult(False, detail=str(exc))

    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode == 0:
        try:
            after = version("yt-dlp")
        except PackageNotFoundError:
            after = None
        changed = before != after
        return UpdateResult(True, changed=changed)
    lines = output.splitlines()
    return UpdateResult(False, detail=lines[-1][:220] if lines else "pip devolvió un error.")


def update_flowmobile(repository: str, reference: str = "main") -> UpdateResult:
    if PLATFORM.is_ashell:
        try:
            from install_ios import install

            install(repository, reference)
            return UpdateResult(True, changed=True)
        except (OSError, RuntimeError, ValueError) as exc:
            return UpdateResult(False, detail=str(exc))

    path: Path | None = None
    try:
        if PLATFORM.is_windows:
            filename, suffix = "install-windows.ps1", ".ps1"
        elif PLATFORM.is_linux:
            filename, suffix = "install-linux.sh", ".sh"
        else:
            filename, suffix = "install.sh", ".sh"
        script = _verified_release_asset(repository, reference, filename)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            delete=False,
        ) as handle:
            handle.write(script)
            path = Path(handle.name)
        environment = os.environ.copy()
        environment["FLOWMOBILE_BRANCH"] = reference
        if PLATFORM.is_windows:
            command = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(path), "-Repository", repository, "-Auto",
            ]
        else:
            command = ["sh", str(path), repository, "--auto"]
        result = subprocess.run(command, check=False, env=environment)
        if result.returncode == 0:
            return UpdateResult(True, changed=True)
        return UpdateResult(False, detail="El instalador de FlowMobile devolvió un error.")
    except (OSError, UnicodeError, ValueError, URLError) as exc:
        return UpdateResult(False, detail=str(exc))
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def update_ffmpeg() -> UpdateResult:
    if PLATFORM.is_ashell:
        return UpdateResult(True, detail="FFmpeg está gestionado por a-Shell.")
    if PLATFORM.is_windows:
        command = [
            "winget", "install", "--id", "Gyan.FFmpeg", "--exact", "--silent",
            "--accept-package-agreements", "--accept-source-agreements",
        ]
    elif PLATFORM.is_linux:
        manager_commands = (
            ("apt-get", ["sudo", "apt-get", "install", "-y", "ffmpeg"]),
            ("dnf", ["sudo", "dnf", "install", "-y", "ffmpeg"]),
            ("pacman", ["sudo", "pacman", "-S", "--needed", "--noconfirm", "ffmpeg"]),
            ("zypper", ["sudo", "zypper", "--non-interactive", "install", "ffmpeg"]),
        )
        command = next((value for name, value in manager_commands if shutil.which(name)), [])
        if not command:
            return UpdateResult(False, detail="No se reconoció el gestor de paquetes de Linux.")
    else:
        command = ["pkg", "install", "-y", "ffmpeg"]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return UpdateResult(False, detail=str(exc))
    if result.returncode == 0:
        return UpdateResult(True, changed=True)
    lines = (result.stdout + result.stderr).strip().splitlines()
    return UpdateResult(False, detail=lines[-1][:220] if lines else "pkg devolvió un error.")
