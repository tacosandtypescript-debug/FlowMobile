import json
from pathlib import Path
import tempfile
import unittest

from flow.infrastructure.diagnostics import save_diagnostic_report


class DiagnosticTests(unittest.TestCase):
    def test_report_excludes_urls_cookies_and_private_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            target = save_diagnostic_report(Path(folder))
            content = target.read_text(encoding="utf-8")
            data = json.loads(content)

        self.assertEqual(data["application"], "FlowMobile")
        self.assertNotIn("http://", content)
        self.assertNotIn("https://", content)
        self.assertNotIn("cookiefile", content.casefold())
        self.assertNotIn(str(Path.home()), content)


if __name__ == "__main__":
    unittest.main()
