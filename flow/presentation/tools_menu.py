from __future__ import annotations

from pathlib import Path
from typing import Any

from flow.domain.formatting import format_bytes
from flow.domain.sites import PLATFORM_GROUPS, supported_platforms
from flow.infrastructure.device import open_share, open_url
from flow.infrastructure.diagnostics import save_diagnostic_report
from flow.infrastructure.feedback import ISSUES_URL, SECURITY_REPORT_URL, feedback_url
from flow.infrastructure.sessions import import_cookies, remove_cookies, session_status
from flow.infrastructure.security import harden_private_files, security_status
from flow.infrastructure.settings import save_settings
from flow.infrastructure.uninstall import uninstall
from flow.presentation.theme import *


def show_sessions(cli: Any) -> None:
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
            raw_path = cli.read_input("Ruta del archivo cookies.txt › ").strip().strip("\"'")
            try:
                imported = import_cookies(Path(raw_path))
                print(f"{GREEN}✓ {imported.cookies} cookies guardadas de forma privada.{RESET}")
            except ValueError as exc:
                print(f"{RED}{exc}{RESET}")
            cli.pause()
        elif choice == "2":
            confirm = cli.prompt_choice("¿Eliminar cookies? [1] Sí  [2] No", {"1", "2"})
            if confirm == "1":
                remove_cookies()
                print(f"{GREEN}Sesión eliminada.{RESET}")
                cli.pause()


def show_supported_platforms(cli: Any) -> None:
    cli.logo("PLATAFORMAS COMPATIBLES")
    print(
        f"{GREEN}✓ {len(supported_platforms())} plataformas reconocidas{RESET}\n"
        f"{GRAY}El contenido privado puede requerir cookies; la disponibilidad "
        f"también depende del sitio y la región.{RESET}\n"
    )
    for group, names in PLATFORM_GROUPS:
        print(f"{MAGENTA}{BOLD}{group.upper()}{RESET}")
        for name in names:
            print(f"  {CYAN}•{RESET} {name}")
        print()
    cli.pause()


def show_feedback(cli: Any) -> None:
    while True:
        cli.logo("SUGERENCIAS Y REPORTES")
        print(
            f"{GRAY}GitHub abrirá un formulario para que lo revises antes de enviarlo. "
            f"FlowMobile no publica nada automáticamente.{RESET}\n"
        )
        cli.menu_item("1", "Enviar una sugerencia", "funciones, plataformas o interfaz")
        cli.menu_item("2", "Reportar un error", "incluye versión y dispositivo, sin datos privados")
        cli.menu_item("3", "Problema de seguridad", "reporte privado para el responsable")
        cli.menu_item("0", "Volver")
        choice = cli.prompt_choice("Selecciona", {"0", "1", "2", "3"})
        if choice == "0":
            return
        target = {
            "1": feedback_url("suggestion"),
            "2": feedback_url("bug"),
            "3": SECURITY_REPORT_URL,
        }[choice]
        if open_url(target):
            print(
                f"\n{GREEN}✓ GitHub abierto.{RESET} "
                f"{GRAY}Revisa el formulario y pulsa Enviar cuando esté listo.{RESET}"
            )
        else:
            print(f"\n{YELLOW}No se pudo abrir GitHub desde la terminal.{RESET}")
            print(f"{CYAN}{ISSUES_URL}{RESET}")
        cli.pause()


def show_diagnostics_menu(cli: Any) -> None:
    while True:
        cli.logo("DIAGNÓSTICO Y PRUEBAS")
        print(f"{GRAY}Revisa el funcionamiento sin mezclarlo con los ajustes.{RESET}\n")
        cli.menu_item("1", "Informe de diagnóstico", "privado y preparado para compartir")
        cli.menu_item("2", "Pruebas reales", "descargan archivos y consumen datos")
        cli.menu_item("0", "Volver")
        choice = cli.prompt_choice("Selecciona", {"0", "1", "2"})
        if choice == "0":
            return
        if choice == "1":
            cli.show_diagnostic()
        else:
            cli.show_real_tests()


def show_security(cli: Any) -> None:
    cli.logo("CENTRO DE SEGURIDAD")
    harden_private_files()
    status = security_status()
    source = (
        f"{GREEN}✓ Repositorio oficial{RESET}"
        if status.official_source
        else f"{YELLOW}⚠ Origen no oficial configurado{RESET}"
    )
    integrity = (
        f"{GREEN}✓ {status.integrity_detail}{RESET}"
        if status.integrity_ok
        else f"{RED}✕ {status.integrity_detail}{RESET}"
    )
    if status.cookies_private is None:
        cookies = f"{GRAY}• Cookies privadas no configuradas{RESET}"
    elif status.cookies_private:
        cookies = f"{GREEN}✓ Cookies protegidas (solo usuario){RESET}"
    else:
        cookies = f"{YELLOW}⚠ Revisa los permisos de cookies{RESET}"
    print(f"{source}\n{integrity}\n{cookies}")
    print(
        f"\n{GRAY}Versión {status.version}. Las actualizaciones estables se "
        f"comprueban con SHA-256 antes de ejecutarse.{RESET}"
    )
    cli.pause()


def show_tools(cli: Any) -> None:
    while True:
        with cli.buffered_screen():
            cli.logo("AYUDA Y HERRAMIENTAS")
            cli.section("AYUDA")
            cli.menu_item("1", "Sugerencias y reportes", "buzón público y seguridad privada")
            cli.menu_item("2", "Plataformas compatibles", "35 sitios reconocidos")
            cli.section("PRIVACIDAD Y PREFERENCIAS")
            cli.menu_item("3", "Centro de seguridad", "origen, integridad y privacidad")
            cli.menu_item("4", "Cookies y sesiones")
            cli.menu_item("5", "Ajustes")
            cli.section("MANTENIMIENTO")
            cli.menu_item("6", "Sistema y reparación", "estado, dependencias y temporales")
            cli.menu_item("7", "Diagnóstico y pruebas", "informe privado y pruebas reales")
            cli.menu_item("8", "Desinstalar FlowMobile")
            cli.menu_item("0", "Volver")
        choice = cli.prompt_choice(
            "Selecciona",
            {"0", "1", "2", "3", "4", "5", "6", "7", "8"},
        )
        if choice == "0":
            return
        actions = {
            "1": lambda: show_feedback(cli),
            "2": lambda: show_supported_platforms(cli),
            "3": lambda: show_security(cli),
            "4": cli.show_sessions,
            "5": cli.show_settings,
            "6": cli.show_system_repair,
            "7": lambda: show_diagnostics_menu(cli),
            "8": cli.show_uninstall,
        }
        actions[choice]()


def show_diagnostic(cli: Any) -> None:
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


def show_uninstall(cli: Any) -> None:
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


def show_settings(cli: Any) -> None:
    kind_labels = {"ask": "Preguntar siempre", "video": "Video", "audio": "Solo audio"}
    audio_labels = {"auto": "Automático", "m4a": "M4A", "mp3": "MP3"}
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
            print("\n[1] Preguntar siempre  [2] Video  [3] Solo audio")
            value = cli.prompt_choice("Formato", {"1", "2", "3"})
            cli.settings.default_kind = {"1": "ask", "2": "video", "3": "audio"}[value]
        elif choice == "2":
            print("\n[1] Mejor  [2] 2160p  [3] 1440p  [4] 1080p")
            print("[5] 720p   [6] 480p   [7] 360p")
            value = cli.prompt_choice("Calidad máxima", {str(i) for i in range(1, 8)})
            cli.settings.video_quality = {
                "1": "best", "2": "2160", "3": "1440", "4": "1080",
                "5": "720", "6": "480", "7": "360",
            }[value]
        elif choice == "3":
            print("\n[1] Automático recomendado  [2] M4A  [3] MP3")
            value = cli.prompt_choice("Formato de audio", {"1", "2", "3"})
            cli.settings.audio_format = {"1": "auto", "2": "m4a", "3": "mp3"}[value]
        elif choice == "4":
            print("\n[1] Comprobar en cada inicio  [2] Desactivar")
            value = cli.prompt_choice("Actualizaciones", {"1", "2"})
            cli.settings.auto_updates = value == "1"
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
