#!/usr/bin/env python3
"""Lanzador de FlowMobile compatible con ios_system de a-Shell."""

from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


home = Path.home()
documents = home if home.name == "Documents" else home / "Documents"
app_directory = Path(os.environ.get("FLOWMOBILE_HOME", documents / "FlowMobile"))
entrypoint = app_directory / "main.py"

if not entrypoint.is_file():
    print(f"FlowMobile no está instalado en {app_directory}", file=sys.stderr)
    print("Vuelve a ejecutar el instalador oficial.", file=sys.stderr)
    raise SystemExit(1)

sys.path.insert(0, str(app_directory))
runpy.run_path(str(entrypoint), run_name="__main__")
