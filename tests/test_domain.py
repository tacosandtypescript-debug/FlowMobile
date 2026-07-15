import unittest

from flow.domain.formatting import format_bytes, format_time
from flow.domain.sites import platform_name


class FormattingTests(unittest.TestCase):
    def test_time_under_one_hour(self):
        self.assertEqual(format_time(65), "01:05")

    def test_time_over_one_hour(self):
        self.assertEqual(format_time(3665), "01:01:05")

    def test_unknown_values(self):
        self.assertEqual(format_time(None), "--:--")
        self.assertEqual(format_bytes(None), "—")


class PlatformTests(unittest.TestCase):
    def test_known_subdomain(self):
        self.assertEqual(platform_name("https://m.youtube.com/watch?v=1"), "YouTube")

    def test_domain_substring_is_not_a_match(self):
        self.assertEqual(platform_name("https://notx.com/video"), "Sitio web")


if __name__ == "__main__":
    unittest.main()
