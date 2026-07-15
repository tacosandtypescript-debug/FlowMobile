import subprocess
import unittest

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


if __name__ == "__main__":
    unittest.main()
