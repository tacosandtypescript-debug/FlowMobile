from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flow.infrastructure import sessions


COOKIE_TEXT = """# Netscape HTTP Cookie File
.example.com\tTRUE\t/\tTRUE\t2147483647\tsession\tsecret
"""


class CookieSessionTests(unittest.TestCase):
    def test_imports_netscape_cookies_into_private_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "export.txt"
            target = root / "private" / "cookies.txt"
            target.parent.mkdir()
            source.write_text(COOKIE_TEXT, encoding="utf-8")
            with patch.object(sessions, "COOKIES_FILE", target):
                status = sessions.import_cookies(source)
            self.assertTrue(status.configured)
            self.assertEqual(status.cookies, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), COOKIE_TEXT)

    def test_rejects_files_that_are_not_cookie_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "passwords.txt"
            source.write_text("usuario:contraseña", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Netscape"):
                sessions.validate_cookie_file(source)

    def test_cookie_options_are_empty_when_no_session_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(sessions, "COOKIES_FILE", Path(folder) / "missing.txt"):
                self.assertEqual(sessions.cookie_options(), {})


if __name__ == "__main__":
    unittest.main()
