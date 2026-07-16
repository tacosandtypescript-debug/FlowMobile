from __future__ import annotations

import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse

from flow.infrastructure.platform import PLATFORM


def _run(command: list[str]) -> bool:
    try:
        return subprocess.run(command, check=False, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def scan_media(path: Path) -> bool:
    """Registra el archivo en MediaStore con API o con el broadcast de Android."""
    if not PLATFORM.is_termux:
        return True
    if shutil.which("termux-media-scan") is not None:
        if _run(["termux-media-scan", path.as_posix()]):
            return True
    user_id = os.environ.get("TERMUX__USER_ID", "0")
    if not user_id.isdecimal() or (len(user_id) > 1 and user_id.startswith("0")):
        user_id = "0"
    portable_path = path.as_posix()
    if not portable_path.startswith("/"):
        portable_path = path.resolve().as_posix()
    return _run([
        "/system/bin/am",
        "broadcast",
        "--user", user_id,
        "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
        "-d", f"file://{portable_path}",
    ])


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


def open_url(url: str) -> bool:
    """Abre una URL web sin pasarla por un intérprete de órdenes."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if PLATFORM.is_termux:
        if shutil.which("termux-open-url") is not None:
            return _run(["termux-open-url", url])
        return _run(["termux-open", url])
    return _run(["open", url])


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
