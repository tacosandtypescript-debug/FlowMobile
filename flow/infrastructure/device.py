from __future__ import annotations

import mimetypes
from pathlib import Path
import shutil
import subprocess

from flow.infrastructure.platform import PLATFORM


def _run(command: list[str]) -> bool:
    try:
        return subprocess.run(command, check=False, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def scan_media(path: Path) -> bool:
    """Pide a Android indexar el archivo cuando Termux:API está disponible."""
    if not PLATFORM.is_termux:
        return True
    if shutil.which("termux-media-scan") is None:
        return False
    return _run(["termux-media-scan", path.as_posix()])


def open_share(path: Path) -> bool:
    portable_path = path.as_posix()
    if PLATFORM.is_termux:
        scan_media(path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if _run([
            "termux-open",
            "--send",
            "--chooser",
            "--content-type",
            content_type,
            portable_path,
        ]):
            return True
        if shutil.which("termux-share") is not None:
            return _run([
                "termux-share",
                "-a", "send",
                "-c", content_type,
                portable_path,
            ])
        return False
    return _run(["open", portable_path])


def play_media(path: Path) -> bool:
    portable_path = path.as_posix()
    if PLATFORM.is_termux:
        return _run(["termux-open", portable_path])
    return _run(["play", portable_path])


def notify_complete(path: Path) -> bool:
    """Usa notificación Android cuando existe y conserva el timbre universal."""
    print("\a", end="", flush=True)
    if not PLATFORM.is_termux:
        return True
    scan_media(path)
    return _run([
        "termux-notification",
        "--title", "FlowMobile",
        "--content", f"Descarga terminada: {path.name}",
    ])
