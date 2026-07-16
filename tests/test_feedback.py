import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from flow.infrastructure import feedback


class FeedbackTests(unittest.TestCase):
    def test_bug_report_contains_only_safe_automatic_context(self):
        platform = SimpleNamespace(mobile_os="Android", name="Termux")
        with patch.object(feedback, "PLATFORM", platform):
            url = feedback.feedback_url("bug")
        parsed = urlparse(url)
        values = parse_qs(parsed.query)
        body = values["body"][0]
        self.assertEqual(parsed.hostname, "github.com")
        self.assertEqual(values["labels"], ["bug"])
        self.assertIn("FlowMobile:", body)
        self.assertIn("Android / Termux", body)
        self.assertNotIn("cookiefile", body.casefold())
        self.assertNotIn("http://", body.casefold())

    def test_suggestion_uses_enhancement_category(self):
        values = parse_qs(urlparse(feedback.feedback_url("suggestion")).query)
        self.assertEqual(values["labels"], ["enhancement"])
        self.assertTrue(values["title"][0].startswith("[Sugerencia]"))

    def test_unknown_feedback_type_is_rejected(self):
        with self.assertRaises(ValueError):
            feedback.feedback_url("private-data")


if __name__ == "__main__":
    unittest.main()
