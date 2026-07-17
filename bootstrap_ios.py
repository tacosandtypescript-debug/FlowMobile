#!/usr/bin/env python3
"""Carga siempre el instalador iOS más reciente mediante la API de GitHub."""

from __future__ import annotations

import os
import hashlib
import json
import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_REPOSITORY = "tacosandtypescript-debug/FlowMobile"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def latest_stable_reference(repository: str) -> str:
    request = Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "Cache-Control": "no-cache",
            "User-Agent": "FlowMobile-iOS-bootstrap",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            release = json.loads(response.read().decode("utf-8"))
        tag = str(release.get("tag_name") or "").strip()
        if re.fullmatch(r"v?\d+(?:\.\d+){1,3}", tag):
            return tag
    except (OSError, UnicodeError, ValueError):
        pass
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
    with urlopen(Request(f"{base}/SHA256SUMS", headers=headers), timeout=30) as response:
        checksums = response.read().decode("utf-8")
    with urlopen(Request(f"{base}/install_ios.py", headers=headers), timeout=30) as response:
        payload = response.read()
    expected = _expected_checksum(checksums, "install_ios.py")
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError("El instalador no coincide con el SHA-256 del release oficial.")
    return payload.decode("utf-8")


def main() -> int:
    repository = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPOSITORY
    if not REPOSITORY_PATTERN.fullmatch(repository):
        print("Repositorio no válido. Usa USUARIO/FlowMobile.", file=sys.stderr)
        return 1

    branch = os.environ.get("FLOWMOBILE_BRANCH", "").strip() or latest_stable_reference(repository)
    if not branch:
        print("No se encontró un release estable verificable.", file=sys.stderr)
        return 1
    try:
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
        print(f"No se pudo verificar el instalador oficial: {exc}", file=sys.stderr)
        return 1

    sys.argv = ["install_ios.py", repository, branch]
    namespace = {"__name__": "__main__", "__file__": "install_ios.py"}
    exec(compile(source, "install_ios.py", "exec"), namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
