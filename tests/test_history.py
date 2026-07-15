import unittest

from flow.infrastructure.history import search_history


class HistorySearchTests(unittest.TestCase):
    def setUp(self):
        self.history = [
            {"title": "Viaje a Madrid", "platform": "YouTube", "type": "video", "resolution": "1080p"},
            {"title": "Canción", "platform": "TikTok", "type": "audio", "resolution": "M4A"},
        ]

    def test_search_is_case_insensitive_and_accepts_multiple_words(self):
        self.assertEqual(search_history("YOUTUBE 1080", self.history), [self.history[0]])

    def test_empty_search_returns_all_entries(self):
        self.assertEqual(search_history("  ", self.history), self.history)


if __name__ == "__main__":
    unittest.main()
