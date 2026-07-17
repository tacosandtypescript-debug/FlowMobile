#!/usr/bin/env python3
"""Carga siempre el instalador iOS más reciente mediante la API de GitHub."""

from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_REPOSITORY = "tacosandtypescript-debug/FlowMobile"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _read_request(request: Request, timeout: int) -> bytes:
    last_error: OSError | None = None
    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            if attempt == 0 and (exc.code == 429 or 500 <= exc.code < 600):
                last_error = exc
                time.sleep(1)
                continue
            raise
        except (OSError, URLError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
    assert last_error is not None
    raise last_error


def _bootstrap_log_path() -> Path:
    home = Path.home()
    documents = home if home.name == "Documents" else home / "Documents"
    return Path(os.environ.get("FLOWMOBILE_INSTALL_LOG", documents / ".flowmobile-install.log"))


def _show_bootstrap_problem(exc: BaseException) -> None:
    log_path = _bootstrap_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"FlowMobile bootstrap error\n{type(exc).__name__}: {exc}\n", encoding="utf-8")
    try:
        log_path.chmod(0o600)
    except OSError:
        pass
    if isinstance(exc, HTTPError):
        code = f"FM-IOS-HTTP-{exc.code}"
        cause = f"GitHub respondió con HTTP {exc.code}."
        hint = "Espera unos minutos o cambia de red antes de repetir."
    elif isinstance(exc, URLError):
        code = "FM-IOS-NETWORK"
        cause = "a-Shell no pudo conectarse a GitHub."
        hint = "Comprueba internet, DNS o VPN y repite el mismo comando."
    else:
        code = "FM-IOS-BOOTSTRAP"
        cause = "No se pudo preparar el instalador oficial."
        hint = "Comprueba que exista un release estable y vuelve a intentarlo."
    print("\n✕ No se pudo iniciar la instalación.", file=sys.stderr)
    print(f"Código: {code}", file=sys.stderr)
    print(f"Causa: {cause}", file=sys.stderr)
    print(f"Detalle: {exc}", file=sys.stderr)
    print(f"Solución: {hint}", file=sys.stderr)
    print(f"Registro completo: {log_path}", file=sys.stderr)


def _latest_stable_reference(repository: str) -> str:
    request = Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "Cache-Control": "no-cache",
            "User-Agent": "FlowMobile-iOS-bootstrap",
        },
    )
    release = json.loads(_read_request(request, 15).decode("utf-8"))
    tag = str(release.get("tag_name") or "").strip()
    if re.fullmatch(r"v?\d+(?:\.\d+){1,3}", tag):
        return tag
    raise ValueError("GitHub no publicó una etiqueta estable válida.")


def latest_stable_reference(repository: str) -> str:
    try:
        return _latest_stable_reference(repository)
    except (OSError, UnicodeError, ValueError):
        return ""


def _expected_checksum(checksums: str, filename: str) -> str:
    for line in checksums.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == filename:
            digest = parts[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                return digest
    raise ValueError(f"SHA-256 no publicado para {filename}.")


def _verified_release_installer(repository: str, reference: str) -> str:
    base = f"https://github.com/{repository}/releases/download/{reference}"
    headers = {"Cache-Control": "no-cache", "User-Agent": "FlowMobile-iOS-bootstrap"}
    checksums = _read_request(
        Request(f"{base}/SHA256SUMS", headers=headers), 30
    ).decode("utf-8")
    payload = _read_request(Request(f"{base}/install_ios.py", headers=headers), 30)
    expected = _expected_checksum(checksums, "install_ios.py")
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError("El instalador no coincide con el SHA-256 del release oficial.")
    return payload.decode("utf-8")


def main() -> int:
    repository = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPOSITORY
    if not REPOSITORY_PATTERN.fullmatch(repository):
        _show_bootstrap_problem(ValueError("Repositorio no válido. Usa USUARIO/FlowMobile."))
        return 1

    try:
        branch = os.environ.get("FLOWMOBILE_BRANCH", "").strip() or _latest_stable_reference(repository)
        if re.fullmatch(r"v?\d+(?:\.\d+){1,3}", branch):
            source = _verified_release_installer(repository, branch)
        elif os.environ.get("FLOWMOBILE_ALLOW_UNVERIFIED") == "1":
            url = (
                f"https://api.github.com/repos/{repository}/contents/install_ios.py"
                f"?ref={quote(branch, safe='')}"
            )
            request = Request(
                url,
                headers={
                    "Accept": "application/vnd.github.raw+json",
                    "Cache-Control": "no-cache",
                    "User-Agent": "FlowMobile-iOS-bootstrap",
                },
            )
            with urlopen(request, timeout=30) as response:
                source = response.read().decode("utf-8")
        else:
            raise ValueError("Solo se permiten releases estables verificados.")
    except (OSError, UnicodeError, ValueError) as exc:
        _show_bootstrap_problem(exc)
        return 1

    sys.argv = ["install_ios.py", repository, branch]
    namespace = {"__name__": "__main__", "__file__": "install_ios.py"}
    exec(compile(source, "install_ios.py", "exec"), namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
