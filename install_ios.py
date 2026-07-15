#!/usr/bin/env python3
"""Instalador nativo de FlowMobile para a-Shell.

a-Shell ejecuta Python y otros comandos mediante ios_system. Invocar esos
comandos desde un proceso ``sh``/``dash`` separado no es compatible, por eso
este instalador realiza toda la preparación dentro del mismo proceso Python.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile
from urllib.request import Request, urlopen


DEFAULT_REPOSITORY = "tacosandtypescript-debug/FlowMobile"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PRESERVED_ITEMS = ("Downloads", ".flowmobile", "flow_settings.json")
PROFILE_START = "# >>> FlowMobile launcher >>>"
PROFILE_END = "# <<< FlowMobile launcher <<<"


def documents_directory(home: Path | None = None) -> Path:
    base = (home or Path.home()).expanduser()
    return base if base.name == "Documents" else base / "Documents"


def _download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "FlowMobile-installer"})
    with urlopen(request, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def _safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if os.path.commonpath((str(root), str(target))) != str(root):
                raise RuntimeError("El paquete contiene una ruta no segura.")
        bundle.extractall(destination, filter="data")


def _find_source(work_directory: Path) -> Path:
    for candidate in work_directory.iterdir():
        if candidate.is_dir() and (candidate / "flow").is_dir() and (
            candidate / "main.py"
        ).is_file():
            return candidate
    raise RuntimeError("El paquete de FlowMobile no es válido.")


def _install_python_dependencies() -> None:
    try:
        from pip._internal.cli.main import main as pip_main
    except ImportError as exc:
        raise RuntimeError("pip no está disponible en esta instalación de a-Shell.") from exc

    status = pip_main(
        [
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--upgrade",
            "yt-dlp",
            "yt-dlp-ejs",
        ]
    )
    if status:
        raise RuntimeError("pip no pudo instalar yt-dlp y yt-dlp-ejs.")


def _configure_profile(documents: Path, app_directory: Path) -> None:
    """Sustituye aliases antiguos sin alterar otras preferencias de a-Shell."""
    profile = documents / ".profile"
    try:
        previous = profile.read_text(encoding="utf-8")
    except FileNotFoundError:
        previous = ""

    cleaned: list[str] = []
    inside_flowmobile_block = False
    for line in previous.splitlines():
        stripped = line.strip()
        if stripped == PROFILE_START:
            inside_flowmobile_block = True
            continue
        if stripped == PROFILE_END:
            inside_flowmobile_block = False
            continue
        if inside_flowmobile_block:
            continue
        if re.match(r"^\s*alias\s+flow\s*=", line):
            continue
        cleaned.append(line)

    target = str(app_directory / "main.py").replace("'", "'\"'\"'")
    content = "\n".join(cleaned).rstrip()
    if content:
        content += "\n\n"
    content += (
        f"{PROFILE_START}\n"
        f"alias flow='python3 \"{target}\"'\n"
        f"{PROFILE_END}\n"
    )
    profile.write_text(content, encoding="utf-8")


def install(
    repository: str = DEFAULT_REPOSITORY,
    branch: str = "main",
    *,
    home: Path | None = None,
) -> Path:
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("Repositorio no válido. Usa USUARIO/FlowMobile.")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
        raise ValueError("Rama de GitHub no válida.")

    documents = documents_directory(home)
    app_directory = Path(os.environ.get("FLOWMOBILE_HOME", documents / "FlowMobile"))
    bin_directory = documents / "bin"
    temporary_root = documents / "tmp"
    temporary_root.mkdir(parents=True, exist_ok=True)
    bin_directory.mkdir(parents=True, exist_ok=True)
    work_directory = Path(
        tempfile.mkdtemp(prefix="flowmobile-install-", dir=temporary_root)
    )
    archive = work_directory / "flowmobile.tar.gz"
    backup = work_directory / "previous"

    print("Instalando FlowMobile para a-Shell…")
    try:
        _download(
            f"https://github.com/{repository}/archive/refs/heads/{branch}.tar.gz",
            archive,
        )
        _safe_extract(archive, work_directory)
        source = _find_source(work_directory)

        existing: Path | None = app_directory if app_directory.is_dir() else None
        if existing is None:
            for legacy in (documents / "FlowIOS", documents / "FlowApp"):
                if legacy.is_dir():
                    existing = legacy
                    break
        if existing is not None:
            shutil.move(str(existing), str(backup))

        try:
            shutil.move(str(source), str(app_directory))
        except Exception:
            if backup.is_dir() and not app_directory.exists():
                shutil.move(str(backup), str(app_directory))
            raise

        for name in PRESERVED_ITEMS:
            previous = backup / name
            current = app_directory / name
            if previous.exists() and not current.exists():
                shutil.move(str(previous), str(current))

        (app_directory / ".flowmobile-source").write_text(
            repository + "\n", encoding="utf-8"
        )
        # ios_system reconoce scripts Python por su extensión. El comando corto
        # se registra como alias en .profile para que funcione desde cualquier
        # carpeta y no dependa de que a-Shell interprete un archivo sin .py.
        (bin_directory / "flow").unlink(missing_ok=True)
        launcher = bin_directory / "flow.py"
        shutil.copy2(app_directory / "scripts" / "flow_ios.py", launcher)
        _configure_profile(documents, app_directory)
        _install_python_dependencies()
    finally:
        shutil.rmtree(work_directory, ignore_errors=True)

    print("FlowMobile instalado para iOS.")
    print("Activa el comando con: cd && . ./.profile")
    print(f"En esta ventana puedes iniciar con: python3 {app_directory / 'main.py'}")
    return app_directory


def main(arguments: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if arguments is None else arguments)
    repository = values[0] if values else DEFAULT_REPOSITORY
    branch = values[1] if len(values) > 1 else os.environ.get("FLOWMOBILE_BRANCH", "main")
    try:
        install(repository, branch)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"No se pudo instalar FlowMobile: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
