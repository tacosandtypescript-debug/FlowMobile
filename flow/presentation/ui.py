from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
from io import StringIO
import sys
from typing import Any, Callable

from flow import APP_NAME, APP_VERSION
from flow.domain.formatting import format_bytes, format_time
from flow.domain.sites import platform_name
from flow.infrastructure.clipboard import clipboard_urls
from flow.infrastructure.platform import PLATFORM
from flow.presentation.theme import *


class ConsoleUI:
    """Utilidades de presentación para la terminal."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self._last_accessible_progress = -10

    def clear(self) -> None:
        if self.settings.interface_mode == "accessible":
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

    @staticmethod
    def line(width: int = 38) -> str:
        return "─" * width

    def logo(self, title: str, tools_status: tuple[bool, bool] | None = None) -> None:
        self.clear()
        tools_ok = bool(tools_status and all(tools_status))
        if tools_status is None:
            status_color, status_label = CYAN, "VERIFICANDO SISTEMA"
        elif tools_ok:
            status_color, status_label = GREEN, "SISTEMA LISTO"
        else:
            status_color, status_label = YELLOW, "REVISAR HERRAMIENTAS"
        print(f"{MAGENTA}{BOLD}{APP_NAME}{RESET}")
        print(f"{GRAY}{PLATFORM.mobile_os} · {PLATFORM.name} · v{APP_VERSION}{RESET}")
        print(f"{CYAN}{self.line()}{RESET}")
        print(
            f"{status_color}● {status_label}{RESET}  "
            f"{GRAY}yt-dlp{RESET} {CYAN}{self._ytdlp_version()}{RESET}"
        )
        print()
        print(f"{WHITE}{BOLD}{title}{RESET}")
        print(f"{CYAN}{self.line()}{RESET}")

    @staticmethod
    def _ytdlp_version() -> str:
        import yt_dlp

        return yt_dlp.version.__version__

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

    @staticmethod
    def menu_item(number: str, title: str, detail: str = "") -> None:
        print(f"{CYAN}{BOLD}[{number}]{RESET} {WHITE}{BOLD}{title}{RESET}")
        if detail:
            print(f"    {GRAY}{detail}{RESET}")

    @staticmethod
    def section(title: str) -> None:
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

    def show_error(self, url: str, error: Exception) -> None:
        from flow.domain.errors import friendly_error

        title, hint = friendly_error(url, error)
        print(f"{RED}{BOLD}{title}{RESET}")
        print(f"{YELLOW}{hint}{RESET}")

    def run_menu(
        self,
        title: str,
        options: dict[str, tuple[str, str, Callable[[], None]],
        tools_status: tuple[bool, bool] | None = None,
    ) -> None:
        """Muestra un menú dinámico y ejecuta la acción seleccionada."""
        while True:
            self.logo(title, tools_status=tools_status)
            for key, (label, detail, _) in options.items():
                self.menu_item(key, label, detail)
            print(f"{RED}[0]{RESET} Volver")
            choice = self.prompt_choice("Selecciona", set(options) | {"0"})
            if choice == "0":
                return
            action = options[choice][2]
            action()


def format_size(value: int | None) -> str:
    return format_bytes(value) if value is not None else "—"


def format_duration(seconds: int | float | None) -> str:
    return format_time(seconds)
