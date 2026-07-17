import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from flow.domain.urls import extract_web_urls, is_web_url
from flow.infrastructure.clipboard import clipboard_urls
from flow.infrastructure.platform import PlatformInfo


class ClipboardTests(unittest.TestCase):
    def test_extracts_only_unique_web_urls(self):
        text = "texto https://youtu.be/abc, clave=123 https://youtu.be/abc ftp://host/file"
        self.assertEqual(extract_web_urls(text), ["https://youtu.be/abc"])
        self.assertFalse(is_web_url("javascript:alert(1)"))

    def test_ashell_uses_pbpaste(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, "https://tiktok.com/video/1", "")

        platform = PlatformInfo("ashell", "a-Shell", "iOS")
        self.assertEqual(clipboard_urls(platform, runner), ["https://tiktok.com/video/1"])
        self.assertEqual(calls[0][0], ["pbpaste"])
        self.assertEqual(calls[0][1]["timeout"], 2)

    def test_missing_clipboard_command_is_silent(self):
        def runner(command, **kwargs):
            raise FileNotFoundError(command[0])

        platform = PlatformInfo("termux", "Termux", "Android")
        self.assertEqual(clipboard_urls(platform, runner), [])

    def test_windows_uses_powershell_clipboard(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout="https://youtube.com/watch?v=1"))
        platform = PlatformInfo("windows", "Terminal", "Windows")
        self.assertEqual(clipboard_urls(platform, runner), ["https://youtube.com/watch?v=1"])
        self.assertEqual(runner.call_args.args[0][:2], ["powershell", "-NoProfile"])

    def test_linux_falls_back_between_clipboard_tools(self):
        runner = Mock(side_effect=[OSError("missing"), SimpleNamespace(returncode=0, stdout="https://x.com/a/status/1")])
        platform = PlatformInfo("linux", "Terminal", "Linux")
        self.assertEqual(clipboard_urls(platform, runner), ["https://x.com/a/status/1"])
        self.assertEqual(runner.call_args_list[1].args[0][0], "xclip")


if __name__ == "__main__":
    unittest.main()
