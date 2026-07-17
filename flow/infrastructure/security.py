from __future__ import annotations

from dataclasses import dataclass
import os

from flow import APP_VERSION
from flow.infrastructure.paths import BASE_DIR
from flow.infrastructure.sessions import COOKIES_FILE
from flow.infrastructure.updates import DEFAULT_REPOSITORY, configured_repository
from scripts.security_manifest import verify_manifest


@dataclass(frozen=True, slots=True)
class SecurityStatus:
    official_source: bool
    integrity_ok: bool
    integrity_detail: str
    cookies_private: bool | None
    version: str = APP_VERSION


def security_status() -> SecurityStatus:
    errors = verify_manifest(BASE_DIR)
    cookie_private: bool | None = None
    if COOKIES_FILE.is_file():
        try:
            cookie_private = not bool(COOKIES_FILE.stat().st_mode & 0o077)
        except OSError:
            cookie_private = False
    return SecurityStatus(
        official_source=configured_repository() == DEFAULT_REPOSITORY,
        integrity_ok=not errors,
        integrity_detail=errors[0] if errors else "Código verificado con SHA-256",
        cookies_private=cookie_private,
    )


def harden_private_files() -> None:
    if COOKIES_FILE.is_file():
        try:
            os.chmod(COOKIES_FILE, 0o600)
        except OSError:
            pass
