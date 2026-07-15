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


def termux_shared_downloads() -> Path | None:
    if not PLATFORM.is_termux:
        return None
    home = Path.home()
    candidates = [
        home / "storage" / "downloads",
        Path("/storage/emulated/0/Download"),
    ]
    return next(
        (path for path in candidates if path.exists() and os.access(path, os.W_OK)),
        None,
    )
