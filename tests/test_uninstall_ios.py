from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from uninstall_ios import main, purge_flowmobile


class IOSStandaloneUninstallTests(unittest.TestCase):
    def test_confirmation_is_required(self):
        self.assertEqual(main([]), 2)

    def test_cleaner_removes_every_flowmobile_path_and_preserves_other_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            documents = root / "Documents"
            app = documents / "FlowMobile"
            legacy_app = documents / "FlowApp"
            (app / "flow").mkdir(parents=True)
            legacy_app.mkdir()
            (documents / ".flowmobile-data").mkdir()
            (documents / ".flowmobile-rollback").mkdir()
            (documents / ".flowmobile").mkdir()
            (documents / "Downloads" / "FlowMobile").mkdir(parents=True)
            (documents / "Downloads" / "history.json").write_text("[]", encoding="utf-8")
            (documents / "bin").mkdir()
            (documents / "bin" / "flow.py").write_text("FlowMobile", encoding="utf-8")
            (documents / "bin" / "keep.py").write_text("keep", encoding="utf-8")
            (app / "main.py").write_text("print('flow')", encoding="utf-8")
            profile = documents / ".profile"
            profile.write_text(
                "export KEEP=1\n"
                "# >>> FlowMobile launcher >>>\n"
                "alias flow='python3 FlowMobile/main.py'\n"
                "# <<< FlowMobile launcher <<<\n",
                encoding="utf-8",
            )

            with patch("uninstall_ios._remove_current_alias"):
                result = purge_flowmobile(home=root)

            self.assertTrue(result.ok, result.errors)
            for path in (
                app,
                legacy_app,
                documents / ".flowmobile-data",
                documents / ".flowmobile-rollback",
                documents / ".flowmobile",
                documents / "Downloads" / "FlowMobile",
                documents / "Downloads" / "history.json",
                documents / "bin" / "flow.py",
            ):
                self.assertFalse(path.exists(), path)
            self.assertEqual(profile.read_text(encoding="utf-8"), "export KEEP=1\n")
            self.assertTrue((documents / "bin" / "keep.py").is_file())

    def test_custom_application_must_be_inside_documents_and_is_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            documents = root / "Documents"
            custom_app = documents / "FlowMobile-prueba"
            custom_app.mkdir(parents=True)

            with patch("uninstall_ios._remove_current_alias"):
                result = purge_flowmobile(home=root, app_directory=custom_app)

            self.assertTrue(result.ok, result.errors)
            self.assertFalse(custom_app.exists())

            outside = root / "fuera"
            outside.mkdir()
            with self.assertRaises(ValueError):
                purge_flowmobile(home=root, app_directory=outside)
            self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()
