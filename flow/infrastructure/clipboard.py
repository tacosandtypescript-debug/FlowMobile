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
    if platform.is_ashell:
        commands = (["pbpaste"],)
    elif platform.is_termux:
        commands = (["termux-clipboard-get"],)
    elif platform.is_windows:
        commands = (["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],)
    else:
        commands = (
            ["wl-paste", "--no-newline"],
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "--clipboard", "--output"],
        )
    for command in commands:
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return extract_web_urls(result.stdout)
    return []
