from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from flow.domain.models import MediaInfo, DownloadChoice, DownloadResult
from flow.domain.cancellation import DownloadCancelled
from flow.domain.sites import platform_name
from flow.infrastructure import ytdlp_gateway
from flow.infrastructure.ffmpeg import convert_audio, convert_video, media_quality
from flow.infrastructure.history import HistoryError, save_history


class MediaService:
    def playlist_urls(self, url: str) -> list[str]:
        return ytdlp_gateway.playlist_urls(url)

    def inspect(self, url: str) -> MediaInfo:
        info = ytdlp_gateway.inspect(url)
        return MediaInfo(
            url=url,
            title=info.get("title") or "Sin título",
            uploader=info.get("uploader") or info.get("channel") or "Desconocido",
            platform=platform_name(url),
            duration=info.get("duration"),
            raw=info,
        )

    def resolutions(self, media: MediaInfo) -> list[int]:
        return ytdlp_gateway.available_resolutions(media.raw)

    def estimated_size(
        self,
        media: MediaInfo,
        choice: DownloadChoice,
    ) -> int | None:
        return ytdlp_gateway.estimate_size(
            media.raw,
            choice.height,
            audio_only=choice.kind == "audio",
        )

    def download(
        self,
        media: MediaInfo,
        choice: DownloadChoice,
        progress_hook: Callable[[dict[str, Any]], None],
        conversion_progress: Callable[[float], None],
        video_dir: Path | None = None,
        audio_dir: Path | None = None,
    ) -> DownloadResult:
        final_file: Path | None = None
        info: dict[str, Any] = {}
        try:
            info, final_file = ytdlp_gateway.download(
                media.url,
                choice.kind,
                choice.height,
                progress_hook,
                **({"video_dir": video_dir} if video_dir is not None else {}),
                **({"audio_dir": audio_dir} if audio_dir is not None else {}),
            )

            if choice.kind == "video":
                final_file = convert_video(
                    final_file,
                    info.get("duration"),
                    conversion_progress,
                )
            else:
                conversion_progress(0.0)
                final_file = convert_audio(final_file, choice.audio_format)
                conversion_progress(100.0)
        except KeyboardInterrupt:
            preserved = [final_file] if final_file is not None and final_file.exists() else []
            return DownloadResult(
                ok=False,
                file=final_file,
                error=DownloadCancelled(preserved),
            )
        except Exception as exc:
            return DownloadResult(ok=False, file=final_file, error=exc)

        size = final_file.stat().st_size
        quality = (
            media_quality(final_file)
            if choice.kind == "video"
            else final_file.suffix.lstrip(".").upper()
        )
        warning: str | None = None
        try:
            save_history({
                "date": datetime.now().isoformat(timespec="seconds"),
                "title": info.get("title") or media.title,
                "platform": media.platform,
                "type": choice.kind,
                "resolution": quality or (
                    f"hasta {choice.height}p" if choice.height else "mejor disponible"
                ),
                "duration": info.get("duration"),
                "size": size,
                "file": str(final_file),
            })
        except HistoryError as exc:
            warning = str(exc)

        return DownloadResult(
            ok=True,
            file=final_file,
            warning=warning,
            quality=quality,
        )
