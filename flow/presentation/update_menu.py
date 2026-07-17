from __future__ import annotations

from datetime import datetime
import threading
from typing import Any

import yt_dlp

from flow import APP_VERSION
from flow.infrastructure.ffmpeg import tools_status
from flow.infrastructure.platform import PLATFORM
from flow.infrastructure.settings import save_settings
from flow.infrastructure.updates import (
    check_available_updates,
    is_newer,
    update_ffmpeg,
    update_flowmobile,
    update_ytdlp,
)
from flow.presentation.theme import *


def record_update_check(cli: Any, check: Any) -> tuple[bool, bool, bool, bool]:
    flow_pending = is_newer(check.flow_latest, APP_VERSION)
    if flow_pending:
        cli.flow_update_version = check.flow_latest
        cli.flow_release_notes = check.release_notes
    elif check.flow_latest is not None:
        cli.flow_update_version = None
        cli.flow_release_notes = ()
    if check.flow_latest is not None:
        cli.settings.last_flow_version = check.flow_latest
        cli.settings.last_flow_release_notes = check.release_notes
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


def check_updates(cli: Any, force: bool = False, interactive: bool = False) -> None:
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
    repairable_tools_missing = (PLATFORM.is_termux or PLATFORM.is_desktop) and not (
        ffmpeg_available and ffprobe_available
    )

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
    if check.ytdlp_latest is None:
        print(f"{YELLOW}! No se pudo verificar la versión de yt-dlp.{RESET}")
    elif ytdlp_pending:
        print(
            f"{YELLOW}! yt-dlp {check.ytdlp_latest} disponible "
            f"(actual {yt_dlp.version.__version__}).{RESET}"
        )
    else:
        print(f"{GREEN}✓ yt-dlp {yt_dlp.version.__version__}{RESET}")
    print(
        f"{GREEN if ffmpeg_available else YELLOW}"
        f"{'✓' if ffmpeg_available else '!'} FFmpeg "
        f"{'disponible' if ffmpeg_available else 'no disponible'}{RESET}"
    )
    if ffmpeg_pending:
        print(f"{YELLOW}! Termux tiene una actualización de FFmpeg disponible.{RESET}")
    print(
        f"{GREEN if ffprobe_available else YELLOW}"
        f"{'✓' if ffprobe_available else '!'} FFprobe "
        f"{'disponible' if ffprobe_available else 'no disponible'}{RESET}"
    )

    if check.error:
        print(f"{YELLOW}No se pudo verificar todo: {check.error[:180]}{RESET}")

    if flow_pending or ytdlp_pending or ffmpeg_pending or repairable_tools_missing:
        print()
        selected = cli.prompt_choice("¿Quieres actualizar ahora? [1] Sí  [2] No", {"1", "2"})
        if selected == "2":
            print(f"{GRAY}La actualización se volverá a ofrecer al abrir FlowMobile.{RESET}")
            cli.pause()
            return

        if ytdlp_pending:
            print(f"{CYAN}Actualizando yt-dlp y EJS…{RESET}")
            result = update_ytdlp()
            if result.ok:
                message = "yt-dlp actualizado" if result.changed else "dependencias verificadas"
                print(f"{GREEN}✓ {message}.{RESET}")
            else:
                print(f"{RED}✗ No se pudo actualizar yt-dlp: {result.detail}{RESET}")

        if ffmpeg_pending or repairable_tools_missing:
            action = "Instalando" if repairable_tools_missing else "Actualizando"
            print(f"{CYAN}{action} FFmpeg para {PLATFORM.mobile_os}…{RESET}")
            result = update_ffmpeg()
            if result.ok:
                print(f"{GREEN}✓ FFmpeg preparado.{RESET}")
            else:
                print(f"{RED}✗ No se pudo preparar FFmpeg: {result.detail}{RESET}")

        if flow_pending and check.repository:
            print(f"{CYAN}Actualizando FlowMobile con respaldo automático…{RESET}")
            result = update_flowmobile(check.repository, check.flow_ref or "main")
            if result.ok:
                print(f"{GREEN}✓ FlowMobile actualizado. Vuelve a ejecutar: flow{RESET}")
                cli.pause()
                raise SystemExit(0)
            print(f"{RED}✗ No se pudo actualizar FlowMobile: {result.detail}{RESET}")
            print(f"{GRAY}La versión anterior se conserva cuando el instalador falla.{RESET}")

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


def start_background_update_check(cli: Any) -> None:
    """Comprueba Internet sin impedir que aparezca el menú principal."""
    if cli.update_check_running:
        return
    cli.update_check_running = True

    def worker() -> None:
        try:
            with cli._update_lock:
                if cli.settings.auto_updates:
                    previous_version = cli.flow_update_version
                    check = check_available_updates(include_package_manager=False)
                    cli.record_update_check(check)
                    if (
                        cli.flow_update_version
                        and cli.flow_update_version != previous_version
                    ):
                        cli.announce_background_update(cli.flow_update_version)
                else:
                    cli._tools_status = tools_status()
        finally:
            cli.update_check_running = False

    threading.Thread(
        target=worker,
        name="flowmobile-update-check",
        daemon=True,
    ).start()
