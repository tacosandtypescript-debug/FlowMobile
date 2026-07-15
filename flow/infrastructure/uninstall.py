from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil

from flow.infrastructure.paths import BASE_DIR, DOWNLOAD_DIR
from flow.infrastructure.platform import PLATFORM, PlatformInfo


PROFILE_START = "# >>> FlowMobile launcher >>>"
PROFILE_END = "# <<< FlowMobile launcher <<<"
PRESERVED_ITEMS = {"Downloads", ".flowmobile", "flow_settings.json"}


@dataclass(slots=True)
class UninstallResult:
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

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
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        result.removed.append(str(path))
    except OSError as exc:
        result.errors.append(f"{path}: {exc}")


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
    download_directory: Path = DOWNLOAD_DIR,
    platform: PlatformInfo = PLATFORM,
    home: Path | None = None,
) -> UninstallResult:
    """Quita código y lanzadores; opcionalmente elimina absolutamente todos los datos."""
    app_directory = _validate_app_directory(app_directory)
    documents = documents_directory(home)
    result = UninstallResult()
    _remove_launcher(app_directory, platform, documents, result)

    download_directory = download_directory.resolve()
    download_is_inside_app = download_directory == app_directory / "Downloads"
    if purge_all:
        if not download_is_inside_app and download_directory.exists():
            if download_directory.name != "FlowMobile":
                raise ValueError("FlowMobile se negó a borrar una carpeta de descargas no reconocida.")
            _remove_path(download_directory, result)
        _remove_path(app_directory, result)
        return result

    for child in list(app_directory.iterdir()):
        if child.name in PRESERVED_ITEMS:
            continue
        _remove_path(child, result)
    return result
