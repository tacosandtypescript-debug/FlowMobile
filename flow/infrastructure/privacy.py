from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Callable


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _windows_principal() -> str:
    username = os.environ.get("USERNAME", "").strip()
    domain = os.environ.get("USERDOMAIN", "").strip()
    return f"{domain}\\{username}" if domain and username else username


def protect_private_path(
    path: Path,
    *,
    directory: bool | None = None,
    platform_name: str | None = None,
    runner: Runner = subprocess.run,
) -> bool:
    """Limita un archivo o directorio al usuario actual en POSIX y Windows."""
    if not path.exists():
        return False
    is_directory = path.is_dir() if directory is None else directory
    try:
        path.chmod(0o700 if is_directory else 0o600)
    except OSError:
        if (platform_name or os.name) != "nt":
            return False

    if (platform_name or os.name) != "nt":
        try:
            return not bool(path.stat().st_mode & 0o077)
        except OSError:
            return False

    principal = _windows_principal()
    if not principal:
        return False
    grant = f"{principal}:(OI)(CI)F" if is_directory else f"{principal}:F"
    try:
        result = runner(
            ["icacls.exe", str(path), "/inheritance:r", "/grant:r", grant],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def private_path_is_protected(path: Path, platform_name: str | None = None) -> bool:
    if not path.exists():
        return False
    if (platform_name or os.name) != "nt":
        try:
            return not bool(path.stat().st_mode & 0o077)
        except OSError:
            return False
    # Las rutas privadas se endurecen al crearse y en cada inicio. En Windows,
    # icacls es la comprobación autoritativa y devuelve error si no puede fijar ACL.
    return protect_private_path(path, platform_name="nt")
