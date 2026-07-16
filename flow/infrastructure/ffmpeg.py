from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
import subprocess
import threading
from typing import Callable


@dataclass(frozen=True, slots=True)
class MediaProbe:
    size: int
    duration: float | None
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    audio_codec: str | None


@lru_cache(maxsize=None)
def command_available(name: str) -> bool:
    """Detecta también comandos internos de a-Shell que no aparecen en PATH."""
    try:
        result = subprocess.run(
            [name, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def has_encoder(name: str) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
        )
        return name in (result.stdout + result.stderr)
    except OSError:
        return False


def tools_status() -> tuple[bool, bool]:
    return command_available("ffmpeg"), command_available("ffprobe")


def probe_media(source: Path) -> MediaProbe | None:
    """Comprueba estructura, códecs, duración y resolución del archivo real."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
                "-of", "json", str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        payload = json.loads(result.stdout)
        streams = payload.get("streams") or []
        video = next(
            (stream for stream in streams if stream.get("codec_type") == "video"),
            {},
        )
        audio = next(
            (stream for stream in streams if stream.get("codec_type") == "audio"),
            {},
        )
        rate = str(video.get("r_frame_rate") or "")
        fps: float | None = None
        if "/" in rate:
            numerator, denominator = rate.split("/", 1)
            try:
                fps = float(numerator) / float(denominator)
            except (ValueError, ZeroDivisionError):
                pass
        raw_duration = (payload.get("format") or {}).get("duration")
        try:
            duration = float(raw_duration) if raw_duration is not None else None
        except (TypeError, ValueError):
            duration = None
        return MediaProbe(
            size=source.stat().st_size,
            duration=duration,
            width=video.get("width") if isinstance(video.get("width"), int) else None,
            height=video.get("height") if isinstance(video.get("height"), int) else None,
            fps=fps,
            video_codec=str(video.get("codec_name")) if video.get("codec_name") else None,
            audio_codec=str(audio.get("codec_name")) if audio.get("codec_name") else None,
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def is_ios_compatible(source: Path) -> bool:
    """Comprueba si un MP4 ya usa H.264 y audio AAC (o no tiene audio)."""
    if source.suffix.lower() not in {".mp4", ".m4v", ".mov"}:
        return False
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type,codec_name", "-of", "json", str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        streams = json.loads(result.stdout).get("streams", [])
        videos = [s for s in streams if s.get("codec_type") == "video"]
        audios = [s for s in streams if s.get("codec_type") == "audio"]
        return (
            bool(videos)
            and all(s.get("codec_name") == "h264" for s in videos)
            and all(s.get("codec_name") == "aac" for s in audios)
        )
    except (OSError, ValueError):
        return False


def media_quality(source: Path) -> str | None:
    """Lee la calidad real del archivo final mediante FFprobe."""
    probe = probe_media(source)
    if probe is None or probe.width is None or probe.height is None:
        return None
    parts = [f"{probe.width}×{probe.height}"]
    if probe.fps is not None:
        parts.append(f"{probe.fps:g} fps")
    if probe.video_codec:
        parts.append(probe.video_codec.upper())
    return " · ".join(parts)


def convert_video(
    source: Path,
    duration: float | int | None,
    progress_callback: Callable[[float], None],
) -> Path:
    if is_ios_compatible(source):
        progress_callback(100.0)
        return source

    if has_encoder("libx264"):
        encoder = "libx264"
        video_args = ["-preset", "veryfast", "-crf", "21"]
    elif has_encoder("h264_videotoolbox"):
        encoder = "h264_videotoolbox"
        video_args = ["-b:v", "8M"]
    else:
        raise RuntimeError("FFmpeg no tiene un codificador H.264 disponible.")

    target = source.with_name(source.stem + " [compatible].mp4")
    temp = source.with_name(source.stem + " [convirtiendo].mp4")

    command = [
        "ffmpeg", "-y", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-c:v", encoder, *video_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        "-nostats", "-loglevel", "error",
        str(temp),
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    output_tail: deque[str] = deque(maxlen=20)

    def _drain_stderr() -> None:
        if process.stderr is not None:
            for line in process.stderr:
                clean = line.strip()
                if clean:
                    output_tail.append(clean)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    total = float(duration or 0)
    if process.stdout is not None:
        for raw in process.stdout:
            line = raw.strip()
            if not line.startswith(("out_time_ms=", "out_time_us=")):
                continue
            try:
                seconds = int(line.split("=", 1)[1]) / 1_000_000
            except (TypeError, ValueError, IndexError):
                continue
            progress_callback(min(100.0, seconds / total * 100) if total else 0.0)

    code = process.wait()
    stderr_thread.join()

    if code != 0 or not temp.exists():
        temp.unlink(missing_ok=True)
        detail = "\n".join(output_tail)
        raise RuntimeError(detail or "FFmpeg no pudo convertir el video.")

    temp.replace(target)
    source.unlink(missing_ok=True)
    progress_callback(100.0)
    return target


def convert_audio(source: Path, preferred_format: str = "auto") -> Path:
    """Extrae un archivo de audio real, conservando el original si algo falla."""
    if source.suffix.lower() == ".m4a" and preferred_format != "mp3":
        return source

    # Muchos sitios entregan AAC dentro de un MP4. Primero intentamos extraerlo
    # sin recodificar: es rápido y no pierde calidad.
    if preferred_format != "mp3":
        copied_target = source.with_suffix(".m4a")
        copied_temp = copied_target.with_name(
            copied_target.stem + " [extrayendo]" + copied_target.suffix
        )
        try:
            copied = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(source), "-map", "0:a:0", "-vn",
                    "-c:a", "copy", "-loglevel", "error", str(copied_temp),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise RuntimeError(f"No se pudo iniciar FFmpeg desde Flow: {exc}") from exc
        if copied.returncode == 0 and copied_temp.exists():
            copied_temp.replace(copied_target)
            source.unlink(missing_ok=True)
            return copied_target
        copied_temp.unlink(missing_ok=True)

    if preferred_format == "mp3" and has_encoder("libmp3lame"):
        target = source.with_suffix(".mp3")
        codec_args = ["-c:a", "libmp3lame", "-q:a", "0"]
    elif preferred_format in {"auto", "m4a"} and has_encoder("aac"):
        target = source.with_suffix(".m4a")
        codec_args = ["-c:a", "aac", "-b:a", "192k"]
    elif preferred_format == "auto" and has_encoder("libmp3lame"):
        target = source.with_suffix(".mp3")
        codec_args = ["-c:a", "libmp3lame", "-q:a", "0"]
    else:
        raise RuntimeError(
            "FFmpeg no tiene un codificador MP3 o AAC disponible. El archivo "
            "original se conservó."
        )

    temp = target.with_name(target.stem + " [convirtiendo]" + target.suffix)
    command = [
        "ffmpeg", "-y",
        "-i", str(source),
        "-vn",
        *codec_args,
        "-loglevel", "error",
        str(temp),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0 or not temp.exists():
        temp.unlink(missing_ok=True)
        detail = result.stderr.strip().splitlines()
        reason = detail[-1] if detail else "FFmpeg no pudo extraer el audio."
        raise RuntimeError(reason)

    temp.replace(target)
    if source != target:
        source.unlink(missing_ok=True)
    return target
