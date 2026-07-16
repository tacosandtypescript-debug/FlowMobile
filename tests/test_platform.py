import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from flow.infrastructure.platform import PlatformInfo, detect_platform, termux_shared_downloads


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


if __name__ == "__main__":
    unittest.main()
