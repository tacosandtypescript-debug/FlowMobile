from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MediaInfo:
    url: str
    title: str
    uploader: str
    platform: str
    duration: int | float | None
    raw: dict[str, Any]


@dataclass(slots=True)
class DownloadChoice:
    kind: str
    height: int | None = None
    audio_format: str = "auto"


@dataclass(slots=True)
class DownloadResult:
    ok: bool
    file: Path | None = None
    error: Exception | None = None
    warning: str | None = None
    quality: str | None = None
