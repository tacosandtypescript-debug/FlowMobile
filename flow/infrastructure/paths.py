from pathlib import Path

from flow.infrastructure.platform import PLATFORM, termux_shared_downloads

BASE_DIR = Path(__file__).resolve().parents[2]
STATE_DIR = BASE_DIR / ".flowmobile"
SESSION_DIR = STATE_DIR / "sessions"
QUEUE_DIR = STATE_DIR / "queues"


def _prepare_download_dir() -> Path:
    """Usa almacenamiento compartido en Android y vuelve al privado si falla."""
    shared_downloads = termux_shared_downloads()
    preferred = (
        shared_downloads / "FlowMobile"
        if PLATFORM.is_termux and shared_downloads is not None
        else BASE_DIR / "Downloads"
    )
    fallback = BASE_DIR / "Downloads"
    last_error: OSError | None = None

    for candidate in dict.fromkeys((preferred, fallback)):
        try:
            (candidate / "Videos").mkdir(parents=True, exist_ok=True)
            (candidate / "Audio").mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError as exc:
            last_error = exc

    raise OSError("FlowMobile no pudo preparar una carpeta de descargas") from last_error


DOWNLOAD_DIR = _prepare_download_dir()
VIDEO_DIR = DOWNLOAD_DIR / "Videos"
AUDIO_DIR = DOWNLOAD_DIR / "Audio"
BATCH_DIR = DOWNLOAD_DIR / "Lotes"
HISTORY_FILE = STATE_DIR / "history.json"
SETTINGS_FILE = STATE_DIR / "settings.json"
LEGACY_HISTORY_FILE = BASE_DIR / "Downloads" / "history.json"
LEGACY_SETTINGS_FILE = BASE_DIR / "flow_settings.json"

STATE_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
BATCH_DIR.mkdir(parents=True, exist_ok=True)
for private_directory in (STATE_DIR, SESSION_DIR, QUEUE_DIR):
    try:
        private_directory.chmod(0o700)
    except OSError:
        pass
