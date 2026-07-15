#!/usr/bin/env python3
"""Diagnóstico de FlowMobile ejecutable directamente en a-Shell."""

from __future__ import annotations

import compileall
from pathlib import Path
import sys
import unittest


project_directory = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_directory))


def main() -> int:
    version = (project_directory / "VERSION").read_text(encoding="utf-8").strip()
    print(f"FlowMobile {version}")
    from flow import APP_VERSION

    if version != APP_VERSION:
        print(f"ERROR: VERSION ({version}) y el código ({APP_VERSION}) no coinciden.")
        return 1
    required = (
        "main.py",
        "install_ios.py",
        "install-termux.sh",
        "scripts/flow_ios.py",
        "flow/presentation/cli.py",
    )
    missing = [name for name in required if not (project_directory / name).is_file()]
    if missing:
        print("ERROR: instalación incompleta: " + ", ".join(missing))
        return 1
    rollback = project_directory.parent / ".flowmobile-rollback"
    if rollback.exists():
        print("ERROR: quedó un respaldo de actualización sin resolver.")
        return 1
    print("Comprobando sintaxis de Python…")
    if not compileall.compile_dir(project_directory / "flow", quiet=1):
        return 1
    if not compileall.compile_file(project_directory / "main.py", quiet=1):
        return 1
    for installer in ("install_ios.py", "bootstrap_ios.py", "scripts/release_notes.py"):
        if not compileall.compile_file(project_directory / installer, quiet=1):
            return 1

    print("Comprobando plataforma, yt-dlp y herramientas multimedia…")
    import yt_dlp

    from flow.infrastructure.ffmpeg import tools_status
    from flow.infrastructure.platform import PLATFORM

    ffmpeg_available, ffprobe_available = tools_status()
    print(
        f"{PLATFORM.mobile_os} / {PLATFORM.name} / "
        f"yt-dlp {yt_dlp.version.__version__}"
    )
    print(f"FFmpeg: {'OK' if ffmpeg_available else 'NO DISPONIBLE'}")
    print(f"FFprobe: {'OK' if ffprobe_available else 'NO DISPONIBLE'}")
    if not ffmpeg_available or not ffprobe_available:
        return 1

    print("Ejecutando pruebas…")
    suite = unittest.defaultTestLoader.discover(str(project_directory / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    print("FlowMobile está listo para una prueba real de audio y video.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
