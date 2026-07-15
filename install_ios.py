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
PRESERVED_DATA_NAME = ".flowmobile-data"
ROLLBACK_NAME = ".flowmobile-rollback"
PROFILE_START = "# >>> FlowMobile launcher >>>"
PROFILE_END = "# <<< FlowMobile launcher <<<"


def documents_directory(home: Path | None = None) -> Path:
    base = (home or Path.home()).expanduser()
    return base if base.name == "Documents" else base / "Documents"


def _download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "FlowMobile-installer"})
    with urlopen(request, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def _download_source_archive(repository: str, reference: str, destination: Path) -> None:
    candidates = (
        f"https://github.com/{repository}/archive/refs/heads/{reference}.tar.gz",
        f"https://github.com/{repository}/archive/refs/tags/{reference}.tar.gz",
    )
    last_error: OSError | None = None
    for url in candidates:
        try:
            _download(url, destination)
            return
        except OSError as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
    raise RuntimeError(f"No se pudo descargar la referencia {reference}.") from last_error


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


def _flow_alias(app_directory: Path) -> str:
    target = (app_directory / "main.py").as_posix().replace("'", "'\"'\"'")
    return f"alias flow='python3 \"{target}\"'"


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

    content = "\n".join(cleaned).rstrip()
    if content:
        content += "\n\n"
    content += (
        f"{PROFILE_START}\n"
        f"{_flow_alias(app_directory)}\n"
        f"{PROFILE_END}\n"
    )
    profile.write_text(content, encoding="utf-8")


def _valid_launcher_configuration(documents: Path, app_directory: Path) -> bool:
    """Confirma que una ventana nueva de a-Shell podrá resolver ``flow``."""
    launcher = documents / "bin" / "flow.py"
    profile = documents / ".profile"
    if not launcher.is_file() or not profile.is_file():
        return False
    try:
        content = profile.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return (
        content.count(PROFILE_START) == 1
        and content.count(PROFILE_END) == 1
        and _flow_alias(app_directory) in content
    )


def _remove_profile_configuration(documents: Path) -> None:
    profile = documents / ".profile"
    try:
        previous = profile.read_text(encoding="utf-8")
    except OSError:
        return
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
        if inside_flowmobile_block or re.match(r"^\s*alias\s+flow\s*=", line):
            continue
        cleaned.append(line)
    content = "\n".join(cleaned).rstrip()
    profile.write_text(content + ("\n" if content else ""), encoding="utf-8")


def _merge_directory(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if not target.exists():
            shutil.move(str(child), str(target))
        elif child.is_dir() and target.is_dir():
            _merge_directory(child, target)


def _clean_installations(candidates: list[Path], preserved: Path) -> None:
    """Elimina código anterior después de rescatar datos personales."""
    preserved.mkdir(parents=True, exist_ok=True)
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)

    for candidate in unique:
        if not candidate.is_dir():
            continue
        for name in PRESERVED_ITEMS:
            source = candidate / name
            destination = preserved / name
            if source.is_dir():
                _merge_directory(source, destination)
            elif source.is_file() and not destination.exists():
                shutil.move(str(source), str(destination))
        shutil.rmtree(candidate)


def _restore_preserved(preserved: Path, app_directory: Path) -> None:
    app_directory.mkdir(parents=True, exist_ok=True)
    for name in PRESERVED_ITEMS:
        source = preserved / name
        destination = app_directory / name
        if source.exists() and not destination.exists():
            shutil.move(str(source), str(destination))


def _copy_preserved(source_directory: Path, app_directory: Path) -> None:
    if not source_directory.is_dir():
        return
    app_directory.mkdir(parents=True, exist_ok=True)
    for name in PRESERVED_ITEMS:
        source = source_directory / name
        destination = app_directory / name
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        elif source.is_file():
            shutil.copy2(source, destination)


def _valid_installation(directory: Path) -> bool:
    return (
        (directory / "main.py").is_file()
        and (directory / "flow").is_dir()
        and (directory / "VERSION").is_file()
    )


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
    preserved = work_directory / "preserved"
    rollback = documents / ROLLBACK_NAME

    print("Instalando FlowMobile para a-Shell…")
    try:
        if rollback.exists():
            if _valid_installation(app_directory):
                shutil.rmtree(rollback)
            else:
                if app_directory.exists():
                    shutil.rmtree(app_directory)
                shutil.move(str(rollback), str(app_directory))

        _download_source_archive(repository, branch, archive)
        _safe_extract(archive, work_directory)
        source = _find_source(work_directory)
        if not _valid_installation(source):
            raise RuntimeError("La versión descargada no superó la validación previa.")

        legacy_candidates = [
            documents / PRESERVED_DATA_NAME,
            documents / "FlowIOS",
            documents / "FlowApp",
        ]
        _clean_installations(
            [candidate for candidate in legacy_candidates if candidate != app_directory],
            preserved,
        )

        try:
            if app_directory.exists():
                shutil.move(str(app_directory), str(rollback))
            shutil.move(str(source), str(app_directory))
            _copy_preserved(rollback, app_directory)
            _copy_preserved(preserved, app_directory)
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
            if not _valid_installation(app_directory):
                raise RuntimeError("La instalación nueva quedó incompleta.")
            if not _valid_launcher_configuration(documents, app_directory):
                raise RuntimeError("No se pudo registrar el comando flow en a-Shell.")
        except Exception:
            shutil.rmtree(app_directory, ignore_errors=True)
            if rollback.exists():
                shutil.move(str(rollback), str(app_directory))
                _copy_preserved(preserved, app_directory)
                _configure_profile(documents, app_directory)
            else:
                saved = documents / PRESERVED_DATA_NAME
                _copy_preserved(preserved, saved)
                (bin_directory / "flow.py").unlink(missing_ok=True)
                _remove_profile_configuration(documents)
            raise
        else:
            shutil.rmtree(rollback, ignore_errors=True)
    finally:
        shutil.rmtree(work_directory, ignore_errors=True)

    print("FlowMobile instalado para iOS con una copia limpia.")
    print("El comando flow quedó registrado correctamente.")
    print("Esta misma ventana todavía no ha recargado .profile.")
    print("Para abrirlo aquí, ejecuta AHORA como una orden separada:")
    print("cd && . ./.profile && flow")
    print("También puedes abrir una ventana NUEVA de a-Shell y escribir: flow")
    return app_directory


def main(arguments: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if arguments is None else arguments)
    repository = values[0] if values else DEFAULT_REPOSITORY
    if len(values) > 1 and values[1].startswith("&"):
        print(
            "a-Shell no admite && en la orden de instalación. "
            "Ejecuta solo el enlace y después abre una ventana nueva.",
            file=sys.stderr,
        )
        return 1
    branch = values[1] if len(values) > 1 else os.environ.get("FLOWMOBILE_BRANCH", "main")
    try:
        install(repository, branch)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"No se pudo instalar FlowMobile: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
