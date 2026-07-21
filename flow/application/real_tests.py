from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path

from flow.domain.models import DownloadChoice
from flow.infrastructure.ffmpeg import MediaProbe, probe_media
from flow.infrastructure.paths import STATE_DIR
from flow.infrastructure.privacy import protect_private_path


@dataclass(frozen=True, slots=True)
class RealTestCase:
    label: str
    choice: DownloadChoice


@dataclass(frozen=True, slots=True)
class Verification:
    ok: bool
    summary: str
    size: int
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    share_ready: bool = False


def quick_cases() -> tuple[RealTestCase, ...]:
    return (
        RealTestCase("Video 360p", DownloadChoice("video", 360)),
        RealTestCase("Audio M4A", DownloadChoice("audio", audio_format="m4a")),
    )


def full_cases() -> tuple[RealTestCase, ...]:
    return (
        RealTestCase("Video 360p", DownloadChoice("video", 360)),
        RealTestCase("Video 720p", DownloadChoice("video", 720)),
        RealTestCase("Video 1080p", DownloadChoice("video", 1080)),
        RealTestCase("Video máxima", DownloadChoice("video", None)),
        RealTestCase("Audio M4A", DownloadChoice("audio", audio_format="m4a")),
        RealTestCase("Audio MP3", DownloadChoice("audio", audio_format="mp3")),
    )


def verify_download(
    path: Path,
    choice: DownloadChoice,
    probe: MediaProbe | None = None,
) -> Verification:
    try:
        size = path.stat().st_size
    except OSError:
        return Verification(False, "archivo no encontrado", 0)
    inspected = probe if probe is not None else probe_media(path)
    if size <= 0:
        return Verification(False, "archivo vacío", size)
    if inspected is None:
        return Verification(False, "FFprobe no pudo abrir el archivo", size)

    if choice.kind == "video":
        if not inspected.video_codec or not inspected.width or not inspected.height:
            return Verification(False, "no contiene un flujo de vídeo válido", size)
        short_side = min(inspected.width, inspected.height)
        if choice.height is not None and short_side > choice.height:
            return Verification(
                False,
                f"resolución {short_side}p supera el límite {choice.height}p",
                size,
                inspected.width,
                inspected.height,
                inspected.video_codec,
                inspected.audio_codec,
                True,
            )
        summary = (
            f"{inspected.width}×{inspected.height} · "
            f"{inspected.video_codec.upper()} · "
            f"audio {(inspected.audio_codec or 'no detectado').upper()}"
        )
    else:
        if not inspected.audio_codec:
            return Verification(False, "no contiene un flujo de audio válido", size)
        expected_suffix = ".mp3" if choice.audio_format == "mp3" else ".m4a"
        if path.suffix.lower() != expected_suffix:
            return Verification(
                False,
                f"se esperaba {expected_suffix.upper()} y se obtuvo {path.suffix.upper()}",
                size,
                audio_codec=inspected.audio_codec,
                share_ready=True,
            )
        summary = f"{path.suffix[1:].upper()} · {inspected.audio_codec.upper()}"

    return Verification(
        True,
        summary,
        size,
        inspected.width,
        inspected.height,
        inspected.video_codec,
        inspected.audio_codec,
        True,
    )


def save_report(rows: list[dict[str, object]]) -> Path:
    report_dir = STATE_DIR / "diagnostics"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = report_dir / f"real-test-{stamp}.json"
    target.write_text(
        json.dumps({"created": datetime.now().isoformat(), "results": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not protect_private_path(target):
        target.unlink(missing_ok=True)
        raise OSError("No se pudo proteger el informe de pruebas reales.")
    return target


def verification_dict(verification: Verification) -> dict[str, object]:
    return asdict(verification)
