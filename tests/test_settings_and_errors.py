import unittest

from flow.domain.errors import friendly_error
from flow.infrastructure.settings import AppSettings


class SettingsTests(unittest.TestCase):
    def test_invalid_values_return_to_safe_defaults(self):
        settings = AppSettings("unknown", "9999", "wav").normalize()
        self.assertEqual(settings.default_kind, "ask")
        self.assertEqual(settings.video_quality, "best")
        self.assertEqual(settings.audio_format, "auto")

    def test_invalid_boolean_does_not_disable_updates(self):
        settings = AppSettings(auto_updates="false").normalize()  # type: ignore[arg-type]
        self.assertTrue(settings.auto_updates)

    def test_invalid_cached_update_values_are_safely_cleared(self):
        settings = AppSettings(
            last_flow_version=7,  # type: ignore[arg-type]
            last_flow_release_notes="texto",  # type: ignore[arg-type]
        ).normalize()
        self.assertIsNone(settings.last_flow_version)
        self.assertEqual(settings.last_flow_release_notes, ())

    def test_invalid_announced_version_is_safely_cleared(self):
        settings = AppSettings(last_announced_flow_version=8).normalize()  # type: ignore[arg-type]
        self.assertIsNone(settings.last_announced_flow_version)

    def test_invalid_interface_preferences_use_private_safe_defaults(self):
        settings = AppSettings(
            clipboard_detection="no",  # type: ignore[arg-type]
            colors="no",  # type: ignore[arg-type]
            interface_mode="animated",
        ).normalize()
        self.assertTrue(settings.clipboard_detection)
        self.assertTrue(settings.colors)
        self.assertEqual(settings.interface_mode, "compact")

class FriendlyErrorTests(unittest.TestCase):
    def test_tiktok_ip_block_recommends_changing_network(self):
        title, hint = friendly_error(
            "https://www.tiktok.com/video/1",
            RuntimeError("Your IP address is blocked from accessing this post"),
        )
        self.assertIn("TikTok", title)
        self.assertIn("IP", title)
        self.assertIn("Wi-Fi", hint)
        self.assertIn("datos móviles", hint)

    def test_rate_limit_mentions_platform(self):
        title, hint = friendly_error(
            "https://www.tiktok.com/video/1",
            RuntimeError("HTTP Error 429: Too Many Requests"),
        )
        self.assertIn("TikTok", title)
        self.assertIn("minutos", hint)

    def test_private_content_has_actionable_hint(self):
        title, hint = friendly_error(
            "https://www.instagram.com/reel/1",
            RuntimeError("This video is private"),
        )
        self.assertIn("Instagram", title)
        self.assertIn("público", hint)


if __name__ == "__main__":
    unittest.main()
