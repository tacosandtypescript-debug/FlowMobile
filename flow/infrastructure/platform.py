from __future__ import annotations

from dataclasses import dataclass
import os
import platform as system_platform
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    key: str
    name: str
    mobile_os: str

    @property
    def is_termux(self) -> bool:
        return self.key == "termux"

    @property
    def is_ashell(self) -> bool:
        return self.key == "ashell"

    @property
    def is_windows(self) -> bool:
        return self.key == "windows"

    @property
    def is_linux(self) -> bool:
        return self.key == "linux"

    @property
    def is_desktop(self) -> bool:
        return self.key in {"windows", "linux"}


def detect_platform(
    environment: Mapping[str, str] | None = None,
    system: str | None = None,
) -> PlatformInfo:
    env = environment if environment is not None else os.environ
    prefix = env.get("PREFIX", "").lower()
    home = env.get("HOME", "").replace("\\", "/").lower()
    if env.get("TERMUX_VERSION") or "com.termux" in prefix:
        return PlatformInfo("termux", "Termux", "Android")
    if (
        "/mobile/containers/" in home
        or home.startswith("/private/var/mobile/")
        or (home.startswith("/private/") and home.endswith("/documents"))
    ):
        return PlatformInfo("ashell", "a-Shell", "iOS")
    current_system = (system or system_platform.system()).casefold()
    if current_system == "windows":
        return PlatformInfo("windows", "Terminal", "Windows")
    if current_system == "linux":
        return PlatformInfo("linux", "Terminal", "Linux")
    return PlatformInfo("ashell", "a-Shell", "iOS")


def desktop_downloads_directory(
    platform: PlatformInfo | None = None,
    home: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path | None:
    current = platform or PLATFORM
    if not current.is_desktop:
        return None
    current_home = home or Path.home()
    env = environment if environment is not None else os.environ
    configured = env.get("FLOWMOBILE_DOWNLOADS", "").strip()
    if configured:
        return Path(configured).expanduser()
    if current.is_linux:
        xdg = env.get("XDG_DOWNLOAD_DIR", "").strip()
        if not xdg:
            try:
                for line in (current_home / ".config" / "user-dirs.dirs").read_text(
                    encoding="utf-8"
                ).splitlines():
                    if line.startswith("XDG_DOWNLOAD_DIR="):
                        xdg = line.split("=", 1)[1].strip().strip('"')
                        break
            except (OSError, UnicodeError):
                pass
        if xdg:
            expanded = xdg.replace("$HOME", str(current_home))
            return Path(expanded).expanduser()
    return current_home / "Downloads"


PLATFORM = detect_platform()


def _directory_is_writable(path: Path) -> bool:
    """Comprueba escritura real; os.access no es fiable con permisos de Android."""
    if not path.is_dir():
        return False
    probe = path / f".flowmobile-write-test-{os.getpid()}"
    try:
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def termux_shared_downloads(
    platform: PlatformInfo | None = None,
    home: Path | None = None,
) -> Path | None:
    return termux_shared_directory("downloads", platform, home)


def termux_shared_directory(
    name: str,
    platform: PlatformInfo | None = None,
    home: Path | None = None,
) -> Path | None:
    current_platform = platform or PLATFORM
    if not current_platform.is_termux:
        return None
    current_home = home or Path.home()
    android_names = {"downloads": "Download", "movies": "Movies", "music": "Music"}
    if name not in android_names:
        raise ValueError(f"Carpeta compartida de Android no reconocida: {name}")
    candidates = [
        current_home / "storage" / name,
        Path("/storage/emulated/0") / android_names[name],
    ]
    return next((path for path in candidates if _directory_is_writable(path)), None)
