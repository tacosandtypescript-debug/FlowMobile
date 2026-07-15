from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from flow.infrastructure.paths import STATE_DIR


RESUME_FILE = STATE_DIR / "resume.json"


def _load() -> list[str]:
    try:
        data = json.loads(RESUME_FILE.read_text(encoding="utf-8"))
        return [str(value) for value in data if isinstance(value, str)] if isinstance(data, list) else []
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []


def protected_partial_files() -> set[Path]:
    existing = {Path(value).resolve() for value in _load() if Path(value).is_file()}
    _save(existing)
    return existing


def register_partial_files(paths: Iterable[Path]) -> None:
    protected = protected_partial_files()
    protected.update(path.resolve() for path in paths if path.is_file())
    _save(protected)


def _save(paths: Iterable[Path]) -> None:
    temporary = RESUME_FILE.with_suffix(".tmp")
    values = sorted(str(path) for path in paths)
    if not values:
        RESUME_FILE.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
        return
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    os.replace(temporary, RESUME_FILE)
