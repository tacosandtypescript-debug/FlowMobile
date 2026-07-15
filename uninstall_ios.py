#!/usr/bin/env python3
"""Desinstalador independiente y seguro de FlowMobile para a-Shell."""

from __future__ import annotations

from dataclasses import dataclass, field
import ctypes
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time


APP_NAMES = ("FlowMobile", "FlowApp", "FlowIOS")
PRIVATE_NAMES = (
    ".flowmobile",
    ".flowmobile-data",
    ".flowmobile-rollback",
    "flow_settings.json",
    ".flowmobile-source",
    ".flowios-source",
)
PROFILE_START = "# >>> FlowMobile launcher >>>"
PROFILE_END = "# <<< FlowMobile launcher <<<"


@dataclass(slots=True)
class CleanupResult:
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def documents_directory(home: Path | None = None) -> Path:
    base = (home or Path.home()).expanduser()
    return base if base.name == "Documents" else base / "Documents"


def _safe_target(path: Path, documents: Path) -> Path:
    # resolve() unifica nombres equivalentes del sistema antes de comparar:
    # RUNNER~1/nombre largo en Windows y /var//private/var en iOS.
    root = documents.resolve(strict=False)
    target = path.resolve(strict=False)
    if target == root or os.path.commonpath((str(root), str(target))) != str(root):
        raise ValueError(f"Ruta protegida, no se borrará: {target}")
    return target


def _make_writable(function, path: str, _error) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        function(path)
    except OSError:
        pass


def _delete_path(path: Path, documents: Path, result: CleanupResult) -> None:
    path = _safe_target(path, documents)
    existed = path.exists() or path.is_symlink()
    if not existed:
        return
    last_error: OSError | None = None
    for attempt in range(3):
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, onerror=_make_writable)
            else:
                try:
                    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
                except OSError:
                    pass
                path.unlink(missing_ok=True)
            if not path.exists() and not path.is_symlink():
                result.removed.append(str(path))
                return
        except OSError as exc:
            last_error = exc
        time.sleep(0.1 * (attempt + 1))
    detail = str(last_error) if last_error else "el sistema todavía muestra la ruta"
    result.errors.append(f"{path}: {detail}")


def _quarantine_app(path: Path, documents: Path, result: CleanupResult) -> None:
    path = _safe_target(path, documents)
    if not path.exists() and not path.is_symlink():
        return
    quarantine = documents / f".flowmobile-deleting-{path.name.lower()}-{os.getpid()}"
    _delete_path(quarantine, documents, result)
    try:
        path.rename(quarantine)
    except OSError:
        _delete_path(path, documents, result)
        return
    _delete_path(quarantine, documents, result)
    if path.exists() or path.is_symlink():
        result.errors.append(f"{path}: la carpeta original sigue visible")
    else:
        result.removed.append(str(path))


def _clean_profile(profile: Path, result: CleanupResult) -> None:
    try:
        previous = profile.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except (OSError, UnicodeError) as exc:
        result.errors.append(f"{profile}: {exc}")
        return

    cleaned: list[str] = []
    inside_block = False
    changed = False
    for line in previous.splitlines():
        stripped = line.strip()
        if stripped == PROFILE_START:
            inside_block = True
            changed = True
            continue
        if stripped == PROFILE_END:
            inside_block = False
            changed = True
            continue
        if inside_block or re.match(r"^\s*alias\s+flow\s*=", line):
            changed = True
            continue
        cleaned.append(line)
    if not changed:
        return
    content = "\n".join(cleaned).rstrip()
    try:
        if content:
            profile.write_text(content + "\n", encoding="utf-8")
        else:
            profile.unlink(missing_ok=True)
        result.removed.append(str(profile) + " (configuración de flow)")
    except OSError as exc:
        result.errors.append(f"{profile}: {exc}")


def _remove_current_alias() -> None:
    try:
        command = ctypes.CDLL(None).ios_system
        command.argtypes = (ctypes.c_char_p,)
        command.restype = ctypes.c_int
        command(b"unalias flow")
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def _remove_dependencies(result: CleanupResult) -> None:
    try:
        from pip._internal.cli.main import main as pip_main

        status = pip_main(
            [
                "uninstall",
                "--yes",
                "--disable-pip-version-check",
                "yt-dlp",
                "yt-dlp-ejs",
            ]
        )
    except (ImportError, OSError) as exc:
        result.errors.append(f"Dependencias Python: {exc}")
        return
    if status:
        result.errors.append("pip no pudo eliminar yt-dlp y yt-dlp-ejs")
    else:
        result.removed.append("yt-dlp y yt-dlp-ejs")


def purge_flowmobile(
    *,
    home: Path | None = None,
    remove_dependencies: bool = False,
    app_directory: Path | None = None,
) -> CleanupResult:
    documents = documents_directory(home).resolve()
    if not documents.is_dir():
        raise ValueError(f"No existe la carpeta Documents esperada: {documents}")
    result = CleanupResult()
    previous_directory = Path.cwd()
    os.chdir(documents)
    try:
        applications = [documents / name for name in APP_NAMES]
        if app_directory is not None:
            custom_application = _safe_target(app_directory, documents)
            if custom_application not in applications:
                applications.insert(0, custom_application)
        for application in applications:
            _quarantine_app(application, documents, result)
        for name in PRIVATE_NAMES:
            _delete_path(documents / name, documents, result)

        _delete_path(documents / "Downloads" / "FlowMobile", documents, result)
        _delete_path(documents / "Downloads" / "history.json", documents, result)
        for temporary in (documents / "tmp").glob("flowmobile-install-*"):
            _delete_path(temporary, documents, result)
        for temporary in documents.glob(".flowmobile-deleting-*"):
            _delete_path(temporary, documents, result)

        _delete_path(documents / "bin" / "flow.py", documents, result)
        launcher = documents / "bin" / "flow"
        try:
            launcher_content = launcher.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            launcher_content = ""
        if "FlowMobile" in launcher_content or "flow_ios" in launcher_content:
            _delete_path(launcher, documents, result)

        for profile_name in (".profile", ".bashrc"):
            _clean_profile(documents / profile_name, result)
        _remove_current_alias()
        if remove_dependencies:
            _remove_dependencies(result)
    finally:
        if previous_directory.exists():
            os.chdir(previous_directory)
        else:
            os.chdir(documents)

    verified_paths = [documents / name for name in (*APP_NAMES, *PRIVATE_NAMES)]
    if app_directory is not None:
        verified_paths.append(_safe_target(app_directory, documents))
    remaining = [
        path
        for path in verified_paths
        if path.exists() or path.is_symlink()
    ]
    remaining.extend(documents.glob(".flowmobile-deleting-*"))
    for path in remaining:
        message = f"{path}: continúa presente después de la verificación final"
        if message not in result.errors:
            result.errors.append(message)
    return result


def main(arguments: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if arguments is None else arguments)
    if "BORRAR" not in values:
        print("Limpieza cancelada. Para confirmar añade BORRAR al final.")
        return 2
    remove_dependencies = "--dependencies" in values
    print("Eliminando completamente FlowMobile de a-Shell…")
    try:
        result = purge_flowmobile(remove_dependencies=remove_dependencies)
    except (OSError, ValueError) as exc:
        print(f"No se pudo iniciar la limpieza: {exc}", file=sys.stderr)
        return 1
    if result.errors:
        print("La limpieza quedó incompleta:", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("FlowMobile, sus datos y sus lanzadores fueron eliminados.")
    if remove_dependencies:
        print("También se eliminaron yt-dlp y yt-dlp-ejs.")
    print("Cierra esta ventana de a-Shell antes de volver a instalar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
