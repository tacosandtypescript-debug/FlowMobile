import unittest
import threading
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from flow.presentation.cli import FlowCLI


class InteractiveMenuTests(unittest.TestCase):
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
        )
        cli.update_check_running = False
        cli._update_lock = threading.Lock()
        cli.flow_update_version = None
        cli.flow_release_notes = ()
        check = SimpleNamespace(
            flow_latest="7.4.1",
            ytdlp_latest="9999.1.1",
            repository="owner/repository",
            release_notes=(),
            ffmpeg_pending=False,
            error="",
        )

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
