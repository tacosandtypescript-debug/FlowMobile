from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
import time
import yt_dlp

from flow.domain.cancellation import DownloadCancelled
from flow.infrastructure.paths import AUDIO_DIR, VIDEO_DIR
from flow.infrastructure.resume import register_partial_files
from flow.infrastructure.sessions import cookie_options


class SilentLogger:
    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


def retry_delay(attempt: int) -> float:
    """Espera exponencial limitada para no bombardear servicios móviles."""
    return float(min(30, 2 ** max(0, attempt)))


def common_options(progress_hook: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": SilentLogger(),
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "retry_sleep_functions": {
            "http": retry_delay,
            "fragment": retry_delay,
            "extractor": retry_delay,
        },
        "sleep_interval_requests": 0.75,
        "socket_timeout": 30,
        "continuedl": True,
        "nopart": False,
    }
    options.update(cookie_options())
    return options


def inspect(url: str) -> dict[str, Any]:
    options = common_options(lambda _: None)
    options.update({"skip_download": True, "progress_hooks": []})

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries")
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                return entry
    return info


def playlist_urls(url: str) -> list[str]:
    options = common_options(lambda _: None)
    options.update({
        "skip_download": True,
        "progress_hooks": [],
        "noplaylist": False,
        "extract_flat": "in_playlist",
    })
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries") if isinstance(info, dict) else None
    urls: list[str] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        candidates = (
            entry.get("webpage_url"),
            entry.get("original_url"),
            entry.get("url"),
        )
        selected = next(
            (value for value in candidates if isinstance(value, str) and value.startswith(("http://", "https://"))),
            None,
        )
        if selected is None and entry.get("id") and str(entry.get("ie_key") or "").casefold() == "youtube":
            selected = f"https://www.youtube.com/watch?v={entry['id']}"
        if selected:
            urls.append(selected)
    return list(dict.fromkeys(urls))


def available_resolutions(info: dict[str, Any]) -> list[int]:
    values: set[int] = set()
    for fmt in info.get("formats") or []:
        if not isinstance(fmt, dict):
            continue
        height = fmt.get("height")
        width = fmt.get("width")
        vcodec = fmt.get("vcodec")
        protocol = fmt.get("protocol")
        if (
            vcodec in (None, "none", "images")
            or protocol == "mhtml"
            or fmt.get("has_drm") is True
        ):
            continue
        if isinstance(width, int) and width > 0 and isinstance(height, int) and height > 0:
            values.add(min(width, height))
        elif isinstance(height, int) and height > 0:
            values.add(height)
    return sorted(values, reverse=True)


def estimate_size(
    info: dict[str, Any],
    height: int | None,
    audio_only: bool = False,
) -> int | None:
    video_sizes: list[int] = []
    combined_sizes: list[int] = []
    audio_sizes: list[int] = []
    for fmt in info.get("formats") or []:
        if not isinstance(fmt, dict) or fmt.get("has_drm") is True:
            continue
        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")
        fmt_height = fmt.get("height")
        fmt_width = fmt.get("width")
        size = fmt.get("filesize") or fmt.get("filesize_approx")

        if not isinstance(size, (int, float)) or size <= 0:
            continue

        if audio_only:
            if vcodec in (None, "none") and acodec not in (None, "none"):
                audio_sizes.append(int(size))
        else:
            if vcodec in (None, "none"):
                continue
            resolution = (
                min(fmt_width, fmt_height)
                if isinstance(fmt_width, int) and isinstance(fmt_height, int)
                else fmt_height
            )
            if height is None or resolution == height or (
                isinstance(resolution, int) and resolution <= height
            ):
                if acodec in (None, "none"):
                    video_sizes.append(int(size))
                else:
                    combined_sizes.append(int(size))

    if audio_only:
        return max(audio_sizes) if audio_sizes else None

    if video_sizes:
        for fmt in info.get("formats") or []:
            if not isinstance(fmt, dict) or fmt.get("has_drm") is True:
                continue
            if fmt.get("vcodec") not in (None, "none"):
                continue
            if fmt.get("acodec") in (None, "none"):
                continue
            size = fmt.get("filesize") or fmt.get("filesize_approx")
            if isinstance(size, (int, float)) and size > 0:
                audio_sizes.append(int(size))
        return max(video_sizes) + (max(audio_sizes) if audio_sizes else 0)

    return max(combined_sizes) if combined_sizes else None


def result_file(info: dict[str, Any], folder: Path) -> Path | None:
    paths: list[str] = []
    for key in ("filepath", "_filename"):
        value = info.get(key)
        if isinstance(value, str):
            paths.append(value)
    for item in info.get("requested_downloads") or []:
        if isinstance(item, dict):
            for key in ("filepath", "_filename"):
                value = item.get(key)
                if isinstance(value, str):
                    paths.append(value)

    for value in reversed(paths):
        path = Path(value)
        try:
            if (
                path.exists()
                and path.is_file()
                and path.parent.resolve() == folder.resolve()
            ):
                return path
        except OSError:
            continue
    return None


def newest_file(folder: Path, since: float) -> Path | None:
    candidates: list[Path] = []
    for path in folder.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in {".part", ".ytdl", ".json"}:
            continue
        try:
            if path.stat().st_mtime >= since - 2:
                candidates.append(path)
        except OSError:
            pass
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def download(
    url: str,
    kind: str,
    height: int | None,
    progress_hook: Callable[[dict[str, Any]], None],
    video_dir: Path = VIDEO_DIR,
    audio_dir: Path = AUDIO_DIR,
) -> tuple[dict[str, Any], Path]:
    options = common_options(progress_hook)
    started = time.time()

    if kind == "audio":
        target_dir = audio_dir
        options.update({
            "format": "bestaudio[ext=m4a]/bestaudio/best[acodec!=none]",
            "outtmpl": str(target_dir / "%(title).120B [%(id)s].%(ext)s"),
        })
    else:
        target_dir = video_dir
        selector = "bestvideo*+bestaudio/best"
        options.update({
            "format": selector,
            "outtmpl": str(target_dir / "%(title).120B [%(id)s].%(ext)s"),
            "merge_output_format": "mkv",
        })
        if height is not None:
            # `res` usa la dimensión menor y funciona también con video vertical.
            options["format_sort"] = [f"res:{height}"]

    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except (DownloadCancelled, KeyboardInterrupt) as error:
        partials: list[Path] = []
        for path in target_dir.rglob("*.part"):
            try:
                if path.stat().st_mtime >= started - 2:
                    partials.append(path)
            except OSError:
                pass
        register_partial_files(partials)
        if isinstance(error, DownloadCancelled):
            error.partial_files = partials
            raise
        raise DownloadCancelled(partials) from None

    final_file = result_file(info, target_dir) or newest_file(target_dir, started)

    if not final_file or not final_file.exists():
        raise RuntimeError("No pude localizar el archivo descargado.")

    return info, final_file
