#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


def notes_for_version(changelog: str, version: str) -> list[str]:
    notes: list[str] = []
    inside = False
    for raw_line in changelog.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if inside:
                break
            heading = line[3:].strip()
            inside = heading == version or heading.startswith(version + " ")
        elif inside and line.startswith("- "):
            notes.append(line)
    return notes


def main(arguments: list[str] | None = None) -> int:
    values = sys.argv[1:] if arguments is None else arguments
    if len(values) != 1:
        print("Uso: release_notes.py VERSION", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    notes = notes_for_version(
        (root / "CHANGELOG.md").read_text(encoding="utf-8"),
        values[0],
    )
    if not notes:
        print(f"No hay notas para {values[0]}.", file=sys.stderr)
        return 1
    print(f"## FlowMobile {values[0]}\n")
    print("\n".join(notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
