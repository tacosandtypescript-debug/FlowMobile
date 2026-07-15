from __future__ import annotations
from datetime import datetime
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yt_dlp

from flow import APP_NAME, APP_VERSION
from flow.application.media_service import MediaService
from flow.application.real_tests import (
    full_cases,
    quick_cases,
    save_report,
    verification_dict,
    verify_download,
)
from flow.domain.errors import friendly_error
from flow.domain.formatting import format_bytes, format_time
from flow.domain.models import DownloadChoice, MediaInfo
from flow.domain.progress import DownloadProgress
from flow.infrastructure.ffmpeg import tools_status
from flow.infrastructure.history import HistoryError, load_history, search_history
from flow.infrastructure.device import notify_complete, open_share, play_media
from flow.infrastructure.paths import AUDIO_DIR, VIDEO_DIR
from flow.infrastructure.platform import PLATFORM
from flow.infrastructure.repair import (
    clean_temporary_files,
    dependency_statuses,
    repair_dependencies,
)
from flow.infrastructure.settings import load_settings, save_settings
from flow.infrastructure.updates import (
    check_available_updates,
    is_newer,
    update_ffmpeg,
    update_flowmobile,
    update_ytdlp as update_ytdlp_package,
)
from flow.presentation.theme import *


class FlowCLI:
    def __init__(self) -> None:
        self.service = MediaService()
        self.settings = load_settings()
        self.download_progress = DownloadProgress()
        self.flow_update_version: str | None = None
        self.flow_release_notes: tuple[str, ...] = ()

    def clear(self) -> None:
        print("\033[2J\033[3J\033[H", end="", flush=True)

    def line(self, width: int = 38) -> str:
        return "─" * width

    def logo(self, title: str) -> None:
        self.clear()
        ffmpeg_available, ffprobe_available = tools_status()
        tools_ok = ffmpeg_available and ffprobe_available
        status_color = GREEN if tools_ok else YELLOW
        status_label = "SISTEMA LISTO" if tools_ok else "REVISAR HERRAMIENTAS"
        print(f"{MAGENTA}{BOLD}{APP_NAME}{RESET}")
        print(f"{GRAY}{PLATFORM.mobile_os} · {PLATFORM.name} · v{APP_VERSION}{RESET}")
        print(f"{CYAN}{self.line()}{RESET}")
        print(
            f"{status_color}● {status_label}{RESET}  "
            f"{GRAY}yt-dlp{RESET} {CYAN}{yt_dlp.version.__version__}{RESET}"
        )
        print()
        print(f"{WHITE}{BOLD}{title}{RESET}")
        print(f"{CYAN}{self.line()}{RESET}")

    def pause(self) -> None:
        self.read_input(f"\n{GRAY}Presiona Enter para continuar...{RESET}")

    def read_input(self, prompt: str) -> str:
        try:
            return input(prompt)
        except EOFError:
            print(
                f"\n{YELLOW}La entrada interactiva no está disponible. "
                f"Abre una ventana nueva de a-Shell y ejecuta flow.{RESET}"
            )
            raise SystemExit(0) from None

    def menu_item(self, number: str, title: str, detail: str = "") -> None:
        print(f"{CYAN}{BOLD}[{number}]{RESET} {WHITE}{BOLD}{title}{RESET}")
        if detail:
            print(f"    {GRAY}{detail}{RESET}")

    def section(self, title: str) -> None:
        print(f"\n{MAGENTA}{BOLD}{title}{RESET}")

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

    def dashboard(self) -> None:
        def folder_stats(folder: Path) -> tuple[int, int]:
            try:
                files = [path for path in folder.iterdir() if path.is_file()]
                size = sum(path.stat().st_size for path in files)
                return len(files), size
            except OSError:
                return 0, 0

        videos, video_size = folder_stats(VIDEO_DIR)
        audios, audio_size = folder_stats(AUDIO_DIR)
        try:
            free = shutil.disk_usage(VIDEO_DIR).free
        except OSError:
            free = 0
        ffmpeg_available, ffprobe_available = tools_status()
        tools_ok = ffmpeg_available and ffprobe_available
        tools_label = "✓ Herramientas listas" if tools_ok else "! Revisar herramientas"
        if not self.settings.auto_updates:
            update_label, update_color = "○ Actualización manual", GRAY
        elif self.settings.last_update_ok is True:
            update_label, update_color = "✓ Todo actualizado", GREEN
        elif self.settings.last_update_ok is False:
            update_label, update_color = "! Revisión necesaria", YELLOW
        else:
            update_label, update_color = "○ Aún sin comprobar", GRAY

        last_title = "Ninguna descarga todavía"
        try:
            history = load_history()
            if history:
                last_title = str(history[0].get("title") or "Sin título")[:26]
        except HistoryError:
            last_title = "Historial no disponible"

        def row(text: str, color: str = WHITE) -> None:
            print(f"{MAGENTA}│{RESET} {color}{text[:34]:<34}{RESET} {MAGENTA}│{RESET}")

        print(f"{MAGENTA}╭{self.line(36)}╮{RESET}")
        row("PANEL DE FLOWMOBILE", WHITE + BOLD)
        print(f"{MAGENTA}├{self.line(36)}┤{RESET}")
        row(f"▸ Videos  {videos:>3}  {format_bytes(video_size):>10}", CYAN)
        row(f"▸ Audios  {audios:>3}  {format_bytes(audio_size):>10}", GREEN)
        row(f"▸ Libre         {format_bytes(free):>10}", WHITE)
        row(tools_label, GREEN if tools_ok else YELLOW)
        row(update_label, update_color)
        row(f"Última: {last_title}", GRAY)
        print(f"{MAGENTA}╰{self.line(36)}╯{RESET}")

    def draw_progress(self, percent: float, speed: str, eta: str) -> None:
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
            print(f"{MAGENTA}{BOLD}PREFERENCIA GUARDADA{RESET}")
            print(f"{GREEN}[1]{RESET} Usar {description}")
            print(f"{CYAN}[2]{RESET} Elegir manualmente")
            print(f"{RED}[0]{RESET} Cancelar")
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
            print(f"{MAGENTA}{BOLD}FORMATO Y CALIDAD{RESET}")
            print(f"{CYAN}{self.line()}{RESET}")

            audio = DownloadChoice("audio", None, self.settings.audio_format)
            audio_size = self.service.estimated_size(media, audio)
            audio_label = {
                "auto": "M4A/MP3 automático",
                "m4a": "M4A",
                "mp3": "MP3",
            }[self.settings.audio_format]
            print(
                f"{GREEN}{BOLD}[1] Solo audio{RESET} — {audio_label} "
                f"{GRAY}({format_bytes(audio_size) if audio_size else 'tamaño desconocido'}){RESET}"
            )
            actions["1"] = audio
            print(f"{GRAY}    Extrae el sonido y elimina el video.{RESET}")
            print()

            option = 2
            if displayed:
                for index, height in enumerate(displayed):
                    choice = DownloadChoice("video", height)
                    size = self.service.estimated_size(media, choice)
                    badge = f" {GREEN}★ mejor detectada{RESET}" if index == 0 else ""
                    print(
                        f"{CYAN}[{option}]{RESET} Video — {height}p{badge} "
                        f"{GRAY}({format_bytes(size) if size else 'tamaño desconocido'}){RESET}"
                    )
                    actions[str(option)] = choice
                    option += 1
            else:
                print(f"{YELLOW}No se detectaron resoluciones exactas.{RESET}")
                choice = DownloadChoice("video", None)
                print(f"{CYAN}[{option}]{RESET} Video — mejor calidad disponible")
                actions[str(option)] = choice

            valid = set(actions) | {"0"}
            if displayed != resolutions:
                print(f"{MAGENTA}[M]{RESET} Mostrar las {len(resolutions)} calidades detectadas")
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
        while True:
            print()
            print(f"{GREEN}{BOLD}{media_label} LISTO PARA USAR{RESET}")
            print(f"{MAGENTA}{BOLD}SIGUIENTE ACCIÓN{RESET}")
            self.menu_item(
                "1",
                "Compartir / Guardar en Archivos",
                f"abre la vista de {PLATFORM.mobile_os} para enviar o guardar",
            )
            self.menu_item("2", "Reproducir")
            self.menu_item("3", "Mostrar ubicación")
            self.menu_item("4", "Volver al menú")
            self.menu_item("0", "Salir")

            choice = self.prompt_choice("Selecciona", {"0", "1", "2", "3", "4"})
            if choice == "1":
                if not open_share(path):
                    print(f"{RED}No se pudo abrir la hoja para compartir.{RESET}")
                else:
                    print(f"{GREEN}Archivo enviado a la vista de {PLATFORM.mobile_os}.{RESET}")
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
        self.logo("NUEVA DESCARGA")
        print(f"{GRAY}Pega un enlace web o escribe 0 para volver.{RESET}")
        url = self.read_input("Enlace › ").strip()

        if url == "0":
            return

        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
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
        print(f"{MAGENTA}{BOLD}Vista previa{RESET}")
        print(f"{GRAY}Plataforma:{RESET} {media.platform}")
        print(f"{GRAY}Título:{RESET} {media.title}")
        print(f"{GRAY}Autor:{RESET} {media.uploader}")
        print(f"{GRAY}Duración:{RESET} {format_time(media.duration)}")
        detected = self.service.resolutions(media)
        if detected:
            values = ", ".join(f"{value}p" for value in detected[:10])
            suffix = "…" if len(detected) > 10 else ""
            print(f"{GRAY}Calidades detectadas:{RESET} {values}{suffix}")
        else:
            print(f"{YELLOW}Calidades: el sitio no informó resoluciones separadas.{RESET}")

        choice = self.choose_quality(media)
        if choice is None:
            return

        self.download_progress.reset()
        result = self.service.download(
            media,
            choice,
            self.progress_hook,
            self.conversion_progress,
        )

        if not result.ok or result.file is None:
            print(f"\n{RED}{BOLD}✗ ERROR DE DESCARGA{RESET}")
            self.show_error(media.url, result.error or RuntimeError("Error desconocido"))
            if result.file is not None and result.file.exists():
                print(f"{YELLOW}El archivo original se conservó en:{RESET} {result.file}")
            self.pause()
            return

        print(f"\n{GREEN}{BOLD}✓ DESCARGA COMPLETADA{RESET}")
        print(f"{GRAY}Archivo:{RESET} {result.file.name}")
        print(f"{GRAY}Tamaño:{RESET} {format_bytes(result.file.stat().st_size)}")
        if result.quality:
            print(f"{GRAY}Calidad final verificada:{RESET} {GREEN}{result.quality}{RESET}")
        if result.warning:
            print(f"{YELLOW}Aviso: {result.warning}{RESET}")
        notify_complete(result.file)
        self.after_download(result.file, choice.kind)

    def print_history(self, history: list[dict[str, Any]]) -> None:
        if not history:
            print(f"{GRAY}No se encontraron descargas.{RESET}")
            return
        for index, item in enumerate(history[:15], 1):
            print(f"{GREEN}{index:02d}.{RESET} {(item.get('title') or 'Sin título')[:44]}")
            print(
                f"    {GRAY}{item.get('platform', '')} · "
                f"{item.get('type', '')} · "
                f"{item.get('resolution') or '—'} · "
                f"{format_bytes(item.get('size'))}{RESET}"
            )
            print(f"    {CYAN}{self.line(34)}{RESET}")

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
            print()
            self.menu_item("1", "Buscar", "por título, sitio, tipo, calidad o fecha")
            self.menu_item("0", "Volver")
            choice = self.prompt_choice("Selecciona", {"0", "1"})
            if choice == "0":
                return
            query = self.read_input("Buscar › ").strip()
            self.logo(f"RESULTADOS: {query[:24] or 'TODOS'}")
            self.print_history(search_history(query, history))
            self.pause()

    def show_system(self) -> None:
        self.logo("SISTEMA")
        print("Plataforma:", f"{PLATFORM.name} ({PLATFORM.mobile_os})")
        print("Python:", sys.version.split()[0])
        print("yt-dlp:", yt_dlp.version.__version__)
        ffmpeg_available, ffprobe_available = tools_status()
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                check=False,
            )
            print("FFmpeg:", result.stdout.splitlines()[0] if result.stdout else "Disponible")
        except OSError:
            print("FFmpeg: no encontrado")
        print("FFprobe:", "Disponible" if ffprobe_available else "No encontrado")
        if not ffmpeg_available or not ffprobe_available:
            print(f"{YELLOW}La conversión inteligente requiere ambas herramientas.{RESET}")
            if PLATFORM.is_termux:
                print(f"{GRAY}En Termux usa: pkg install ffmpeg{RESET}")
            else:
                print(f"{GRAY}En a-Shell, actualiza la app para recuperar FFmpeg y FFprobe.{RESET}")
        self.pause()

    def show_repair(self) -> None:
        while True:
            self.logo("MODO REPARAR")
            print(f"{GRAY}Revisa herramientas sin borrar tus descargas.{RESET}\n")
            for status in dependency_statuses():
                mark = "✓" if status.ok else "!"
                color = GREEN if status.ok else YELLOW
                print(f"{color}{mark} {status.name:<10}{RESET} {status.detail}")
            print()
            self.menu_item("1", "Reparar dependencias", "Python no se reemplaza; repara yt-dlp, EJS y multimedia")
            self.menu_item("2", "Limpiar temporales dañados", "solo .part, .ytdl, .tmp y conversiones incompletas")
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
        self.logo("PRUEBAS REALES")
        print(f"{YELLOW}Estas pruebas descargan archivos reales y consumen datos.{RESET}")
        print(f"{GRAY}Usa enlaces públicos propios o que tengas permiso de descargar.{RESET}\n")
        self.menu_item("1", "Prueba rápida", "un enlace · vídeo 360p y audio M4A")
        self.menu_item("2", "Prueba completa", "hasta 30 descargas en cinco plataformas")
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

    def show_files(self) -> None:
        self.logo("ARCHIVOS")
        for label, folder in (("VIDEOS", VIDEO_DIR), ("AUDIO", AUDIO_DIR)):
            print(f"{MAGENTA}{BOLD}{label}{RESET}  {GRAY}{folder}{RESET}")
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

    def check_updates(self, force: bool = False, interactive: bool = False) -> None:
        if not force and not self.settings.auto_updates:
            return
        self.logo("COMPROBAR ACTUALIZACIONES")
        print(f"{CYAN}Revisando FlowMobile y sus herramientas…{RESET}")
        check = check_available_updates()
        flow_pending = is_newer(check.flow_latest, APP_VERSION)
        if flow_pending:
            self.flow_update_version = check.flow_latest
            self.flow_release_notes = check.release_notes
        elif check.flow_latest is not None:
            self.flow_update_version = None
            self.flow_release_notes = ()
        ytdlp_pending = is_newer(check.ytdlp_latest, yt_dlp.version.__version__)
        ffmpeg_pending = check.ffmpeg_pending
        ffmpeg_available, ffprobe_available = tools_status()
        termux_tools_missing = PLATFORM.is_termux and not (
            ffmpeg_available and ffprobe_available
        )

        self.settings.last_update_check = datetime.now().isoformat(timespec="seconds")
        self.settings.last_update_ok = (
            not bool(check.error)
            and check.repository is not None
            and check.flow_latest is not None
            and check.ytdlp_latest is not None
            and ffmpeg_available
            and ffprobe_available
            and not flow_pending
            and not ytdlp_pending
            and not ffmpeg_pending
        )
        try:
            save_settings(self.settings)
        except OSError:
            pass

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

        if flow_pending or ytdlp_pending or ffmpeg_pending or termux_tools_missing:
            print()
            selected = self.prompt_choice("¿Quieres actualizar ahora? [1] Sí  [2] No", {"1", "2"})
            if selected == "2":
                print(f"{GRAY}La actualización se volverá a ofrecer al abrir FlowMobile.{RESET}")
                self.pause()
                return

            if ytdlp_pending:
                print(f"{CYAN}Actualizando yt-dlp y EJS…{RESET}")
                result = update_ytdlp_package()
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

            if flow_pending and check.repository:
                print(f"{CYAN}Actualizando FlowMobile…{RESET}")
                result = update_flowmobile(check.repository)
                if result.ok:
                    print(f"{GREEN}✓ FlowMobile actualizado. Vuelve a ejecutar: flow{RESET}")
                    self.pause()
                    raise SystemExit(0)
                print(f"{RED}✗ No se pudo actualizar FlowMobile: {result.detail}{RESET}")

            print(f"{GRAY}Reabre FlowMobile para cargar las herramientas nuevas.{RESET}")
            self.pause()
        elif interactive:
            if ffmpeg_available and ffprobe_available:
                print(f"\n{GREEN}Todo lo verificable está actualizado.{RESET}")
            else:
                print(f"\n{YELLOW}No hay actualizaciones, pero faltan herramientas.{RESET}")
            if PLATFORM.is_ashell and (not ffmpeg_available or not ffprobe_available):
                print(f"{GRAY}FFmpeg y FFprobe se actualizan junto con a-Shell.{RESET}")
            self.pause()

    def show_settings(self) -> None:
        kind_labels = {"ask": "Preguntar siempre", "video": "Video", "audio": "Solo audio"}
        audio_labels = {"auto": "Automático", "m4a": "M4A", "mp3": "MP3"}
        while True:
            self.logo("AJUSTES")
            quality = (
                "Mejor disponible"
                if self.settings.video_quality == "best"
                else f"Hasta {self.settings.video_quality}p"
            )
            self.menu_item("1", "Formato predeterminado", kind_labels[self.settings.default_kind])
            self.menu_item("2", "Calidad de video", quality)
            auto_label = "Comprobar al iniciar" if self.settings.auto_updates else "Desactivadas"
            self.menu_item("3", "Formato de audio", audio_labels[self.settings.audio_format])
            self.menu_item("4", "Comprobar actualizaciones", auto_label)
            self.menu_item("0", "Volver")
            choice = self.prompt_choice("Selecciona", {"0", "1", "2", "3", "4"})
            if choice == "0":
                return
            if choice == "1":
                print("\n[1] Preguntar siempre  [2] Video  [3] Solo audio")
                value = self.prompt_choice("Formato", {"1", "2", "3"})
                self.settings.default_kind = {"1": "ask", "2": "video", "3": "audio"}[value]
            elif choice == "2":
                print("\n[1] Mejor  [2] 2160p  [3] 1440p  [4] 1080p")
                print("[5] 720p   [6] 480p   [7] 360p")
                value = self.prompt_choice("Calidad máxima", {str(i) for i in range(1, 8)})
                self.settings.video_quality = {
                    "1": "best", "2": "2160", "3": "1440", "4": "1080",
                    "5": "720", "6": "480", "7": "360",
                }[value]
            elif choice == "3":
                print("\n[1] Automático recomendado  [2] M4A  [3] MP3")
                value = self.prompt_choice("Formato de audio", {"1", "2", "3"})
                self.settings.audio_format = {"1": "auto", "2": "m4a", "3": "mp3"}[value]
            elif choice == "4":
                print("\n[1] Comprobar en cada inicio  [2] Desactivar")
                value = self.prompt_choice("Actualizaciones", {"1", "2"})
                self.settings.auto_updates = value == "1"
            try:
                save_settings(self.settings)
            except OSError as exc:
                print(f"{RED}No se pudieron guardar los ajustes: {exc}{RESET}")
                self.pause()

    def run(self) -> None:
        self.check_updates()
        while True:
            self.logo("MENÚ PRINCIPAL")
            self.dashboard()
            self.section("DESCARGAR")
            self.menu_item("1", "Nueva descarga", "analizar enlace y elegir video o audio")
            self.section("BIBLIOTECA")
            self.menu_item("2", "Historial", "últimas 15 descargas")
            self.menu_item("3", "Mis archivos", "ver los archivos más recientes")
            self.section("NOVEDADES")
            if self.flow_update_version:
                self.menu_item(
                    "4",
                    f"¡FlowMobile {self.flow_update_version} disponible!",
                    "ver novedades e instalar la actualización",
                )
            else:
                self.menu_item("4", "Actualizaciones", "buscar versiones y novedades")
            self.section("CONFIGURACIÓN")
            self.menu_item("5", "Sistema", "estado de Python, yt-dlp y FFmpeg")
            self.menu_item("6", "Ajustes", "formato y calidad predeterminados")
            self.menu_item("7", "Modo Reparar", "dependencias y temporales dañados")
            self.menu_item("8", "Pruebas reales", "calidad, códecs, tamaño y compartir")
            print()
            self.menu_item("0", "Salir")

            choice = self.prompt_choice(
                "Selecciona",
                {"0", "1", "2", "3", "4", "5", "6", "7", "8"},
            )
            if choice == "1":
                self.new_download()
            elif choice == "2":
                self.show_history()
            elif choice == "3":
                self.show_files()
            elif choice == "4":
                self.check_updates(force=True, interactive=True)
            elif choice == "5":
                self.show_system()
            elif choice == "6":
                self.show_settings()
            elif choice == "7":
                self.show_repair()
            elif choice == "8":
                self.show_real_tests()
            elif choice == "0":
                self.clear()
                print("FlowMobile cerrado.")
                return


def main() -> None:
    try:
        FlowCLI().run()
    except KeyboardInterrupt:
        print("\nFlowMobile cerrado.")
