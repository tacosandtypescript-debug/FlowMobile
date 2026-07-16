from __future__ import annotations

from dataclasses import dataclass
import os
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


def detect_platform(environment: Mapping[str, str] | None = None) -> PlatformInfo:
    env = environment if environment is not None else os.environ
    prefix = env.get("PREFIX", "").lower()
    if env.get("TERMUX_VERSION") or "com.termux" in prefix:
        return PlatformInfo("termux", "Termux", "Android")
    return PlatformInfo("ashell", "a-Shell", "iOS")


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
    current_platform = platform or PLATFORM
    if not current_platform.is_termux:
        return None
    current_home = home or Path.home()
    candidates = [
        current_home / "storage" / "downloads",
        Path("/storage/emulated/0/Download"),
    ]
    return next((path for path in candidates if _directory_is_writable(path)), None)
