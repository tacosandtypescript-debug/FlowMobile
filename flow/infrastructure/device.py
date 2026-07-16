from __future__ import annotations

from pathlib import Path
import subprocess

from flow.infrastructure.platform import PLATFORM


def _run(command: list[str]) -> bool:
    try:
        return subprocess.run(command, check=False).returncode == 0
    except OSError:
        return False


def open_share(path: Path) -> bool:
    portable_path = path.as_posix()
    if PLATFORM.is_termux:
        return _run(["termux-share", portable_path])
    return _run(["open", portable_path])


def play_media(path: Path) -> bool:
    portable_path = path.as_posix()
    if PLATFORM.is_termux:
        return _run(["termux-open", "--view", portable_path])
    return _run(["play", portable_path])


def notify_complete(path: Path) -> bool:
    """Usa notificación Android cuando existe y conserva el timbre universal."""
    print("\a", end="", flush=True)
    if not PLATFORM.is_termux:
        return True
    
    _run(["termux-media-scan", path.as_posix()])

    return _run([
        "termux-notification",
        "--title", "FlowMobile",
        "--content", f"Descarga terminada: {path.name}",
    ])
