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

from flow.presentation.cli import main

if __name__ == "__main__":
    main()
