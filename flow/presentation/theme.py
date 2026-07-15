import os


_COLORS_ENABLED = not bool(os.environ.get("NO_COLOR") or os.environ.get("FLOWMOBILE_NO_COLOR"))


def _ansi(value: str) -> str:
    return value if _COLORS_ENABLED else ""


RESET = _ansi("\033[0m")
BOLD = _ansi("\033[1m")
CYAN = _ansi("\033[96m")
GREEN = _ansi("\033[92m")
YELLOW = _ansi("\033[93m")
RED = _ansi("\033[91m")
GRAY = _ansi("\033[90m")
MAGENTA = _ansi("\033[95m")
WHITE = _ansi("\033[97m")
