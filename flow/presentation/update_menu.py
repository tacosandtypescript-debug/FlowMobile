from __future__ import annotations

from datetime import datetime
import threading
from typing import TYPE_CHECKING

import yt_dlp

from flow import APP_VERSION
from flow.infrastructure.ffmpeg import tools_status
from flow.infrastructure.platform import PLATFORM
from flow.infrastructure.settings import save_settings
from flow.infrastructure.updates import (
    UpdateResult,
    check_available_updates,
    is_newer,
    update_ffmpeg,
    update_flowmobile,
    update_ytdlp,
)
from flow.presentation.theme import *

if TYPE_CHECKING:
    from flow.infrastructure.updates import UpdateCheck
    from flow.presentation.cli import FlowCLI


def record_update_check(cli: "FlowCLI", check: "UpdateCheck") -> tuple[bool, bool, bool, bool]:
    flow_pending = is_newer(check.flow_latest, APP_VERSION)
    if flow_pending:
        cli.flow_update_version = check.flow_latest
        cli.flow_release_notes = check.release_notes
    elif check.flow_latest is not None:
        cli.flow_update_version = None
        cli.flow_release_notes = ()
    ytdlp_pending = is_newer(check.ytdlp_latest, yt_dlp.version.__version__)
    ffmpeg_available, ffprobe_available = tools_status()
    cli._tools_status = (ffmpeg_available, ffprobe_available)
    cli.settings.last_update_check = datetime.now().isoformat(timespec="seconds")
    cli.settings.last_update_ok = (
        not bool(check.error)
        and check.repository is not None
        and check.flow_latest is not None
        and check.ytdlp_latest is not None
        and ffmpeg_available
        and ffprobe_available
        and not flow_pending
        and not ytdlp_pending
        and not check.ffmpeg_pending
    )
    try:
        save_settings(cli.settings)
    except OSError:
        pass
    return flow_pending, ytdlp_pending, ffmpeg_available, ffprobe_available


def _print_tool_status(name: str, available: bool) -> None:
    color = GREEN if available else YELLOW
    mark = "✓" if available else "!"
    status = "disponible" if available else "no encontrado"
    print(f"{color}{mark} {name} {status}{RESET}")


def _print_version_line(
    label: str,
    pending: bool,
    current: str,
    latest: str | None,
) -> None:
    if latest is None:
        print(f"{YELLOW}! No se pudo verificar la versión de {label}.{RESET}")
    elif pending:
        print(f"{YELLOW}! {label} {latest} disponible (actual {current}).{RESET}")
    else:
        print(f"{GREEN}✓ {label} {current}{RESET}")


def _perform_updates(
    cli: "FlowCLI",
    ytdlp_pending: bool,
    ffmpeg_pending: bool,
    termux_tools_missing: bool,
    repository: str | None,
    flow_ref: str | None,
) -> None:
    if ytdlp_pending:
        print(f"{CYAN}Actualizando yt-dlp y EJS…{RESET}")
        result = update_ytdlp()
        if result.ok:
            print(f"{GREEN}✓ yt-dlp actualizado.{RESET}")
        else:
            print(f"{RED}✗ No se pudo actualizar yt-dlp: {result.detail}{RESET}")

    if ffmpeg_pending or termux_tools_missing:
        action = "Instalando" if termux_tools_missing else "Actualizando"
        print(f"{CYAN}{action} FFmpeg desde Termux…{RESET}")
        result = update_ffmpeg()
        if result.ok:
            print(f"{GREEN}✓ FFmpeg preparado.{RESET}")
        else:
            print(f"{RED}✗ No se pudo preparar FFmpeg: {result.detail}{RESET}")

    if repository and cli.flow_update_version:
        print(f"{CYAN}Actualizando FlowMobile con respaldo automático…{RESET}")
        result = update_flowmobile(repository, flow_ref or "main")
        if result.ok:
            print(f"{GREEN}✓ FlowMobile actualizado. Vuelve a ejecutar: flow{RESET}")
            cli.pause()
            raise SystemExit(0)
        print(f"{RED}✗ No se pudo actualizar FlowMobile: {result.detail}{RESET}")
        print(f"{GRAY}La versión anterior se conserva cuando el instalador falla.{RESET}")


def check_updates(cli: "FlowCLI", force: bool = False, interactive: bool = False) -> None:
    if not force and not cli.settings.auto_updates:
        return
    cli.logo("COMPROBAR ACTUALIZACIONES")
    print(f"{CYAN}Revisando FlowMobile y sus herramientas…{RESET}")
    with cli._update_lock:
        check = check_available_updates()
        flow_pending, ytdlp_pending, ffmpeg_available, ffprobe_available = (
            cli.record_update_check(check)
        )
    ffmpeg_pending = check.ffmpeg_pending
    termux_tools_missing = PLATFORM.is_termux and not (ffmpeg_available and ffprobe_available)

    if check.repository is None:
        print(f"{YELLOW}! FlowMobile: repositorio de GitHub sin configurar.{RESET}")
    elif check.flow_latest is None:
        print(f"{YELLOW}! No se pudo verificar la versión de FlowMobile.{RESET}")
    elif flow_pending:
        print(f"{YELLOW}! FlowMobile {check.flow_latest} disponible (actual {APP_VERSION}).{RESET}")
        print(f"\n{MAGENTA}{BOLD}NOVEDADES DE LA VERSIÓN{RESET}")
        if check.release_notes:
            for note in check.release_notes:
                print(f"{CYAN}•{RESET} {note}")
        else:
            print(f"{GRAY}Hay una nueva versión lista para instalar.{RESET}")
    else:
        print(f"{GREEN}✓ FlowMobile {APP_VERSION}{RESET}")

    _print_version_line("yt-dlp", ytdlp_pending, yt_dlp.version.__version__, check.ytdlp_latest)
    _print_tool_status("FFmpeg", ffmpeg_available)
    if ffmpeg_pending:
        print(f"{YELLOW}! Termux tiene una actualización de FFmpeg disponible.{RESET}")
    _print_tool_status("FFprobe", ffprobe_available)

    if check.error:
        print(f"{YELLOW}No se pudo verificar todo: {check.error[:180]}{RESET}")

    if flow_pending or ytdlp_pending or ffmpeg_pending or termux_tools_missing:
        print()
        selected = cli.prompt_choice("¿Quieres actualizar ahora? [1] Sí  [2] No", {"1", "2"})
        if selected == "2":
            print(f"{GRAY}La actualización se volverá a ofrecer al abrir FlowMobile.{RESET}")
            cli.pause()
            return
        _perform_updates(cli, ytdlp_pending, ffmpeg_pending, termux_tools_missing, check.repository, check.flow_ref)
        print(f"{GRAY}Reabre FlowMobile para cargar las herramientas nuevas.{RESET}")
        cli.pause()
    elif interactive:
        if ffmpeg_available and ffprobe_available:
            print(f"\n{GREEN}Todo lo verificable está actualizado.{RESET}")
        else:
            print(f"\n{YELLOW}No hay actualizaciones, pero faltan herramientas.{RESET}")
        if PLATFORM.is_ashell and (not ffmpeg_available or not ffprobe_available):
            print(f"{GRAY}FFmpeg y FFprobe se actualizan junto con a-Shell.{RESET}")
        cli.pause()


def start_background_update_check(cli: "FlowCLI") -> None:
    """Comprueba Internet sin impedir que aparezca el menú principal."""
    if cli.update_check_running:
        return
    cli.update_check_running = True

    def worker() -> None:
        try:
            with cli._update_lock:
                if cli.settings.auto_updates:
                    check = check_available_updates(include_package_manager=False)
                    cli.record_update_check(check)
                else:
                    cli._tools_status = tools_status()
        finally:
            cli.update_check_running = False

    threading.Thread(
        target=worker,
        name="flowmobile-update-check",
        daemon=True,
    ).start()
