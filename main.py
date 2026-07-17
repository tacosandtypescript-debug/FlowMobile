#!/usr/bin/env python3
from pathlib import Path
import os
import sys

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from flow.infrastructure.settings import load_settings

if not load_settings().colors:
    os.environ["FLOWMOBILE_NO_COLOR"] = "1"

if "--health-check" in sys.argv[1:]:
    import yt_dlp
    from flow import APP_VERSION
    from flow.infrastructure.ffmpeg import tools_status

    if not all(tools_status()):
        print("FlowMobile: FFmpeg o FFprobe no está disponible.", file=sys.stderr)
        raise SystemExit(1)
    print(f"FlowMobile {APP_VERSION}: OK · yt-dlp {yt_dlp.version.__version__}")
    raise SystemExit(0)

if "--version" in sys.argv[1:]:
    from flow import APP_VERSION

    print(APP_VERSION)
    raise SystemExit(0)

from flow.presentation.cli import main

if __name__ == "__main__":
    main()
