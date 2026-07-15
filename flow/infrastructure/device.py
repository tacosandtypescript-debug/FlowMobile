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
    if PLATFORM.is_termux:
        return _run(["termux-open", "--send", str(path)])
    return _run(["open", str(path)])


def play_media(path: Path) -> bool:
    if PLATFORM.is_termux:
        return _run(["termux-open", str(path)])
    return _run(["play", str(path)])


def notify_complete(path: Path) -> bool:
    """Usa notificación Android cuando existe y conserva el timbre universal."""
    print("\a", end="", flush=True)
    if not PLATFORM.is_termux:
        return True
    return _run([
        "termux-notification",
        "--title", "FlowMobile",
        "--content", f"Descarga terminada: {path.name}",
    ])
