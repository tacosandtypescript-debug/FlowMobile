from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path

from flow.infrastructure.paths import LEGACY_SETTINGS_FILE, SETTINGS_FILE


@dataclass(slots=True)
class AppSettings:
    default_kind: str = "ask"
    video_quality: str = "best"
    audio_format: str = "auto"
    auto_updates: bool = True
    clipboard_detection: bool = True
    colors: bool = True
    interface_mode: str = "compact"
    last_update_check: str | None = None
    last_update_ok: bool | None = None

    def normalize(self) -> "AppSettings":
        if self.default_kind not in {"ask", "video", "audio"}:
            self.default_kind = "ask"
        if self.video_quality not in {"best", "2160", "1440", "1080", "720", "480", "360"}:
            self.video_quality = "best"
        if self.audio_format not in {"auto", "m4a", "mp3"}:
            self.audio_format = "auto"
        if not isinstance(self.auto_updates, bool):
            self.auto_updates = True
        if not isinstance(self.clipboard_detection, bool):
            self.clipboard_detection = True
        if not isinstance(self.colors, bool):
            self.colors = True
        if self.interface_mode not in {"compact", "accessible"}:
            self.interface_mode = "compact"
        return self

def load_settings() -> AppSettings:
    source = SETTINGS_FILE if SETTINGS_FILE.exists() else LEGACY_SETTINGS_FILE
    if not source.exists():
        return AppSettings()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AppSettings()
        def _to_bool(value: object) -> bool:
            return bool(value) if not isinstance(value, str) else value.lower() in {"true", "1", "yes"}

        last_update_check = data.get("last_update_check")
        last_update_ok = data.get("last_update_ok")
        return AppSettings(
            default_kind=str(data.get("default_kind", "ask")),
            video_quality=str(data.get("video_quality", "best")),
            audio_format=str(data.get("audio_format", "auto")),
            auto_updates=_to_bool(data.get("auto_updates", True)),
            clipboard_detection=_to_bool(data.get("clipboard_detection", True)),
            colors=_to_bool(data.get("colors", True)),
            interface_mode=str(data.get("interface_mode", "compact")),
            last_update_check=str(last_update_check) if last_update_check is not None else None,
            last_update_ok=None if last_update_ok is None else _to_bool(last_update_ok),
        ).normalize()
    except (OSError, UnicodeError, json.JSONDecodeError):
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    settings.normalize()
    temp = Path(str(SETTINGS_FILE) + ".tmp")
    temp.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp, SETTINGS_FILE)
