#!/usr/bin/env python3
"""Instalador nativo de FlowMobile para a-Shell.

a-Shell ejecuta Python y otros comandos mediante ios_system. Invocar esos
comandos desde un proceso ``sh``/``dash`` separado no es compatible, por eso
este instalador realiza toda la preparación dentro del mismo proceso Python.
"""

from __future__ import annotations

import os
import hashlib
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
import errno
from io import StringIO
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_REPOSITORY = "tacosandtypescript-debug/FlowMobile"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PRESERVED_ITEMS = ("Downloads", ".flowmobile", "flow_settings.json")
PRESERVED_DATA_NAME = ".flowmobile-data"
ROLLBACK_NAME = ".flowmobile-rollback"
PROFILE_START = "# >>> FlowMobile launcher >>>"
PROFILE_END = "# <<< FlowMobile launcher <<<"
INSTALL_LOG_NAME = ".flowmobile-install.log"


def _console_print(text: str = "", *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    try:
        print(text, file=stream)
    except UnicodeEncodeError:
        encoding = stream.encoding or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding), file=stream)


@dataclass(frozen=True, slots=True)
class InstallProblem:
    code: str
    cause: str
    hint: str
    technical: str


class InstallerUI:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.verbose = os.environ.get("FLOWMOBILE_VERBOSE") == "1"
        self.stage = "Preparando"
        self.number = 0
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("FlowMobile installer log\n", encoding="utf-8")
        try:
            log_path.chmod(0o600)
        except OSError:
            pass

    def start(self, stage: str) -> None:
        self.number += 1
        self.stage = stage
        _console_print(f"[{self.number}/6] {stage}…")
        self.write(f"\n== {stage} ==\n")

    def done(self, detail: str = "") -> None:
        suffix = f" · {detail}" if detail else ""
        _console_print(f"      ✓ Listo{suffix}")

    def write(self, text: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(text)

    def run_pip(self, arguments: list[str]) -> tuple[int, str]:
        from pip._internal.cli.main import main as pip_main

        if self.verbose:
            output = StringIO()
            with self.log_path.open("a", encoding="utf-8") as log:
                stdout = _TeeStream(sys.stdout, log, output)
                stderr = _TeeStream(sys.stderr, log, output)
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = pip_main(arguments)
            return status, _last_useful_line(output.getvalue())
        output = StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            status = pip_main(arguments)
        captured = output.getvalue()
        self.write(captured)
        return status, _last_useful_line(captured) or f"pip terminó con código {status}"


class _TeeStream:
    def __init__(self, console, log, captured: StringIO) -> None:
        self.console = console
        self.log = log
        self.captured = captured

    def write(self, text: str) -> int:
        self.console.write(text)
        self.log.write(text)
        self.captured.write(text)
        return len(text)

    def flush(self) -> None:
        self.console.flush()
        self.log.flush()

    def isatty(self) -> bool:
        return False


class ReportedInstallError(RuntimeError):
    """Error ya explicado al usuario; evita imprimir un segundo mensaje genérico."""


def _last_useful_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:300] if lines else "Sin detalle adicional"


def _diagnose_install_error(exc: BaseException, stage: str) -> InstallProblem:
    technical = _last_useful_line(str(exc))
    if isinstance(exc, HTTPError):
        code = exc.code
        if code == 404:
            return InstallProblem(
                "FM-IOS-HTTP-404", "GitHub no encontró el archivo de instalación.",
                "Espera unos minutos y confirma que exista un release estable.", technical,
            )
        if code in {403, 429}:
            return InstallProblem(
                f"FM-IOS-HTTP-{code}", "GitHub limitó temporalmente la descarga.",
                "Cambia de red o espera unos minutos antes de repetir.", technical,
            )
        return InstallProblem(
            f"FM-IOS-HTTP-{code}", f"GitHub respondió con HTTP {code}.",
            "Comprueba la conexión y vuelve a intentarlo.", technical,
        )
    if isinstance(exc, URLError):
        return InstallProblem(
            "FM-IOS-NETWORK", "a-Shell no pudo conectarse a GitHub.",
            "Comprueba internet, DNS o VPN y repite el mismo comando.", technical,
        )
    if isinstance(exc, tarfile.TarError):
        return InstallProblem(
            "FM-IOS-ARCHIVE", "El paquete descargado está incompleto o dañado.",
            "Borra el intento anterior y repite con una conexión estable.", technical,
        )
    if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
        return InstallProblem(
            "FM-IOS-SPACE", "No queda espacio suficiente en el dispositivo.",
            "Libera espacio en Archivos y vuelve a ejecutar el instalador.", technical,
        )
    if isinstance(exc, PermissionError):
        return InstallProblem(
            "FM-IOS-PERMISSION", "a-Shell no pudo escribir en Documents.",
            "Usa a-Shell completa y revisa su acceso a Archivos.", technical,
        )
    lowered = str(exc).casefold()
    if "sha-256" in lowered or "integridad" in lowered or "manifiesto" in lowered:
        return InstallProblem(
            "FM-IOS-INTEGRITY", "La verificación de seguridad no coincide.",
            "No omitas esta comprobación; vuelve a descargar desde el repositorio oficial.", technical,
        )
    if stage == "Dependencias" or "pip" in lowered:
        return InstallProblem(
            "FM-IOS-PIP", "No se pudieron preparar yt-dlp y EJS.",
            "Actualiza a-Shell completa, comprueba internet y repite la instalación.", technical,
        )
    if stage == "Activando flow":
        return InstallProblem(
            "FM-IOS-LAUNCHER", "No se pudo registrar el comando flow.",
            "Ejecuta: cd && . ./.profile && flow", technical,
        )
    return InstallProblem(
        "FM-IOS-INSTALL", f"La instalación falló durante «{stage}».",
        "Consulta el registro y repite el comando de instalación.", technical,
    )


def _show_install_problem(problem: InstallProblem, stage: str, log_path: Path) -> None:
    _console_print(f"\n✕ Instalación detenida en: {stage}", error=True)
    _console_print(f"Código: {problem.code}", error=True)
    _console_print(f"Causa: {problem.cause}", error=True)
    _console_print(f"Detalle: {problem.technical}", error=True)
    _console_print(f"Solución: {problem.hint}", error=True)
    _console_print(f"Registro completo: {log_path}", error=True)


def documents_directory(home: Path | None = None) -> Path:
    base = (home or Path.home()).expanduser()
    return base if base.name == "Documents" else base / "Documents"


def _download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "FlowMobile-installer"})
    last_error: OSError | None = None
    for attempt in range(2):
        try:
            with urlopen(request, timeout=60) as response, destination.open("wb") as output:
                shutil.copyfileobj(response, output)
            return
        except HTTPError as exc:
            if attempt == 0 and (exc.code == 429 or 500 <= exc.code < 600):
                last_error = exc
                destination.unlink(missing_ok=True)
                time.sleep(1)
                continue
            raise
        except (OSError, URLError) as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt == 0:
                time.sleep(1)
    assert last_error is not None
    raise last_error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_checksum(text: str, filename: str) -> str:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == filename:
            value = parts[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", value):
                return value
    raise RuntimeError(f"SHA-256 no publicado para {filename}.")


def _download_source_archive(repository: str, reference: str, destination: Path) -> None:
    if re.fullmatch(r"v?\d+(?:\.\d+){1,3}", reference):
        version = reference.lstrip("v")
        filename = f"FlowMobile-{version}.tar.gz"
        base = f"https://github.com/{repository}/releases/download/{reference}"
        checksum_file = destination.with_name("SHA256SUMS")
        _download(f"{base}/SHA256SUMS", checksum_file)
        _download(f"{base}/{filename}", destination)
        expected = _expected_checksum(checksum_file.read_text(encoding="utf-8"), filename)
        if _sha256(destination) != expected:
            destination.unlink(missing_ok=True)
            raise RuntimeError("El paquete no coincide con el SHA-256 del release oficial.")
        return
    if os.environ.get("FLOWMOBILE_ALLOW_UNVERIFIED") != "1":
        raise RuntimeError("Solo se permiten releases estables verificados.")
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


def _verify_source_manifest(source: Path) -> None:
    manifest = source / "SECURITY_MANIFEST.sha256"
    if not manifest.is_file():
        raise RuntimeError("El release no contiene el manifiesto de seguridad.")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            raise RuntimeError("El manifiesto de seguridad no es válido.")
        relative = parts[1].lstrip("*")
        target = (source / relative).resolve()
        if os.path.commonpath((str(source.resolve()), str(target))) != str(source.resolve()):
            raise RuntimeError("El manifiesto contiene una ruta no segura.")
        if not target.is_file() or _sha256(target) != parts[0].lower():
            raise RuntimeError(f"Falló la integridad del archivo: {relative}")


def _install_python_dependencies(app_directory: Path, ui: InstallerUI | None = None) -> None:
    try:
        from pip._internal.cli.main import main as pip_main
    except ImportError as exc:
        raise RuntimeError("pip no está disponible en esta instalación de a-Shell.") from exc

    arguments = [
        "install", "--disable-pip-version-check", "--require-hashes",
        "--only-binary=:all:", "--no-deps", "--upgrade", "--quiet",
        "--progress-bar=off", "--retries", "1", "--timeout", "30",
        "-r", str(app_directory / "requirements.lock"),
    ]
    if ui is None:
        status = pip_main(arguments)
        detail = f"pip terminó con código {status}"
    else:
        status, detail = ui.run_pip(arguments)
    if status:
        raise RuntimeError(f"pip no pudo instalar yt-dlp y yt-dlp-ejs: {detail}")


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


def _activate_current_session(app_directory: Path, executor=None) -> bool:
    """Registra el alias en el diccionario global de ios_system de a-Shell."""
    if executor is None:
        try:
            import ctypes

            executor = ctypes.CDLL(None).ios_system
            executor.argtypes = (ctypes.c_char_p,)
            executor.restype = ctypes.c_int
        except (AttributeError, ImportError, OSError):
            return False
    try:
        return executor(_flow_alias(app_directory).encode("utf-8")) == 0
    except (OSError, TypeError, ValueError):
        return False


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
    rollback = documents / ROLLBACK_NAME
    log_path = Path(os.environ.get("FLOWMOBILE_INSTALL_LOG", documents / INSTALL_LOG_NAME))
    try:
        ui = InstallerUI(log_path)
    except OSError as exc:
        problem = _diagnose_install_error(exc, "Preparando")
        _show_install_problem(problem, "Preparando", log_path)
        raise ReportedInstallError(problem.code) from exc
    work_directory: Path | None = None
    activated_current = False

    _console_print("\nFlowMobile · Instalación para a-Shell")
    _console_print("La salida técnica se guardará en un registro privado.\n")
    try:
        ui.start("Preparando")
        temporary_root.mkdir(parents=True, exist_ok=True)
        bin_directory.mkdir(parents=True, exist_ok=True)
        work_directory = Path(
            tempfile.mkdtemp(prefix="flowmobile-install-", dir=temporary_root)
        )
        archive = work_directory / "flowmobile.tar.gz"
        preserved = work_directory / "preserved"
        if rollback.exists():
            if _valid_installation(app_directory):
                shutil.rmtree(rollback)
            else:
                if app_directory.exists():
                    shutil.rmtree(app_directory)
                shutil.move(str(rollback), str(app_directory))
        ui.done("entorno listo")

        ui.start("Descargando")
        _download_source_archive(repository, branch, archive)
        ui.done("release oficial")

        ui.start("Verificando")
        _safe_extract(archive, work_directory)
        source = _find_source(work_directory)
        _verify_source_manifest(source)
        if not _valid_installation(source):
            raise RuntimeError("La versión descargada no superó la validación previa.")
        installed_version = (source / "VERSION").read_text(encoding="utf-8").strip()
        ui.done(f"SHA-256 · v{installed_version}")

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
            ui.start("Instalando")
            if app_directory.exists():
                shutil.move(str(app_directory), str(rollback))
            shutil.move(str(source), str(app_directory))
            _copy_preserved(rollback, app_directory)
            _copy_preserved(preserved, app_directory)
            (app_directory / ".flowmobile-source").write_text(
                repository + "\n", encoding="utf-8"
            )
            ui.done("datos anteriores conservados")

            ui.start("Dependencias")
            _install_python_dependencies(app_directory, ui)
            if not _valid_installation(app_directory):
                raise RuntimeError("La instalación nueva quedó incompleta.")
            ui.done("yt-dlp y EJS")

            ui.start("Activando flow")
            # ios_system reconoce scripts Python por su extensión. El comando corto
            # se registra como alias en .profile para que funcione desde cualquier
            # carpeta y no dependa de que a-Shell interprete un archivo sin .py.
            (bin_directory / "flow").unlink(missing_ok=True)
            launcher = bin_directory / "flow.py"
            shutil.copy2(app_directory / "scripts" / "flow_ios.py", launcher)
            _configure_profile(documents, app_directory)
            if not _valid_launcher_configuration(documents, app_directory):
                raise RuntimeError("No se pudo registrar el comando flow en a-Shell.")
            activated_current = _activate_current_session(app_directory)
            ui.done("comando registrado")
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
    except Exception as exc:
        ui.write(f"\nERROR [{ui.stage}]: {type(exc).__name__}: {exc}\n")
        problem = _diagnose_install_error(exc, ui.stage)
        _show_install_problem(problem, ui.stage, log_path)
        raise ReportedInstallError(problem.code) from exc
    finally:
        if work_directory is not None:
            shutil.rmtree(work_directory, ignore_errors=True)

    _console_print(f"\n✓ FlowMobile {installed_version} instalado correctamente.")
    print(f"Aplicación: {app_directory}")
    print(f"Descargas: {app_directory / 'Downloads'}")
    if activated_current:
        print("Abre ahora con: flow")
    else:
        print("La instalación terminó, pero esta ventana no recargó el alias.")
        print("Ejecuta una vez:")
        print("cd && . ./.profile && flow")
    print("En ventanas nuevas solo necesitas escribir: flow")
    print(f"Registro: {log_path}")
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
    except ReportedInstallError:
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"No se pudo instalar FlowMobile: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
