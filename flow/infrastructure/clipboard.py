from __future__ import annotations

import subprocess
from typing import Callable

from flow.domain.urls import extract_web_urls
from flow.infrastructure.platform import PLATFORM, PlatformInfo


Runner = Callable[..., subprocess.CompletedProcess[str]]


def clipboard_urls(
    platform: PlatformInfo = PLATFORM,
    runner: Runner = subprocess.run,
) -> list[str]:
    """Lee únicamente URLs del portapapeles y falla silenciosamente si no hay API."""
    command = ["pbpaste"] if platform.is_ashell else ["termux-clipboard-get"]
    try:
        result = runner(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return extract_web_urls(result.stdout)
