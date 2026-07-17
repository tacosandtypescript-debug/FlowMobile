#!/usr/bin/env python3
"""Genera y verifica el manifiesto de integridad del código ejecutable."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


MANIFEST_NAME = "SECURITY_MANIFEST.sha256"
ROOT_FILES = {
    "main.py",
    "bootstrap_ios.py",
    "install_ios.py",
    "uninstall_ios.py",
    "install.sh",
    "install-ios.sh",
    "install-termux.sh",
    "install-linux.sh",
    "install-windows.ps1",
    "requirements.txt",
    "requirements.lock",
}


def critical_files(root: Path) -> list[Path]:
    files = [root / name for name in ROOT_FILES if (root / name).is_file()]
    files.extend(path for path in (root / "flow").rglob("*.py") if path.is_file())
    scripts = root / "scripts"
    if scripts.is_dir():
        files.extend(
            path
            for path in scripts.iterdir()
            if path.is_file() and (path.suffix in {".py", ".sh", ".ps1"} or path.name == "flow")
        )
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_text(root: Path) -> str:
    return "".join(
        f"{file_sha256(path)}  {path.relative_to(root).as_posix()}\n"
        for path in critical_files(root)
    )


def verify_manifest(root: Path) -> list[str]:
    manifest = root / MANIFEST_NAME
    if not manifest.is_file():
        return ["Falta SECURITY_MANIFEST.sha256"]
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in parts[0]
        ):
            return ["El manifiesto tiene una línea inválida"]
        name = parts[1].lstrip("*")
        target = (root / name).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            return ["El manifiesto contiene una ruta no segura"]
        if name in expected:
            return [f"El manifiesto repite el archivo: {name}"]
        expected[name] = parts[0].lower()
    current = {path.relative_to(root).as_posix(): path for path in critical_files(root)}
    errors: list[str] = []
    for name in sorted(set(expected) | set(current)):
        path = current.get(name)
        if path is None:
            errors.append(f"Archivo inesperado en el manifiesto: {name}")
        elif name not in expected:
            errors.append(f"Archivo ejecutable sin registrar: {name}")
        elif path.is_symlink():
            errors.append(f"Enlace simbólico no permitido: {name}")
        elif file_sha256(path) != expected[name]:
            errors.append(f"Archivo modificado: {name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("root", nargs="?", default=".")
    values = parser.parse_args()
    root = Path(values.root).resolve()
    if values.write:
        (root / MANIFEST_NAME).write_text(manifest_text(root), encoding="utf-8")
        return 0
    errors = verify_manifest(root)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
