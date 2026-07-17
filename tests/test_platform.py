import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from flow.infrastructure.platform import (
    PlatformInfo,
    desktop_downloads_directory,
    detect_platform,
    termux_shared_directory,
    termux_shared_downloads,
)


class PlatformDetectionTests(unittest.TestCase):
    def test_termux_environment(self):
        platform = detect_platform({
            "TERMUX_VERSION": "0.118.3",
            "PREFIX": "/data/data/com.termux/files/usr",
        })
        self.assertTrue(platform.is_termux)
        self.assertEqual(platform.mobile_os, "Android")

    def test_ashell_environment(self):
        platform = detect_platform({"HOME": "/private/app/Documents"})
        self.assertTrue(platform.is_ashell)
        self.assertEqual(platform.mobile_os, "iOS")

    def test_windows_and_linux_are_detected_as_desktop(self):
        windows = detect_platform({"HOME": "C:/Users/Ana"}, system="Windows")
        linux = detect_platform({"HOME": "/home/ana"}, system="Linux")
        self.assertTrue(windows.is_windows)
        self.assertTrue(linux.is_linux)
        self.assertTrue(windows.is_desktop)
        self.assertEqual(windows.mobile_os, "Windows")
        self.assertEqual(linux.mobile_os, "Linux")

    def test_desktop_downloads_supports_xdg_and_override(self):
        linux = PlatformInfo("linux", "Terminal", "Linux")
        windows = PlatformInfo("windows", "Terminal", "Windows")
        home = Path("/home/ana")
        self.assertEqual(
            desktop_downloads_directory(linux, home, {"XDG_DOWNLOAD_DIR": "$HOME/Descargas"}),
            home / "Descargas",
        )
        self.assertEqual(
            desktop_downloads_directory(windows, Path("C:/Users/Ana"), {"FLOWMOBILE_DOWNLOADS": "D:/Media"}),
            Path("D:/Media"),
        )

    def test_termux_shared_downloads_requires_real_write_access(self):
        platform = PlatformInfo("termux", "Termux", "Android")
        with TemporaryDirectory() as temporary:
            home = Path(temporary)
            downloads = home / "storage" / "downloads"
            downloads.mkdir(parents=True)
            self.assertEqual(termux_shared_downloads(platform, home), downloads)
            self.assertFalse(any(downloads.iterdir()))

    def test_ashell_never_uses_android_shared_downloads(self):
        platform = PlatformInfo("ashell", "a-Shell", "iOS")
        with TemporaryDirectory() as temporary:
            self.assertIsNone(termux_shared_downloads(platform, Path(temporary)))

    def test_termux_uses_android_movies_for_gallery_videos(self):
        platform = PlatformInfo("termux", "Termux", "Android")
        with TemporaryDirectory() as temporary:
            home = Path(temporary)
            movies = home / "storage" / "movies"
            movies.mkdir(parents=True)
            self.assertEqual(termux_shared_directory("movies", platform, home), movies)


if __name__ == "__main__":
    unittest.main()
