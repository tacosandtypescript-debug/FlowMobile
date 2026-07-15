#!/usr/bin/env python3
"""Carga siempre el instalador iOS más reciente mediante la API de GitHub."""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_REPOSITORY = "tacosandtypescript-debug/FlowMobile"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def main() -> int:
    repository = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPOSITORY
    if not REPOSITORY_PATTERN.fullmatch(repository):
        print("Repositorio no válido. Usa USUARIO/FlowMobile.", file=sys.stderr)
        return 1

    branch = os.environ.get("FLOWMOBILE_BRANCH", "main")
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
    try:
        with urlopen(request, timeout=30) as response:
            source = response.read().decode("utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"No se pudo obtener el instalador más reciente: {exc}", file=sys.stderr)
        return 1

    sys.argv = ["install_ios.py", repository, branch]
    namespace = {"__name__": "__main__", "__file__": "install_ios.py"}
    exec(compile(source, "install_ios.py", "exec"), namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
