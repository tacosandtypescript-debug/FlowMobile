from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import re
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
    repository: str | None = None
    release_notes: tuple[str, ...] = ()
    ffmpeg_pending: bool = False
    error: str = ""


DEFAULT_REPOSITORY = "tacosandtypescript-debug/FlowMobile"


def _version_parts(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value))


def is_newer(candidate: str | None, current: str) -> bool:
    return bool(candidate) and _version_parts(candidate or "") > _version_parts(current)


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


def check_available_updates() -> UpdateCheck:
    repository = configured_repository()
    check = UpdateCheck(repository=repository)
    errors: list[str] = []
    try:
        import json

        data = json.loads(_read_url("https://pypi.org/pypi/yt-dlp/json"))
        check.ytdlp_latest = str(data.get("info", {}).get("version") or "") or None
    except (OSError, ValueError, URLError) as exc:
        errors.append(f"yt-dlp: {exc}")

    if repository:
        try:
            check.flow_latest = _read_url(
                f"https://raw.githubusercontent.com/{repository}/main/VERSION"
            )
        except (OSError, UnicodeError, URLError) as exc:
            errors.append(f"FlowMobile: {exc}")
        if check.flow_latest:
            try:
                changelog = _read_url(
                    f"https://raw.githubusercontent.com/{repository}/main/CHANGELOG.md"
                )
                check.release_notes = release_notes_for_version(
                    changelog,
                    check.flow_latest,
                )
            except (OSError, UnicodeError, URLError):
                # La versión sigue siendo válida aunque GitHub no entregue las notas.
                pass
    if PLATFORM.is_termux:
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
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    if PLATFORM.is_termux:
        command.extend(["--upgrade", "--quiet", "yt-dlp[default]"])
    else:
        command.extend([
            "--no-deps", "--upgrade", "--quiet", "--retries", "1",
            "--timeout", "15", "yt-dlp", "yt-dlp-ejs",
        ])
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


def update_flowmobile(repository: str) -> UpdateResult:
    url = f"https://raw.githubusercontent.com/{repository}/main/install.sh"
    path: Path | None = None
    try:
        script = _read_url(url, timeout=15)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".sh",
            delete=False,
        ) as handle:
            handle.write(script)
            path = Path(handle.name)
        result = subprocess.run(
            ["sh", str(path), repository, "--auto"],
            check=False,
        )
        if result.returncode == 0:
            return UpdateResult(True, changed=True)
        return UpdateResult(False, detail="El instalador de FlowMobile devolvió un error.")
    except (OSError, UnicodeError, URLError) as exc:
        return UpdateResult(False, detail=str(exc))
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def update_ffmpeg() -> UpdateResult:
    if not PLATFORM.is_termux:
        return UpdateResult(True, detail="FFmpeg está gestionado por a-Shell.")
    try:
        result = subprocess.run(
            ["pkg", "install", "-y", "ffmpeg"],
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
