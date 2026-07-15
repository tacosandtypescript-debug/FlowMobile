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

class FriendlyErrorTests(unittest.TestCase):
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
