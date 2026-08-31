from __future__ import annotations
from contextlib import contextmanager, redirect_stdout
from io import StringIO
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any

from flow import APP_NAME, APP_VERSION
from flow.application.media_service import MediaService
from flow.application.real_tests import (
    full_cases,
    quick_cases,
    save_report,
    verification_dict,
    verify_download,
)
from flow.domain.cancellation import DownloadCancelled, cancellation_requested
from flow.domain.errors import friendly_error
from flow.domain.formatting import format_bytes, format_time
from flow.domain.models import DownloadChoice, MediaInfo
from flow.domain.progress import DownloadProgress
from flow.domain.sites import platform_name
from flow.domain.urls import is_web_url
from flow.infrastructure.clipboard import clipboard_urls
from flow.infrastructure.ffmpeg import tools_status
from flow.infrastructure.history import HistoryError, load_history, search_history
from flow.infrastructure.batches import (
    DownloadQueue,
    create_queue,
    list_queues,
    save_queue,
)
from flow.infrastructure.device import notify_complete, open_share, play_media
from flow.infrastructure.paths import (
    AUDIO_DIR,
    DOWNLOAD_DIR,
    TERMUX_DOWNLOADS_PUBLIC,
    VIDEO_DIR,
)
from flow.infrastructure.platform import PLATFORM
from flow.infrastructure.repair import (
    clean_temporary_files,
    dependency_statuses,
    repair_dependencies,
)
from flow.infrastructure.settings import load_settings
from flow.infrastructure.updates import is_newer
from flow.presentation.theme import *
from flow.presentation.tools_menu import (
    show_diagnostic as run_diagnostic_menu,
    show_sessions as run_sessions_menu,
    show_settings as run_settings_menu,
    show_tools as run_tools_menu,
    show_uninstall as run_uninstall_menu,
)
from flow.presentation.update_menu import (
    check_updates as run_update_menu,
    record_update_check as run_record_update_check,
    start_background_update_check as run_background_update_check,
)


class FlowCLI:
    def __init__(self) -> None:
        self.service = MediaService()
        self.settings = load_settings()
        self.download_progress = DownloadProgress()
        cached_version = self.settings.last_flow_version
        self.flow_update_version: str | None = (
            cached_version if is_newer(cached_version, APP_VERSION) else None
        )
        self.flow_release_notes: tuple[str, ...] = (
            self.settings.last_flow_release_notes if self.flow_update_version else ()
        )
        self.update_check_running = False
        self._update_lock = threading.Lock()
        self._tools_status: tuple[bool, bool] | None = None
        self._last_accessible_progress = -10
        self._menu_ready = threading.Event()
        self._announced_update_version: str | None = getattr(
            self.settings, "last_announced_flow_version", None
        )

    def announce_background_update(self, version: str) -> None:
        """Avisa incluso si la consulta termina mientras input espera una opción."""
        if self._announced_update_version == version:
            return
        self._announced_update_version = version
        self._menu_ready.wait(timeout=5)
        output = sys.__stdout__ or sys.stdout
        output.write(
            f"\n\a{YELLOW}{BOLD}! FlowMobile {version} disponible.{RESET}\n"
            f"{CYAN}[5] Actualizar{RESET}\n"
        )
        output.flush()

    def ensure_download_storage(self) -> bool:
        """Impide que Termux vuelva a ocultar descargas en sus datos privados."""
        if not PLATFORM.is_termux or TERMUX_DOWNLOADS_PUBLIC:
            return True
        self.logo("PERMISO DE ALMACENAMIENTO")
        print(f"{YELLOW}FlowMobile no iniciará una descarga en la carpeta privada de Termux.{RESET}")
        print(f"{GRAY}Ejecuta: termux-setup-storage{RESET}")
        print(f"{GRAY}Acepta el permiso de archivos de Android y vuelve a abrir flow.{RESET}")
        print(f"{GRAY}Los videos quedarán en Movies/FlowMobile para aparecer en Galería.{RESET}")
        self.pause()
        return False

    def clear(self) -> None:
        mode = getattr(getattr(self, "settings", None), "interface_mode", "compact")
        if mode == "accessible":
            print("\n\n", end="", flush=True)
        else:
            print("\033[2J\033[H", end="", flush=True)

    @contextmanager
    def buffered_screen(self):
        """Entrega la pantalla en un solo bloque para evitar tirones en a-Shell."""
        buffer = StringIO()
        with redirect_stdout(buffer):
            yield
        sys.stdout.write(buffer.getvalue())
        sys.stdout.flush()

    def line(self, width: int = 32) -> str:
        return "─" * width

    def logo(self, title: str) -> None:
        self.clear()
        current_tools = self._tools_status
        if current_tools is None:
            status = f"{CYAN}…{RESET}"
        elif all(current_tools):
            status = f"{GREEN}✓{RESET}"
        else:
            status = f"{YELLOW}!{RESET}"
        print(
            f"{MAGENTA}{BOLD}{APP_NAME}{RESET} {GRAY}{APP_VERSION}{RESET} "
            f"{status} {GRAY}{PLATFORM.mobile_os}{RESET}"
        )
        print(f"{WHITE}{BOLD}{title}{RESET}")

    def pause(self) -> None:
        self.read_input(f"{GRAY}Enter…{RESET} ")

    def read_input(self, prompt: str) -> str:
        try:
            return input(prompt)
        except EOFError:
            print(
                f"\n{YELLOW}La entrada interactiva no está disponible. "
                f"Abre una terminal nueva y ejecuta flow.{RESET}"
            )
            raise SystemExit(0) from None

    def menu_item(self, number: str, title: str, detail: str = "") -> None:
        suffix = f"  {GRAY}{detail}{RESET}" if detail else ""
        print(f"{CYAN}[{number}]{RESET} {title}{suffix}")

    def section(self, title: str) -> None:
        print(f"{GRAY}{title}{RESET}")

    def prompt_choice(self, prompt: str, valid: set[str]) -> str:
        normalized = {value.lower() for value in valid}
        while True:
            choice = self.read_input(
                f"\n{WHITE}{prompt}{RESET} {CYAN}›{RESET} "
            ).strip().lower()
            if choice in normalized:
                return choice
            options = ", ".join(
                sorted(
                    normalized,
                    key=lambda value: (
                        not value.isdigit(),
                        int(value) if value.isdigit() else value,
                    ),
                )
            )
            print(f"{YELLOW}Opción no válida. Usa: {options}.{RESET}")

    def prompt_url(self, prompt: str = "Enlace › ") -> str:
        if self.settings.clipboard_detection:
            candidates = clipboard_urls()
            if candidates:
                candidate = candidates[0]
                host = platform_name(candidate)
                answer = self.read_input(
                    f"{GREEN}Enlace de {host} detectado en el portapapeles.{RESET} "
                    f"¿Usarlo? [S/n] › "
                ).strip().casefold()
                if answer in {"", "s", "si", "sí", "1"}:
                    return candidate
        return self.read_input(prompt).strip()

    def dashboard(self) -> None:
        def folder_stats(folder: Path) -> tuple[int, int]:
            try:
                count = size = 0
                with os.scandir(folder) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            count += 1
                            size += entry.stat(follow_symlinks=False).st_size
                return count, size
            except OSError:
                return 0, 0

        videos, video_size = folder_stats(VIDEO_DIR)
        audios, audio_size = folder_stats(AUDIO_DIR)
        try:
            free = shutil.disk_usage(VIDEO_DIR).free
        except OSError:
            free = 0
        current_tools = self._tools_status
        tools_ok = bool(current_tools and all(current_tools))
        if current_tools is None:
            tools_label, tools_color = "○ sistema", CYAN
        elif tools_ok:
            tools_label, tools_color = "✓ sistema", GREEN
        else:
            tools_label, tools_color = "! sistema", YELLOW
        if not self.settings.auto_updates:
            update_label, update_color = "○ manual", GRAY
        elif self.update_check_running:
            update_label, update_color = "○ buscando", CYAN
        elif self.settings.last_update_ok is True:
            update_label, update_color = "✓ al día", GREEN
        elif self.settings.last_update_ok is False:
            update_label, update_color = "! actualizar", YELLOW
        else:
            update_label, update_color = "○ sin comprobar", GRAY

        last_title = ""
        try:
            history = load_history()
            if history:
                last_title = str(history[0].get("title") or "Sin título")[:28]
        except HistoryError:
            last_title = ""

        print(
            f"{GRAY}{videos}v {format_bytes(video_size)} · "
            f"{audios}a {format_bytes(audio_size)} · "
            f"{format_bytes(free)} libre{RESET}"
        )
        print(f"{tools_color}{tools_label}{RESET}  {update_color}{update_label}{RESET}")
        if last_title:
            print(f"{GRAY}{last_title}{RESET}")

    def draw_progress(self, percent: float, speed: str, eta: str) -> None:
        if self.settings.interface_mode == "accessible":
            step = min(100, int(percent // 10) * 10)
            if step <= self._last_accessible_progress and percent < 100:
                return
            self._last_accessible_progress = step
            print(f"Progreso {percent:.0f}% · {speed} · restante {eta}")
            return
        width = 12
        filled = max(0, min(width, round(width * percent / 100)))
        bar = "█" * filled + "░" * (width - filled)
        print(
            f"\r\033[2K{CYAN}[{GREEN}{bar}{CYAN}] "
            f"{percent:5.1f}% {YELLOW}{speed} {MAGENTA}ETA {eta}{RESET}",
            end="",
            flush=True,
        )

    def progress_hook(self, data: dict[str, Any]) -> None:
        status = data.get("status")
        if status == "downloading":
            if cancellation_requested():
                raise DownloadCancelled()
            snapshot = self.download_progress.update(data)
            if snapshot is None:
                return
            self.draw_progress(
                snapshot.percent,
                f"{format_bytes(snapshot.speed)}/s",
                format_time(snapshot.eta),
            )
        elif status == "finished":
            self.draw_progress(100.0, "—", "00:00")
            print()

    def conversion_progress(self, percent: float) -> None:
        self.draw_progress(percent, "Convirtiendo", "--:--")

    def show_error(self, url: str, error: Exception) -> None:
        title, hint = friendly_error(url, error)
        print(f"{RED}{BOLD}{title}{RESET}")
        print(f"{YELLOW}{hint}{RESET}")

    @staticmethod
    def featured_resolutions(resolutions: list[int]) -> list[int]:
        """Mantiene visible la mejor calidad sin saturar pantallas pequeñas."""
        if len(resolutions) <= 8:
            return resolutions

        selected = {resolutions[0], resolutions[-1]}
        for target in (2160, 1440, 1080, 720, 480, 360):
            closest = min(resolutions, key=lambda value: abs(value - target))
            selected.add(closest)
        return sorted(selected, reverse=True)

    def choose_quality(self, media: MediaInfo) -> DownloadChoice | None:
        resolutions = self.service.resolutions(media)

        if self.settings.default_kind != "ask":
            if self.settings.default_kind == "audio":
                preferred = DownloadChoice(
                    "audio",
                    audio_format=self.settings.audio_format,
                )
                audio_label = {
                    "auto": "M4A/MP3 automático",
                    "m4a": "M4A",
                    "mp3": "MP3",
                }[self.settings.audio_format]
                description = f"Solo audio · {audio_label}"
            else:
                height = (
                    None
                    if self.settings.video_quality == "best"
                    else int(self.settings.video_quality)
                )
                preferred = DownloadChoice("video", height)
                description = (
                    "Video · mejor calidad disponible"
                    if height is None
                    else f"Video · hasta {height}p"
                )
            print()
            print(f"{GRAY}Preferencia:{RESET} {description}")
            print(f"{GREEN}[1]{RESET} Usar  {CYAN}[2]{RESET} Elegir  {RED}[0]{RESET} Cancelar")
            selected = self.prompt_choice("Selecciona", {"0", "1", "2"})
            if selected == "0":
                return None
            if selected == "1":
                return preferred

        show_all = False
        while True:
            actions: dict[str, DownloadChoice] = {}
            displayed = resolutions if show_all else self.featured_resolutions(resolutions)

            print()
            print(f"{GRAY}Calidad{RESET}")

            audio = DownloadChoice("audio", None, self.settings.audio_format)
            audio_size = self.service.estimated_size(media, audio)
            audio_label = {
                "auto": "M4A/MP3",
                "m4a": "M4A",
                "mp3": "MP3",
            }[self.settings.audio_format]
            size_text = format_bytes(audio_size) if audio_size else "—"
            print(f"{GREEN}[1]{RESET} Audio {audio_label}  {GRAY}{size_text}{RESET}")
            actions["1"] = audio

            option = 2
            if displayed:
                for index, height in enumerate(displayed):
                    choice = DownloadChoice("video", height)
                    size = self.service.estimated_size(media, choice)
                    badge = f" {GREEN}★{RESET}" if index == 0 else ""
                    size_text = format_bytes(size) if size else "—"
                    print(
                        f"{CYAN}[{option}]{RESET} {height}p{badge}  {GRAY}{size_text}{RESET}"
                    )
                    actions[str(option)] = choice
                    option += 1
            else:
                print(f"{YELLOW}Sin resoluciones exactas.{RESET}")
                choice = DownloadChoice("video", None)
                print(f"{CYAN}[{option}]{RESET} Mejor disponible")
                actions[str(option)] = choice

            valid = set(actions) | {"0"}
            if displayed != resolutions:
                print(f"{MAGENTA}[M]{RESET} {len(resolutions)} calidades")
                valid.add("m")
            print(f"{RED}[0]{RESET} Cancelar")

            selected = self.prompt_choice("Selecciona calidad", valid)
            if selected == "m":
                show_all = True
                self.logo("ELEGIR CALIDAD")
                print(f"{GRAY}{media.title[:38]}{RESET}")
                continue
            return None if selected == "0" else actions.get(selected)

    def after_download(self, path: Path, kind: str) -> None:
        media_label = "AUDIO" if kind == "audio" else "VIDEO"
        android_location = (
            "Almacenamiento interno › Music › FlowMobile"
            if kind == "audio"
            else "Almacenamiento interno › Movies › FlowMobile"
        )
        while True:
            print()
            print(f"{GREEN}{BOLD}{media_label} listo{RESET}  {GRAY}{path.name}{RESET}")
            if PLATFORM.is_termux:
                print(f"{GRAY}{android_location}{RESET}")
            elif PLATFORM.is_ashell:
                print(
                    f"{GRAY}Archivos › a-Shell › FlowMobile › Downloads › {path.parent.name}{RESET}"
                )
            else:
                print(f"{GRAY}{path.parent}{RESET}")
            share_label = (
                "Abrir carpeta" if getattr(PLATFORM, "is_desktop", False) else "Compartir"
            )
            self.menu_item("1", share_label)
            self.menu_item("2", "Reproducir")
            self.menu_item("3", "Ubicación")
            self.menu_item("4", "Menú")
            self.menu_item("0", "Salir")

            choice = self.prompt_choice("Selecciona", {"0", "1", "2", "3", "4"})
            if choice == "1":
                if not open_share(path):
                    print(f"{RED}No se pudo abrir el archivo o su ubicación.{RESET}")
                    if PLATFORM.is_termux:
                        print(f"{YELLOW}Alternativa manual:{RESET}")
                        print(f"{GRAY}Abre Archivos › {android_location}, mantén pulsado el archivo y toca Compartir.{RESET}")
                    elif PLATFORM.is_ashell:
                        print(f"{YELLOW}Alternativa manual:{RESET}")
                        print(
                            f"{GRAY}Abre Archivos › a-Shell › FlowMobile › Downloads, "
                            "mantén pulsado el archivo y toca Compartir.{RESET}"
                        )
                        print(
                            f"{GRAY}Desde esa hoja puedes Guardar vídeo en Fotos o enviarlo.{RESET}"
                        )
                else:
                    message = "Ubicación abierta." if getattr(PLATFORM, "is_desktop", False) else f"Archivo enviado a la vista de {PLATFORM.mobile_os}."
                    print(f"{GREEN}{message}{RESET}")
                self.pause()
            elif choice == "2":
                if not play_media(path):
                    print(f"{RED}No se pudo abrir el reproductor.{RESET}")
                self.pause()
            elif choice == "3":
                print(path)
                self.pause()
            elif choice == "4":
                return
            elif choice == "0":
                raise SystemExit(0)

    def new_download(self) -> None:
        if not self.ensure_download_storage():
            return
        self.logo("DESCARGAR")
        print(f"{GRAY}Enlace, o 0 para volver.{RESET}")
        url = self.prompt_url()

        if url == "0":
            return

        if not is_web_url(url):
            print(f"{RED}El enlace no es válido.{RESET}")
            self.pause()
            return

        try:
            print(f"{CYAN}Analizando enlace...{RESET}", end="", flush=True)
            media = self.service.inspect(url)
            print(f"\r\033[2K{GREEN}Enlace analizado correctamente.{RESET}")
        except Exception as exc:
            print(f"\r\033[2K{RED}No se pudo analizar el enlace.{RESET}")
            self.show_error(url, exc)
            self.pause()
            return

        print()
        print(f"{WHITE}{BOLD}{media.title[:42]}{RESET}")
        print(
            f"{GRAY}{media.platform} · {media.uploader[:22]} · "
            f"{format_time(media.duration)}{RESET}"
        )
        detected = self.service.resolutions(media)
        if detected:
            values = " ".join(f"{value}p" for value in detected[:8])
            suffix = " …" if len(detected) > 8 else ""
            print(f"{GRAY}{values}{suffix}{RESET}")
        else:
            print(f"{YELLOW}Sin resoluciones separadas.{RESET}")

        choice = self.choose_quality(media)
        if choice is None:
            return

        print(f"\n{YELLOW}Cancelar conservando progreso: c + Enter o Ctrl+C.{RESET}")
        self.download_progress.reset()
        self._last_accessible_progress = -10
        result = self.service.download(
            media,
            choice,
            self.progress_hook,
            self.conversion_progress,
        )

        if not result.ok or result.file is None:
            if isinstance(result.error, DownloadCancelled):
                partials = len(result.error.partial_files)
                print(f"\n{YELLOW}{BOLD}DESCARGA PAUSADA{RESET}")
                print(f"{GRAY}Se conservaron {partials} archivos recuperables.{RESET}")
                print(f"{CYAN}Pega el mismo enlace para continuar desde ese punto.{RESET}")
                self.pause()
                return
            print(f"\n{RED}{BOLD}✗ ERROR DE DESCARGA{RESET}")
            self.show_error(media.url, result.error or RuntimeError("Error desconocido"))
            if result.file is not None and result.file.exists():
                print(f"{YELLOW}El archivo original se conservó en:{RESET} {result.file}")
            self.pause()
            return

        print(f"\n{GREEN}{BOLD}✓ Listo{RESET}  {GRAY}{format_bytes(result.file.stat().st_size)}{RESET}")
        if result.quality:
            print(f"{GREEN}{result.quality}{RESET}")
        if result.warning:
            print(f"{YELLOW}Aviso: {result.warning}{RESET}")
        notify_complete(result.file)
        self.after_download(result.file, choice.kind)

    def print_history(self, history: list[dict[str, Any]]) -> None:
        if not history:
            print(f"{GRAY}No se encontraron descargas.{RESET}")
            return
        for index, item in enumerate(history[:15], 1):
            print(f"{CYAN}{index:02d}{RESET} {(item.get('title') or 'Sin título')[:36]}")
            print(
                f"    {GRAY}{item.get('platform', '')} · "
                f"{item.get('type', '')} · "
                f"{item.get('resolution') or '—'} · "
                f"{format_bytes(item.get('size'))}{RESET}"
            )

    def show_history(self) -> None:
        try:
            history = load_history()
        except HistoryError as exc:
            self.logo("HISTORIAL")
            print(f"{RED}{exc}{RESET}")
            self.pause()
            return
        while True:
            self.logo("HISTORIAL")
            self.print_history(history)
            self.menu_item("1", "Buscar")
            self.menu_item("0", "Volver")
            choice = self.prompt_choice("Selecciona", {"0", "1"})
            if choice == "0":
                return
            query = self.read_input("Buscar › ").strip()
            self.logo(f"RESULTADOS: {query[:24] or 'TODOS'}")
            self.print_history(search_history(query, history))
            self.pause()

    def show_system_repair(self) -> None:
        while True:
            self.logo("SISTEMA")
            if PLATFORM.is_termux:
                storage = "Android público" if TERMUX_DOWNLOADS_PUBLIC else "permiso pendiente"
                print(f"{GRAY}Almacenamiento: {storage}{RESET}")
            for status in dependency_statuses():
                mark = "✓" if status.ok else "!"
                color = GREEN if status.ok else YELLOW
                print(f"{color}{mark} {status.name:<10}{RESET} {GRAY}{status.detail}{RESET}")
            print()
            self.menu_item("1", "Reparar", "yt-dlp, EJS, FFmpeg")
            self.menu_item("2", "Limpiar temporales")
            self.menu_item("3", "Reparar y limpiar")
            self.menu_item("0", "Volver")
            choice = self.prompt_choice("Selecciona", {"0", "1", "2", "3"})
            if choice == "0":
                return
            if choice in {"1", "3"}:
                print(f"\n{CYAN}Reparando dependencias…{RESET}")
                for label, result in repair_dependencies():
                    color, mark = (GREEN, "✓") if result.ok else (RED, "✗")
                    detail = f" — {result.detail}" if result.detail else ""
                    print(f"{color}{mark} {label}{RESET}{detail}")
            if choice in {"2", "3"}:
                cleaned = clean_temporary_files()
                print(
                    f"\n{GREEN}✓ {cleaned.removed} temporales eliminados; "
                    f"{format_bytes(cleaned.recovered_bytes)} recuperados.{RESET}"
                )
                if cleaned.failed:
                    print(f"{YELLOW}{cleaned.failed} archivos no pudieron eliminarse.{RESET}")
            print(f"\n{GRAY}Las descargas completas, el historial y los ajustes no se tocaron.{RESET}")
            self.pause()

    def show_real_tests(self) -> None:
        if not self.ensure_download_storage():
            return
        self.logo("PRUEBAS")
        print(f"{YELLOW}Descargan archivos reales.{RESET}")
        self.menu_item("1", "Rápida", "360p + M4A")
        self.menu_item("2", "Completa", "5 plataformas")
        self.menu_item("0", "Volver")
        mode = self.prompt_choice("Selecciona", {"0", "1", "2"})
        if mode == "0":
            return

        targets: list[tuple[str, str]] = []
        if mode == "1":
            url = self.read_input("Enlace de prueba › ").strip()
            if url:
                targets.append(("Enlace", url))
            cases = quick_cases()
        else:
            print(f"\n{GRAY}Pega un enlace por sitio; Enter lo omite.{RESET}")
            for site in ("YouTube", "TikTok", "Facebook", "Instagram", "X"):
                url = self.read_input(f"{site} › ").strip()
                if url:
                    targets.append((site, url))
            cases = full_cases()
        if not targets:
            print(f"{YELLOW}No se indicó ningún enlace.{RESET}")
            self.pause()
            return

        rows: list[dict[str, object]] = []
        last_file: Path | None = None
        for requested_site, url in targets:
            try:
                media = self.service.inspect(url)
            except Exception as exc:
                title, hint = friendly_error(url, exc)
                print(f"\n{RED}✗ {requested_site}: {title}{RESET}\n{YELLOW}{hint}{RESET}")
                rows.append({"platform": requested_site, "case": "análisis", "ok": False, "summary": title})
                continue
            print(f"\n{MAGENTA}{BOLD}{media.platform}: {media.title[:34]}{RESET}")
            for test_case in cases:
                print(f"{CYAN}Probando {test_case.label}…{RESET}")
                self.download_progress.reset()
                result = self.service.download(
                    media,
                    test_case.choice,
                    self.progress_hook,
                    self.conversion_progress,
                )
                if not result.ok or result.file is None:
                    detail = str(result.error or "error desconocido")[:180]
                    print(f"{RED}✗ {detail}{RESET}")
                    rows.append({"platform": media.platform, "case": test_case.label, "ok": False, "summary": detail})
                    continue
                checked = verify_download(result.file, test_case.choice)
                color, mark = (GREEN, "✓") if checked.ok else (RED, "✗")
                print(
                    f"{color}{mark} {checked.summary}{RESET} · "
                    f"{format_bytes(checked.size)} · compartir {'OK' if checked.share_ready else 'NO'}"
                )
                rows.append({
                    "platform": media.platform,
                    "case": test_case.label,
                    **verification_dict(checked),
                })
                if checked.ok:
                    last_file = result.file

        report = save_report(rows)
        passed = sum(bool(row.get("ok")) for row in rows)
        print(f"\n{MAGENTA}{BOLD}RESULTADO: {passed}/{len(rows)} correctas{RESET}")
        print(f"{GRAY}Informe privado: {report}{RESET}")
        if last_file is not None:
            print(f"\n{CYAN}[1]{RESET} Abrir Compartir con el último archivo")
            print(f"{RED}[0]{RESET} Volver")
            if self.prompt_choice("Verificación final", {"0", "1"}) == "1":
                if open_share(last_file):
                    print(f"{GREEN}✓ Vista Compartir abierta. Confirma visualmente el archivo.{RESET}")
                else:
                    print(f"{RED}✗ El dispositivo no pudo abrir la vista Compartir.{RESET}")
        self.pause()

    def show_sessions(self) -> None:
        run_sessions_menu(self)

    def read_batch_links(self) -> list[str]:
        print(f"{GRAY}Pega un enlace por línea. Enter vacío inicia la cola.{RESET}")
        urls: list[str] = []
        if self.settings.clipboard_detection:
            detected = clipboard_urls()
            if detected:
                answer = self.read_input(
                    f"{GREEN}{len(detected)} enlace(s) detectado(s) en el portapapeles.{RESET} "
                    "¿Añadirlos? [S/n] › "
                ).strip().casefold()
                if answer in {"", "s", "si", "sí", "1"}:
                    urls.extend(detected)
        while True:
            value = self.read_input(f"Enlace {len(urls) + 1} › ").strip()
            if not value:
                return list(dict.fromkeys(urls))
            if not is_web_url(value):
                print(f"{YELLOW}Enlace omitido: no es una URL web válida.{RESET}")
                continue
            urls.append(value)

    def process_queue(self, queue: DownloadQueue) -> None:
        if not self.ensure_download_storage():
            return
        self.logo(f"LOTE {queue.queue_id}")
        print(f"{GRAY}Carpeta separada: {queue.folder}{RESET}")
        print(f"{YELLOW}Cancelar archivo actual: c + Enter o Ctrl+C.{RESET}\n")
        last_file: Path | None = None
        total = len(queue.items)
        for index, item in enumerate(queue.items, 1):
            if item.status == "completed":
                continue
            print(f"{MAGENTA}{BOLD}[{index}/{total}]{RESET} Analizando…")
            item.status = "downloading"
            item.error = ""
            save_queue(queue)
            try:
                media = self.service.inspect(item.url)
                item.title = media.title
                save_queue(queue)
            except KeyboardInterrupt:
                item.status = "paused"
                item.error = "Pausada durante el análisis"
                save_queue(queue)
                print(f"{YELLOW}Cola pausada antes de descargar este elemento.{RESET}")
                break
            except Exception as exc:
                title, _ = friendly_error(item.url, exc)
                item.status = "error"
                item.error = title
                save_queue(queue)
                print(f"{RED}✗ {title}{RESET}")
                continue

            print(f"{CYAN}{media.title[:42]}{RESET}")
            self.download_progress.reset()
            self._last_accessible_progress = -10
            result = self.service.download(
                media,
                queue.choice,
                self.progress_hook,
                self.conversion_progress,
                video_dir=queue.folder,
                audio_dir=queue.folder,
            )
            if result.ok and result.file is not None:
                item.status = "completed"
                item.file = str(result.file)
                last_file = result.file
                print(f"{GREEN}✓ Completada · {format_bytes(result.file.stat().st_size)}{RESET}")
            elif isinstance(result.error, DownloadCancelled):
                item.status = "paused"
                item.error = "Pausada por la persona"
                save_queue(queue)
                print(f"{YELLOW}Cola pausada. Los .part se conservaron.{RESET}")
                break
            else:
                item.status = "error"
                item.error = str(result.error or "Error desconocido")[:180]
                print(f"{RED}✗ {item.error}{RESET}")
            save_queue(queue)

        print(f"\n{MAGENTA}{BOLD}COLA: {queue.completed}/{total} completadas{RESET}")
        print(f"{GRAY}{queue.pending} pendientes, pausadas o con error.{RESET}")
        if last_file is not None:
            notify_complete(last_file)
        self.pause()

    def create_batch(self, urls: list[str]) -> None:
        if not self.ensure_download_storage():
            return
        if not urls:
            print(f"{YELLOW}No se añadieron enlaces.{RESET}")
            self.pause()
            return
        try:
            print(f"{CYAN}Analizando el primer enlace para elegir calidad…{RESET}")
            first_media = self.service.inspect(urls[0])
        except Exception as exc:
            self.show_error(urls[0], exc)
            self.pause()
            return
        choice = self.choose_quality(first_media)
        if choice is None:
            return
        queue = create_queue(urls, choice)
        self.process_queue(queue)

    def resume_batch(self) -> None:
        queues = list_queues(incomplete_only=True)[:9]
        self.logo("REANUDAR COLA")
        if not queues:
            print(f"{GRAY}No hay colas pendientes.{RESET}")
            self.pause()
            return
        actions: dict[str, DownloadQueue] = {}
        for index, queue in enumerate(queues, 1):
            actions[str(index)] = queue
            print(
                f"{CYAN}[{index}]{RESET} {queue.queue_id} · "
                f"{queue.completed}/{len(queue.items)} completas"
            )
        print(f"{RED}[0]{RESET} Volver")
        selected = self.prompt_choice("Selecciona", set(actions) | {"0"})
        if selected != "0":
            self.process_queue(actions[selected])

    def show_batches(self) -> None:
        while True:
            self.logo("LOTES")
            pending = len(list_queues(incomplete_only=True))
            print(f"{GRAY}Pendientes: {pending}{RESET}")
            self.menu_item("1", "Varios enlaces")
            self.menu_item("2", "Playlist")
            self.menu_item("3", "Reanudar")
            self.menu_item("0", "Volver")
            choice = self.prompt_choice("Selecciona", {"0", "1", "2", "3"})
            if choice == "0":
                return
            if choice == "1":
                self.create_batch(self.read_batch_links())
            elif choice == "2":
                url = self.prompt_url("Enlace de playlist › ")
                try:
                    print(f"{CYAN}Leyendo playlist…{RESET}")
                    urls = self.service.playlist_urls(url)
                except Exception as exc:
                    self.show_error(url, exc)
                    self.pause()
                    continue
                print(f"{GREEN}✓ {len(urls)} elementos detectados.{RESET}")
                if urls:
                    confirm = self.prompt_choice("¿Crear esta cola? [1] Sí  [2] No", {"1", "2"})
                    if confirm == "1":
                        self.create_batch(urls)
                else:
                    self.pause()
            elif choice == "3":
                self.resume_batch()

    def show_tools_menu(self) -> None:
        run_tools_menu(self)

    def show_diagnostic(self) -> None:
        run_diagnostic_menu(self)

    def show_uninstall(self) -> None:
        run_uninstall_menu(self)

    def show_files(self) -> None:
        self.logo("ARCHIVOS")
        for label, folder in (("Vídeo", VIDEO_DIR), ("Audio", AUDIO_DIR)):
            print(f"{MAGENTA}{BOLD}{label}{RESET}")
            if PLATFORM.is_termux:
                android_folder = "Movies › FlowMobile" if label == "Vídeo" else "Music › FlowMobile"
                print(f"{GRAY}{android_folder}{RESET}")
            try:
                files = sorted(
                    (path for path in folder.iterdir() if path.is_file()),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
            except OSError as exc:
                print(f"{RED}No se pudo leer la carpeta: {exc}{RESET}")
                files = []
            if not files:
                print(f"  {GRAY}Sin archivos.{RESET}")
            for path in files[:5]:
                try:
                    size = format_bytes(path.stat().st_size)
                except OSError:
                    size = "—"
                print(f"  {GREEN}•{RESET} {path.name[:48]} {GRAY}({size}){RESET}")
            if len(files) > 5:
                print(f"  {GRAY}y {len(files) - 5} más…{RESET}")
            print()
        self.pause()

    def record_update_check(self, check: Any) -> tuple[bool, bool, bool, bool]:
        return run_record_update_check(self, check)

    def check_updates(self, force: bool = False, interactive: bool = False) -> None:
        run_update_menu(self, force=force, interactive=interactive)

    def start_background_update_check(self) -> None:
        run_background_update_check(self)

    def show_settings(self) -> None:
        run_settings_menu(self)

    def run(self) -> None:
        self.start_background_update_check()
        while True:
            with self.buffered_screen():
                self.logo("MENÚ")
                self.dashboard()
                print()
                self.menu_item("1", "Descargar")
                self.menu_item("2", "Lotes")
                self.menu_item("3", "Historial")
                self.menu_item("4", "Archivos")
                if self.flow_update_version:
                    self.menu_item("5", f"Actualizar {self.flow_update_version}")
                else:
                    self.menu_item("5", "Actualizar")
                self.menu_item("6", "Más")
                self.menu_item("0", "Salir")

            self._menu_ready.set()
            choice = self.prompt_choice(
                "Selecciona",
                {"0", "1", "2", "3", "4", "5", "6"},
            )
            if choice == "1":
                self.new_download()
            elif choice == "2":
                self.show_batches()
            elif choice == "3":
                self.show_history()
            elif choice == "4":
                self.show_files()
            elif choice == "5":
                self.check_updates(force=True, interactive=True)
            elif choice == "6":
                self.show_tools_menu()
            elif choice == "0":
                self.clear()
                print("FlowMobile cerrado.")
                return


def main() -> None:
    try:
        FlowCLI().run()
    except KeyboardInterrupt:
        print("\nFlowMobile cerrado.")
