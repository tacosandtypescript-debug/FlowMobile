from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil

from flow.infrastructure.paths import AUDIO_DIR, BASE_DIR, DOWNLOAD_DIR, VIDEO_DIR
from flow.infrastructure.platform import PLATFORM, PlatformInfo


PROFILE_START = "# >>> FlowMobile launcher >>>"
PROFILE_END = "# <<< FlowMobile launcher <<<"
PRESERVED_ITEMS = {"Downloads", ".flowmobile", "flow_settings.json"}
PRESERVED_DATA_NAME = ".flowmobile-data"


@dataclass(slots=True)
class UninstallResult:
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    preserved_at: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def documents_directory(home: Path | None = None) -> Path:
    base = (home or Path.home()).expanduser()
    return base if base.name == "Documents" else base / "Documents"


def remove_profile_launcher(documents: Path) -> bool:
    profile = documents / ".profile"
    try:
        previous = profile.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    except (OSError, UnicodeError):
        return False

    cleaned: list[str] = []
    inside_block = False
    changed = False
    for line in previous.splitlines():
        stripped = line.strip()
        if stripped == PROFILE_START:
            inside_block = True
            changed = True
            continue
        if stripped == PROFILE_END:
            inside_block = False
            changed = True
            continue
        if inside_block:
            changed = True
            continue
        if re.match(r"^\s*alias\s+flow\s*=", line):
            changed = True
            continue
        cleaned.append(line)
    if changed:
        content = "\n".join(cleaned).rstrip()
        profile.write_text(content + ("\n" if content else ""), encoding="utf-8")
    return changed


def _remove_path(path: Path, result: UninstallResult) -> None:
    existed = path.exists() or path.is_symlink()
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    except OSError as exc:
        result.errors.append(f"{path}: {exc}")
        return
    if path.exists() or path.is_symlink():
        result.errors.append(f"{path}: el sistema no confirmó la eliminación")
    elif existed:
        result.removed.append(str(path))


def preserved_data_directory(app_directory: Path) -> Path:
    """Reserva privada usada al quitar el código sin borrar datos personales."""
    return app_directory.parent / PRESERVED_DATA_NAME


def _available_destination(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}.conservado-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _move_preserving(source: Path, destination: Path, result: UninstallResult) -> None:
    """Mueve datos sin sobrescribir archivos conservados por un intento anterior."""
    try:
        if source.is_dir() and not source.is_symlink() and destination.is_dir():
            for child in list(source.iterdir()):
                _move_preserving(child, destination / child.name, result)
            source.rmdir()
            return
        target = _available_destination(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    except OSError as exc:
        result.errors.append(f"{source}: no se pudo conservar: {exc}")


def _preserve_personal_data(
    app_directory: Path,
    destination: Path,
    result: UninstallResult,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in PRESERVED_ITEMS:
        source = app_directory / name
        if source.exists() or source.is_symlink():
            _move_preserving(source, destination / name, result)
    if not result.errors:
        result.preserved_at = str(destination)


def _validate_app_directory(app_directory: Path) -> Path:
    resolved = app_directory.resolve()
    if not (resolved / "main.py").is_file() or not (resolved / "flow").is_dir():
        raise ValueError("La carpeta seleccionada no parece una instalación de FlowMobile.")
    forbidden = {Path(resolved.anchor).resolve(), Path.home().resolve()}
    documents = documents_directory().resolve()
    forbidden.add(documents)
    if resolved in forbidden:
        raise ValueError("FlowMobile se negó a borrar una carpeta protegida del sistema.")
    return resolved


def _remove_launcher(
    app_directory: Path,
    platform: PlatformInfo,
    documents: Path,
    result: UninstallResult,
) -> None:
    if platform.is_ashell:
        if remove_profile_launcher(documents):
            result.removed.append(str(documents / ".profile") + " (alias flow)")
        for launcher in (documents / "bin" / "flow.py", documents / "bin" / "flow"):
            if launcher.exists():
                _remove_path(launcher, result)
        return

    launcher_name = shutil.which("flow")
    if not launcher_name:
        return
    launcher = Path(launcher_name)
    try:
        content = launcher.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        content = ""
    if "FlowMobile" in content or str(app_directory) in content:
        _remove_path(launcher, result)


def uninstall(
    purge_all: bool,
    app_directory: Path = BASE_DIR,
    download_directory: Path | None = None,
    platform: PlatformInfo = PLATFORM,
    home: Path | None = None,
) -> UninstallResult:
    """Quita código y lanzadores; opcionalmente elimina absolutamente todos los datos."""
    app_directory = _validate_app_directory(app_directory)
    documents = documents_directory(home)
    result = UninstallResult()
    _remove_launcher(app_directory, platform, documents, result)

    download_directory = download_directory or DOWNLOAD_DIR
    supplied_download_directory = download_directory
    download_directory = download_directory.resolve()
    download_is_inside_app = download_directory == app_directory / "Downloads"
    preserved_directory = preserved_data_directory(app_directory)
    if purge_all:
        media_directories = [download_directory]
        if supplied_download_directory == DOWNLOAD_DIR:
            media_directories.extend((VIDEO_DIR.resolve(), AUDIO_DIR.resolve()))
        for media_directory in dict.fromkeys(media_directories):
            if media_directory == app_directory / "Downloads" or not media_directory.exists():
                continue
            if media_directory.name != "FlowMobile":
                raise ValueError("FlowMobile se negó a borrar una carpeta de descargas no reconocida.")
            _remove_path(media_directory, result)
        if platform.is_ashell:
            from uninstall_ios import purge_flowmobile

            cleanup = purge_flowmobile(home=home, app_directory=app_directory)
            result.removed.extend(cleanup.removed)
            result.errors.extend(cleanup.errors)
            return result
        if preserved_directory.exists() or preserved_directory.is_symlink():
            _remove_path(preserved_directory, result)
        _remove_path(app_directory, result)
        return result

    _preserve_personal_data(app_directory, preserved_directory, result)
    if result.errors:
        return result
    _remove_path(app_directory, result)
    return result
