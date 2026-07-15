from __future__ import annotations

import select
import sys
from pathlib import Path


class DownloadCancelled(RuntimeError):
    def __init__(self, partial_files: list[Path] | None = None) -> None:
        super().__init__("Descarga cancelada; el progreso parcial se conservó.")
        self.partial_files = partial_files or []


def cancellation_requested() -> bool:
    """Detecta `c + Enter` sin detener la descarga mientras no haya entrada."""
    try:
        readable, _, _ = select.select([sys.stdin], [], [], 0)
        if not readable:
            return False
        return sys.stdin.readline().strip().casefold() in {"c", "cancelar"}
    except (OSError, ValueError, AttributeError):
        return False
