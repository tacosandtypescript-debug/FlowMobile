from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any
from .paths import HISTORY_FILE, LEGACY_HISTORY_FILE
from .privacy import protect_private_path


class HistoryError(RuntimeError):
    """El historial existe, pero no se pudo leer o guardar con seguridad."""


def load_history() -> list[dict[str, Any]]:
    source = HISTORY_FILE if HISTORY_FILE.exists() else LEGACY_HISTORY_FILE
    if not source.exists():
        return []
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HistoryError(f"No se pudo leer el historial: {exc}") from exc
    if not isinstance(data, list):
        raise HistoryError("El historial no tiene el formato esperado.")
    return [item for item in data if isinstance(item, dict)]


def search_history(
    query: str,
    history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    words = [word.casefold() for word in query.split() if word.strip()]
    if not words:
        return history if history is not None else load_history()
    entries = history if history is not None else load_history()
    searchable_fields = ("title", "platform", "type", "resolution", "date", "file")
    return [
        item
        for item in entries
        if all(
            word in " ".join(str(item.get(field) or "") for field in searchable_fields).casefold()
            for word in words
        )
    ]


def save_history(entry: dict[str, Any]) -> None:
    history = load_history()
    history.insert(0, entry)
    temp = Path(str(HISTORY_FILE) + ".tmp")
    try:
        temp.write_text(
            json.dumps(history[:50], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not protect_private_path(temp):
            raise OSError("no se pudieron aplicar permisos privados")
        os.replace(temp, HISTORY_FILE)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise HistoryError(f"No se pudo guardar el historial: {exc}") from exc
