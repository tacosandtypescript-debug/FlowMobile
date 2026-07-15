from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil

from flow.infrastructure.paths import SESSION_DIR


COOKIES_FILE = SESSION_DIR / "cookies.txt"


@dataclass(frozen=True, slots=True)
class SessionStatus:
    configured: bool
    cookies: int = 0
    size: int = 0


def _cookie_rows(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and len(line.split("\t")) >= 7
    ]


def validate_cookie_file(source: Path) -> int:
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"No se pudo leer el archivo de cookies: {exc}") from exc
    rows = _cookie_rows(text)
    header_ok = "netscape http cookie file" in text[:300].casefold()
    if not header_ok and not rows:
        raise ValueError("El archivo no usa el formato Netscape cookies.txt.")
    return len(rows)


def import_cookies(source: Path) -> SessionStatus:
    source = source.expanduser().resolve()
    if source == COOKIES_FILE.resolve():
        return session_status()
    validate_cookie_file(source)
    temporary = COOKIES_FILE.with_suffix(".tmp")
    try:
        shutil.copyfile(source, temporary)
        os.chmod(temporary, 0o600)
        os.replace(temporary, COOKIES_FILE)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"No se pudieron guardar las cookies privadas: {exc}") from exc
    return session_status()


def remove_cookies() -> None:
    COOKIES_FILE.unlink(missing_ok=True)


def session_status() -> SessionStatus:
    if not COOKIES_FILE.is_file():
        return SessionStatus(False)
    try:
        text = COOKIES_FILE.read_text(encoding="utf-8")
        return SessionStatus(True, len(_cookie_rows(text)), COOKIES_FILE.stat().st_size)
    except (OSError, UnicodeError):
        return SessionStatus(False)


def cookie_options() -> dict[str, str]:
    return {"cookiefile": str(COOKIES_FILE)} if COOKIES_FILE.is_file() else {}
