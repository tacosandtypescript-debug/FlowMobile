from pathlib import Path
import tempfile
import unittest

from flow.infrastructure.platform import PlatformInfo
from flow.infrastructure.uninstall import remove_profile_launcher, uninstall


class UninstallTests(unittest.TestCase):
    def test_profile_cleanup_removes_only_flow_launcher(self):
        with tempfile.TemporaryDirectory() as folder:
            documents = Path(folder)
            profile = documents / ".profile"
            profile.write_text(
                "export KEEP=1\n"
                "# >>> FlowMobile launcher >>>\n"
                "alias flow='python3 FlowMobile/main.py'\n"
                "# <<< FlowMobile launcher <<<\n",
                encoding="utf-8",
            )
            self.assertTrue(remove_profile_launcher(documents))
            self.assertEqual(profile.read_text(encoding="utf-8"), "export KEEP=1\n")

    def test_normal_uninstall_preserves_personal_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            documents = root / "Documents"
            app = documents / "FlowMobile"
            (app / "flow").mkdir(parents=True)
            (app / "Downloads").mkdir()
            (app / ".flowmobile").mkdir()
            (documents / "bin").mkdir()
            (app / "main.py").write_text("print('flow')", encoding="utf-8")
            (app / "flow" / "module.py").write_text("", encoding="utf-8")
            (app / "Downloads" / "video.mp4").write_bytes(b"video")
            (app / ".flowmobile" / "settings.json").write_text("{}", encoding="utf-8")
            (documents / "bin" / "flow.py").write_text("FlowMobile", encoding="utf-8")
            platform = PlatformInfo("ashell", "a-Shell", "iOS")

            result = uninstall(False, app, app / "Downloads", platform, root)

            self.assertTrue(result.ok)
            self.assertFalse(app.exists())
            saved = documents / ".flowmobile-data"
            self.assertTrue(Path(result.preserved_at).samefile(saved))
            self.assertTrue((saved / "Downloads" / "video.mp4").exists())
            self.assertTrue((saved / ".flowmobile" / "settings.json").exists())
            self.assertFalse((documents / "bin" / "flow.py").exists())

    def test_complete_uninstall_removes_app_and_shared_downloads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            documents = root / "Documents"
            app = documents / "FlowMobile"
            shared = root / "shared" / "FlowMobile"
            saved = documents / ".flowmobile-data"
            (app / "flow").mkdir(parents=True)
            shared.mkdir(parents=True)
            saved.mkdir(parents=True)
            (documents / "bin").mkdir()
            (app / "main.py").write_text("print('flow')", encoding="utf-8")
            (shared / "audio.m4a").write_bytes(b"audio")
            (saved / "old.txt").write_text("old", encoding="utf-8")
            platform = PlatformInfo("ashell", "a-Shell", "iOS")

            result = uninstall(True, app, shared, platform, root)

            self.assertTrue(result.ok)
            self.assertFalse(app.exists())
            self.assertFalse(shared.exists())
            self.assertFalse(saved.exists())


if __name__ == "__main__":
    unittest.main()
