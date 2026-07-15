import unittest

from flow.infrastructure.platform import detect_platform


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


if __name__ == "__main__":
    unittest.main()
