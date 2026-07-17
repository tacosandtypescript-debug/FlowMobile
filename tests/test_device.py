import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flow.infrastructure import device


class DeviceIntegrationTests(unittest.TestCase):
    def test_windows_share_opens_explorer_at_file(self):
        platform = SimpleNamespace(is_termux=False, is_windows=True, is_linux=False)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device, "_run", return_value=True) as run:
                self.assertTrue(device.open_share(Path("C:/Media/video.mp4")))
        self.assertEqual(run.call_args.args[0][0:2], ["explorer.exe", "/select,"])

    def test_linux_share_opens_parent_directory(self):
        platform = SimpleNamespace(is_termux=False, is_windows=False, is_linux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device, "_run", return_value=True) as run:
                self.assertTrue(device.open_share(Path("/home/ana/Downloads/video.mp4")))
        command = run.call_args.args[0]
        self.assertEqual(command[0], "xdg-open")
        self.assertTrue(command[1].replace("\\", "/").endswith("/home/ana/Downloads"))

    def test_termux_share_uses_android_send_action(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.shutil, "which", return_value=None):
                with patch.object(device.subprocess, "run", return_value=completed) as run:
                    self.assertTrue(device.open_share(Path("/tmp/audio.m4a")))
        self.assertEqual(
            run.call_args.args[0],
            [
                "termux-open", "--send", "--chooser", "--content-type",
                "audio/mp4", "/tmp/audio.m4a",
            ],
        )

    def test_termux_share_falls_back_to_optional_api_command(self):
        failed = SimpleNamespace(returncode=1)
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device, "scan_media", return_value=False):
                with patch.object(device.shutil, "which", return_value="termux-share"):
                    with patch.object(
                        device.subprocess, "run", side_effect=[failed, completed]
                    ) as run:
                        self.assertTrue(device.open_share(Path("/tmp/video.mp4")))
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["termux-share", "-a", "send", "-c", "video/mp4", "/tmp/video.mp4"],
        )

    def test_ashell_share_uses_open(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=False)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.subprocess, "run", return_value=completed) as run:
                self.assertTrue(device.open_share(Path("/tmp/video.mp4")))
        self.assertEqual(run.call_args.args[0], ["open", "/tmp/video.mp4"])

    def test_ashell_opens_feedback_in_browser(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=False)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.subprocess, "run", return_value=completed) as run:
                self.assertTrue(device.open_url("https://github.com/example/issues/new"))
        self.assertEqual(
            run.call_args.args[0],
            ["open", "https://github.com/example/issues/new"],
        )

    def test_termux_opens_feedback_with_native_url_command(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.shutil, "which", return_value="termux-open-url"):
                with patch.object(device.subprocess, "run", return_value=completed) as run:
                    self.assertTrue(device.open_url("https://github.com/example/issues/new"))
        self.assertEqual(
            run.call_args.args[0],
            ["termux-open-url", "https://github.com/example/issues/new"],
        )

    def test_open_url_rejects_non_https_values(self):
        with patch.object(device, "_run") as run:
            self.assertFalse(device.open_url("file:///private/cookies.txt"))
        run.assert_not_called()

    def test_termux_completion_uses_native_notification_when_available(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.shutil, "which", return_value=None):
                with patch.object(device.subprocess, "run", return_value=completed) as run:
                    with patch("builtins.print"):
                        self.assertTrue(device.notify_complete(Path("/tmp/audio.m4a")))
        self.assertEqual(run.call_args.args[0][0], "termux-notification")

    def test_termux_scans_media_when_optional_api_is_available(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.shutil, "which", return_value="termux-media-scan"):
                with patch.object(device.subprocess, "run", return_value=completed) as run:
                    self.assertTrue(device.scan_media(Path("/sdcard/Download/FlowMobile/video.mp4")))
        self.assertEqual(
            run.call_args.args[0],
            ["termux-media-scan", "/sdcard/Download/FlowMobile/video.mp4"],
        )

    def test_termux_scans_media_with_android_when_optional_api_is_missing(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.shutil, "which", return_value=None):
                with patch.dict(device.os.environ, {"TERMUX__USER_ID": "0"}, clear=False):
                    with patch.object(device.subprocess, "run", return_value=completed) as run:
                        self.assertTrue(device.scan_media(Path("/sdcard/Movies/FlowMobile/video.mp4")))
        self.assertEqual(
            run.call_args.args[0],
            [
                "/system/bin/am", "broadcast", "--user", "0",
                "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                "-d", "file:///sdcard/Movies/FlowMobile/video.mp4",
            ],
        )

    def test_ashell_completion_uses_terminal_bell_without_external_command(self):
        platform = SimpleNamespace(is_termux=False)
        with patch.object(device, "PLATFORM", platform):
            with patch("builtins.print") as output:
                self.assertTrue(device.notify_complete(Path("/tmp/video.mp4")))
        output.assert_called_once_with("\a", end="", flush=True)


if __name__ == "__main__":
    unittest.main()
