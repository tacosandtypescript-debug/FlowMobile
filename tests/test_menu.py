import unittest
import threading
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flow.presentation.cli import FlowCLI
from flow.infrastructure.settings import AppSettings
from flow.presentation.update_menu import record_update_check


class InteractiveMenuTests(unittest.TestCase):
    def test_pypi_version_is_not_offered_until_lockfile_verifies_it(self):
        cli = SimpleNamespace(
            flow_update_version=None,
            flow_release_notes=(),
            settings=AppSettings(),
            _tools_status=None,
        )
        check = SimpleNamespace(
            flow_latest="8.0.4",
            flow_ref="v8.0.4",
            release_notes=(),
            ytdlp_latest="9999.1.1",
            ytdlp_locked="2026.7.4",
            repository="owner/repository",
            ffmpeg_pending=False,
            error="",
        )
        with patch("flow.presentation.update_menu.tools_status", return_value=(True, True)):
            with patch("flow.presentation.update_menu.save_settings"):
                _, ytdlp_pending, _, _ = record_update_check(cli, check)
        self.assertFalse(ytdlp_pending)

    def test_runtime_state_is_initialized(self):
        with patch("flow.presentation.cli.MediaService"):
            settings = SimpleNamespace(
                last_flow_version=None,
                last_flow_release_notes=(),
            )
            with patch("flow.presentation.cli.load_settings", return_value=settings):
                cli = FlowCLI()
        self.assertIsInstance(cli._update_lock, type(threading.Lock()))
        self.assertIsNone(cli._tools_status)

    def test_cached_update_is_visible_before_background_check_finishes(self):
        settings = SimpleNamespace(
            last_flow_version="99.0.0",
            last_flow_release_notes=("Cambio importante",),
        )
        with patch("flow.presentation.cli.MediaService"):
            with patch("flow.presentation.cli.load_settings", return_value=settings):
                cli = FlowCLI()
        self.assertEqual(cli.flow_update_version, "99.0.0")
        self.assertEqual(cli.flow_release_notes, ("Cambio importante",))

    def test_late_background_update_prints_immediate_notice(self):
        cli = FlowCLI.__new__(FlowCLI)
        cli._announced_update_version = None
        cli._menu_ready = threading.Event()
        cli._menu_ready.set()
        output = StringIO()
        with patch.object(__import__("sys"), "__stdout__", output):
            cli.announce_background_update("99.0.0")
        self.assertIn("99.0.0 disponible", output.getvalue())
        self.assertIn("[5] Actualizaciones", output.getvalue())

    def test_termux_without_public_storage_blocks_downloads(self):
        cli = FlowCLI.__new__(FlowCLI)
        platform = SimpleNamespace(is_termux=True)
        with patch("flow.presentation.cli.PLATFORM", platform):
            with patch("flow.presentation.cli.TERMUX_DOWNLOADS_PUBLIC", False):
                with patch.object(cli, "logo") as logo:
                    with patch.object(cli, "pause") as pause:
                        with patch("sys.stdout", StringIO()):
                            self.assertFalse(cli.ensure_download_storage())
        logo.assert_called_once_with("PERMISO DE ALMACENAMIENTO")
        pause.assert_called_once()

    def test_ios_screen_is_written_as_one_terminal_frame(self):
        class CountingOutput(StringIO):
            def __init__(self):
                super().__init__()
                self.writes = 0

            def write(self, value):
                self.writes += 1
                return super().write(value)

        cli = FlowCLI.__new__(FlowCLI)
        output = CountingOutput()
        with patch("sys.stdout", output):
            with cli.buffered_screen():
                print("línea 1")
                print("línea 2")
        self.assertEqual(output.writes, 1)
        self.assertEqual(output.getvalue(), "línea 1\nlínea 2\n")

    def test_first_logo_does_not_wait_for_ffmpeg_processes(self):
        cli = FlowCLI.__new__(FlowCLI)
        cli._tools_status = None
        with patch("flow.presentation.cli.tools_status") as status:
            with patch("sys.stdout", StringIO()):
                cli.logo("MENÚ")
        status.assert_not_called()

    def test_update_check_starts_in_background_without_blocking_menu(self):
        cli = FlowCLI.__new__(FlowCLI)
        cli.settings = SimpleNamespace(
            auto_updates=True,
            last_update_check=None,
            last_update_ok=None,
            last_announced_flow_version=None,
        )
        cli.update_check_running = False
        cli._update_lock = threading.Lock()
        cli.flow_update_version = None
        cli.flow_release_notes = ()
        check = SimpleNamespace(
            flow_latest="99.0.0",
            ytdlp_latest="9999.1.1",
            ytdlp_locked="2026.7.4",
            repository="owner/repository",
            release_notes=(),
            ffmpeg_pending=False,
            error="",
        )

        cli.announce_background_update = Mock()
        with patch("flow.presentation.update_menu.check_available_updates", return_value=check):
            with patch("flow.presentation.update_menu.tools_status", return_value=(True, True)):
                with patch("flow.presentation.update_menu.save_settings"):
                    with patch("flow.presentation.update_menu.threading.Thread") as thread:
                        thread.return_value.start.side_effect = (
                            lambda: thread.call_args.kwargs["target"]()
                        )
                        cli.start_background_update_check()

        self.assertTrue(thread.call_args.kwargs["daemon"])
        self.assertFalse(cli.update_check_running)
        cli.announce_background_update.assert_called_once_with("99.0.0")
        self.assertEqual(cli.settings.last_announced_flow_version, "99.0.0")

    def test_cached_update_is_announced_if_notice_was_never_shown(self):
        settings = SimpleNamespace(
            last_flow_version="99.0.0",
            last_flow_release_notes=("Cambio",),
            last_announced_flow_version=None,
        )
        with patch("flow.presentation.cli.MediaService"):
            with patch("flow.presentation.cli.load_settings", return_value=settings):
                cli = FlowCLI()
        self.assertEqual(cli.flow_update_version, "99.0.0")
        self.assertIsNone(cli._announced_update_version)

    def test_closed_input_exits_without_traceback(self):
        cli = FlowCLI.__new__(FlowCLI)
        with patch("builtins.input", side_effect=EOFError):
            with self.assertRaises(SystemExit) as exit_context:
                cli.read_input("Selecciona › ")
        self.assertEqual(exit_context.exception.code, 0)

    def test_clipboard_url_is_used_when_enter_confirms(self):
        cli = FlowCLI.__new__(FlowCLI)
        cli.settings = SimpleNamespace(clipboard_detection=True)
        with patch(
            "flow.presentation.cli.clipboard_urls",
            return_value=["https://www.tiktok.com/video/123?private=value"],
        ):
            with patch.object(cli, "read_input", return_value="") as read:
                selected = cli.prompt_url()

        self.assertEqual(selected, "https://www.tiktok.com/video/123?private=value")
        self.assertNotIn("private=value", read.call_args.args[0])

    def test_accessible_mode_does_not_clear_terminal(self):
        cli = FlowCLI.__new__(FlowCLI)
        cli.settings = SimpleNamespace(interface_mode="accessible")
        output = StringIO()
        with patch("sys.stdout", output):
            cli.clear()
        self.assertNotIn("\033[2J", output.getvalue())

    def test_short_quality_list_is_preserved(self):
        values = [1080, 720, 480]
        self.assertEqual(FlowCLI.featured_resolutions(values), values)

    def test_long_quality_list_keeps_best_and_worst(self):
        values = [4320, 2160, 1440, 1080, 960, 720, 480, 360, 240, 144]
        featured = FlowCLI.featured_resolutions(values)

        self.assertEqual(featured[0], 4320)
        self.assertEqual(featured[-1], 144)
        self.assertLessEqual(len(featured), 8)
        self.assertEqual(featured, sorted(set(featured), reverse=True))


if __name__ == "__main__":
    unittest.main()
