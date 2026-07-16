from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from flow.domain.formatting import format_bytes
from flow.infrastructure.device import open_share
from flow.infrastructure.diagnostics import save_diagnostic_report
from flow.infrastructure.sessions import import_cookies, remove_cookies, session_status
from flow.infrastructure.settings import save_settings
from flow.infrastructure.uninstall import uninstall
from flow.presentation.theme import *

if TYPE_CHECKING:
    from flow.presentation.cli import FlowCLI


def show_sessions(cli: "FlowCLI") -> None:
    def _import() -> None:
        raw_path = cli.read_input("Ruta del archivo cookies.txt › ").strip().strip("\"'")
        try:
            imported = import_cookies(Path(raw_path))
            print(f"{GREEN}✓ {imported.cookies} cookies guardadas de forma privada.{RESET}")
        except ValueError as exc:
            print(f"{RED}{exc}{RESET}")
        cli.pause()

    def _remove() -> None:
        confirm = cli.prompt_choice("¿Eliminar cookies? [1] Sí  [2] No", {"1", "2"})
        if confirm == "1":
            remove_cookies()
            print(f"{GREEN}Sesión eliminada.{RESET}")
            cli.pause()

    while True:
        cli.logo("COOKIES Y SESIONES")
        status = session_status()
        if status.configured:
            print(f"{GREEN}✓ Sesión privada configurada{RESET}")
            print(f"{GRAY}{status.cookies} cookies · {format_bytes(status.size)}{RESET}")
        else:
            print(f"{GRAY}No hay cookies importadas.{RESET}")
        print(f"\n{YELLOW}Nunca pegues contraseñas o tokens directamente en la terminal.{RESET}")
        cli.menu_item("1", "Importar cookies.txt", "formato Netscape exportado por el navegador")
        cli.menu_item("2", "Eliminar sesión privada")
        cli.menu_item("0", "Volver")
        choice = cli.prompt_choice("Selecciona", {"0", "1", "2"})
        if choice == "0":
            return
        if choice == "1":
            _import()
        elif choice == "2":
            _remove()


def show_tools(cli: "FlowCLI") -> None:
    cli.ui.run_menu(
        "HERRAMIENTAS",
        {
            "1": ("Cookies y sesiones", "", cli.show_sessions),
            "2": ("Sistema", "", cli.show_system),
            "3": ("Modo Reparar", "", cli.show_repair),
            "4": ("Ajustes", "", cli.show_settings),
            "5": ("Pruebas reales", "", cli.show_real_tests),
            "6": ("Informe de diagnóstico", "privado y preparado para compartir", cli.show_diagnostic),
            "7": ("Desinstalar FlowMobile", "", cli.show_uninstall),
        },
        tools_status=cli._tools_status,
    )


def show_diagnostic(cli: "FlowCLI") -> None:
    cli.logo("INFORME DE DIAGNÓSTICO")
    try:
        report = save_diagnostic_report()
    except OSError as exc:
        print(f"{RED}No se pudo crear el informe: {exc}{RESET}")
        cli.pause()
        return
    print(f"{GREEN}✓ Informe creado sin enlaces, cookies ni rutas privadas.{RESET}")
    print(f"{GRAY}{report.name}{RESET}")
    choice = cli.prompt_choice("¿Compartirlo ahora? [1] Sí  [2] No", {"1", "2"})
    if choice == "1" and not open_share(report):
        print(f"{YELLOW}No se pudo abrir la vista para compartir.{RESET}")
    cli.pause()


def show_uninstall(cli: "FlowCLI") -> None:
    cli.logo("DESINSTALAR FLOWMOBILE")
    print(f"{YELLOW}Esta acción elimina el comando flow y el código instalado.{RESET}\n")
    cli.menu_item("1", "Desinstalar y conservar datos", "mantiene descargas, historial, colas y cookies")
    cli.menu_item("2", "Borrar absolutamente todo", "incluye descargas, cookies, colas, historial y ajustes")
    cli.menu_item("0", "Cancelar")
    choice = cli.prompt_choice("Selecciona", {"0", "1", "2"})
    if choice == "0":
        return
    purge_all = choice == "2"
    if purge_all:
        print(f"\n{RED}{BOLD}Esta opción no se puede deshacer.{RESET}")
        confirmation = cli.read_input("Escribe BORRAR para continuar › ").strip()
        if confirmation != "BORRAR":
            print(f"{GRAY}Desinstalación cancelada.{RESET}")
            cli.pause()
            return
    else:
        confirmation = cli.prompt_choice(
            "¿Desinstalar conservando tus datos? [1] Sí  [2] No",
            {"1", "2"},
        )
        if confirmation == "2":
            return

    print(f"{CYAN}Eliminando FlowMobile…{RESET}")
    try:
        with cli._update_lock:
            result = uninstall(purge_all=purge_all)
    except (OSError, ValueError) as exc:
        print(f"{RED}No se pudo completar la desinstalación: {exc}{RESET}")
        cli.pause()
        return
    if result.errors:
        print(f"{YELLOW}FlowMobile se eliminó parcialmente:{RESET}")
        for error in result.errors[:5]:
            print(f"{YELLOW}• {error}{RESET}")
    else:
        print(f"{GREEN}✓ FlowMobile fue eliminado correctamente.{RESET}")
    if purge_all:
        print(f"{GRAY}También se eliminaron todos los datos y descargas.{RESET}")
    else:
        print(f"{GRAY}La carpeta del programa también fue eliminada.{RESET}")
        if result.preserved_at:
            print(f"{GRAY}Datos para reinstalar: {result.preserved_at}{RESET}")
    print(f"{GRAY}Cierra esta ventana de terminal. El comando flow ya no estará disponible.{RESET}")
    raise SystemExit(0)


def show_settings(cli: "FlowCLI") -> None:
    kind_labels = {"ask": "Preguntar siempre", "video": "Video", "audio": "Solo audio"}
    audio_labels = {"auto": "Automático", "m4a": "M4A", "mp3": "MP3"}

    def _choose_quality() -> None:
        quality_options = {
            "1": ("best", "Mejor"),
            "2": ("2160", "2160p"),
            "3": ("1440", "1440p"),
            "4": ("1080", "1080p"),
            "5": ("720", "720p"),
            "6": ("480", "480p"),
            "7": ("360", "360p"),
        }
        print("\n[1] Mejor  [2] 2160p  [3] 1440p  [4] 1080p")
        print("[5] 720p   [6] 480p   [7] 360p")
        value = cli.prompt_choice("Calidad máxima", set(quality_options) | {"0"})
        if value in quality_options:
            cli.settings.video_quality = quality_options[value][0]

    def _choose_format() -> None:
        print("\n[1] Preguntar siempre  [2] Video  [3] Solo audio")
        value = cli.prompt_choice("Formato", {"1", "2", "3"})
        cli.settings.default_kind = {"1": "ask", "2": "video", "3": "audio"}[value]

    def _choose_audio() -> None:
        print("\n[1] Automático recomendado  [2] M4A  [3] MP3")
        value = cli.prompt_choice("Formato de audio", {"1", "2", "3"})
        cli.settings.audio_format = {"1": "auto", "2": "m4a", "3": "mp3"}[value]

    def _toggle_updates() -> None:
        print("\n[1] Comprobar en cada inicio  [2] Desactivar")
        value = cli.prompt_choice("Actualizaciones", {"1", "2"})
        cli.settings.auto_updates = value == "1"

    while True:
        cli.logo("AJUSTES")
        quality = (
            "Mejor disponible"
            if cli.settings.video_quality == "best"
            else f"Hasta {cli.settings.video_quality}p"
        )
        cli.menu_item("1", "Formato predeterminado", kind_labels[cli.settings.default_kind])
        cli.menu_item("2", "Calidad de video", quality)
        auto_label = "Comprobar al iniciar" if cli.settings.auto_updates else "Desactivadas"
        cli.menu_item("3", "Formato de audio", audio_labels[cli.settings.audio_format])
        cli.menu_item("4", "Comprobar actualizaciones", auto_label)
        clipboard_label = "Detectar al descargar" if cli.settings.clipboard_detection else "Desactivado"
        cli.menu_item("5", "Portapapeles", clipboard_label)
        cli.menu_item("6", "Colores", "Activados" if cli.settings.colors else "Desactivados")
        mode_label = "Compacta" if cli.settings.interface_mode == "compact" else "Accesible"
        cli.menu_item("7", "Interfaz", mode_label)
        cli.menu_item("0", "Volver")
        choice = cli.prompt_choice("Selecciona", {"0", "1", "2", "3", "4", "5", "6", "7"})
        if choice == "0":
            return
        if choice == "1":
            _choose_format()
        elif choice == "2":
            _choose_quality()
        elif choice == "3":
            _choose_audio()
        elif choice == "4":
            _toggle_updates()
        elif choice == "5":
            cli.settings.clipboard_detection = not cli.settings.clipboard_detection
        elif choice == "6":
            cli.settings.colors = not cli.settings.colors
            print(f"{GRAY}El cambio de colores se aplicará al volver a abrir FlowMobile.{RESET}")
        elif choice == "7":
            print("\n[1] Compacta y rápida  [2] Accesible, sin limpiar pantalla")
            value = cli.prompt_choice("Interfaz", {"1", "2"})
            cli.settings.interface_mode = "compact" if value == "1" else "accessible"
        try:
            save_settings(cli.settings)
        except OSError as exc:
            print(f"{RED}No se pudieron guardar los ajustes: {exc}{RESET}")
            cli.pause()
