from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
import time

from flow.infrastructure.ffmpeg import command_available, tools_status
from flow.infrastructure.paths import AUDIO_DIR, BASE_DIR, BATCH_DIR, VIDEO_DIR
from flow.infrastructure.platform import PLATFORM
from flow.infrastructure.resume import protected_partial_files
from flow.infrastructure.updates import UpdateResult, update_ffmpeg, update_ytdlp


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class CleanupResult:
    removed: int
    recovered_bytes: int
    failed: int = 0


def _package_status(distribution: str, label: str) -> DependencyStatus:
    try:
        installed = version(distribution)
        return DependencyStatus(label, True, installed)
    except PackageNotFoundError:
        return DependencyStatus(label, False, "no instalado")


def dependency_statuses() -> list[DependencyStatus]:
    ffmpeg, ffprobe = tools_status()
    return [
        DependencyStatus("Python", sys.version_info >= (3, 10), sys.version.split()[0]),
        _package_status("yt-dlp", "yt-dlp"),
        _package_status("yt-dlp-ejs", "EJS"),
        DependencyStatus("FFmpeg", ffmpeg, "disponible" if ffmpeg else "no encontrado"),
        DependencyStatus("FFprobe", ffprobe, "disponible" if ffprobe else "no encontrado"),
    ]


def repair_dependencies() -> list[tuple[str, UpdateResult]]:
    results: list[tuple[str, UpdateResult]] = []
    if PLATFORM.is_ashell:
        try:
            from pip._internal.cli.main import main as pip_main

            code = pip_main([
                "install", "--disable-pip-version-check", "--require-hashes",
                "--only-binary=:all:", "--no-deps", "--upgrade", "-r",
                str(BASE_DIR / "requirements.lock"),
            ])
            results.append((
                "yt-dlp + EJS",
                UpdateResult(code == 0, changed=code == 0, detail="" if code == 0 else "pip devolvió un error"),
            ))
        except (ImportError, OSError) as exc:
            results.append(("yt-dlp + EJS", UpdateResult(False, detail=str(exc))))
    else:
        results.append(("yt-dlp + EJS", update_ytdlp()))

    ffmpeg, ffprobe = tools_status()
    if (PLATFORM.is_termux or PLATFORM.is_desktop) and (not ffmpeg or not ffprobe):
        results.append(("FFmpeg + FFprobe", update_ffmpeg()))
    elif PLATFORM.is_ashell and (not ffmpeg or not ffprobe):
        results.append((
            "FFmpeg + FFprobe",
            UpdateResult(False, detail="En iOS forman parte de a-Shell; actualiza la app completa."),
        ))
    else:
        results.append(("FFmpeg + FFprobe", UpdateResult(True, detail="ya disponibles")))
    command_available.cache_clear()
    return results


def is_temporary_download(path: Path) -> bool:
    lowered = path.name.lower()
    return (
        path.suffix.lower() in {".part", ".ytdl", ".tmp"}
        or "[convirtiendo]" in lowered
        or "[extrayendo]" in lowered
    )


def clean_temporary_files(
    roots: tuple[Path, ...] | None = None,
    minimum_age_seconds: int = 300,
    now: float | None = None,
) -> CleanupResult:
    """Elimina solo restos incompletos antiguos; nunca toca medios terminados."""
    current_time = time.time() if now is None else now
    removed = recovered = failed = 0
    protected = protected_partial_files()
    for root in roots or (VIDEO_DIR, AUDIO_DIR, BATCH_DIR):
        if not root.exists():
            continue
        try:
            candidates = list(root.rglob("*"))
        except OSError:
            failed += 1
            continue
        for path in candidates:
            try:
                if not path.is_file() or not is_temporary_download(path):
                    continue
                if path.resolve() in protected:
                    continue
                stat = path.stat()
                if current_time - stat.st_mtime < minimum_age_seconds:
                    continue
                size = stat.st_size
                path.unlink()
                removed += 1
                recovered += size
            except OSError:
                failed += 1
    return CleanupResult(removed, recovered, failed)
