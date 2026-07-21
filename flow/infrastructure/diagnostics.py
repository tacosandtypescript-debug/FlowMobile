from __future__ import annotations

from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
import json
import shutil
import sys
from pathlib import Path

from flow import APP_NAME, APP_VERSION
from flow.infrastructure.ffmpeg import tools_status
from flow.infrastructure.paths import STATE_DIR, VIDEO_DIR
from flow.infrastructure.platform import PLATFORM
from flow.infrastructure.privacy import protect_private_path
from flow.infrastructure.security import security_status


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "no instalado"


def diagnostic_data() -> dict[str, object]:
    ffmpeg, ffprobe = tools_status()
    security = security_status()
    try:
        storage = shutil.disk_usage(VIDEO_DIR)
        free_storage: int | None = storage.free
    except OSError:
        free_storage = None
    return {
        "application": APP_NAME,
        "version": APP_VERSION,
        "created": datetime.now().isoformat(timespec="seconds"),
        "platform": {
            "key": PLATFORM.key,
            "name": PLATFORM.name,
            "mobile_os": PLATFORM.mobile_os,
        },
        "python": sys.version.split()[0],
        "dependencies": {
            "yt-dlp": _package_version("yt-dlp"),
            "yt-dlp-ejs": _package_version("yt-dlp-ejs"),
            "ffmpeg": ffmpeg,
            "ffprobe": ffprobe,
        },
        "free_storage_bytes": free_storage,
        "security": {
            "official_source": security.official_source,
            "integrity_ok": security.integrity_ok,
            "cookies_private": security.cookies_private,
        },
    }


def save_diagnostic_report(directory: Path | None = None) -> Path:
    target_directory = directory or STATE_DIR / "diagnostics"
    target_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = target_directory / f"flowmobile-diagnostic-{stamp}.json"
    target.write_text(
        json.dumps(diagnostic_data(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not protect_private_path(target):
        target.unlink(missing_ok=True)
        raise OSError("No se pudo proteger el informe de diagnóstico.")
    return target
