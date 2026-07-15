import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from install_ios import (
    _clean_installations,
    _configure_profile,
    _restore_preserved,
)


ROOT = Path(__file__).resolve().parents[1]


class InstallerCompatibilityTests(unittest.TestCase):
    def test_bootstrap_and_launcher_do_not_require_grep(self):
        for relative in ("install.sh", "scripts/flow"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("| grep", content)

    def test_ios_installer_explains_python_requirement(self):
        content = (ROOT / "install-ios.sh").read_text(encoding="utf-8")
        self.assertIn("a-Shell completa", content)
        self.assertIn("python3 python", content)

    def test_ashell_uses_a_python_installer_instead_of_dash(self):
        content = (ROOT / "install_ios.py").read_text(encoding="utf-8")
        self.assertIn("def install(", content)
        self.assertNotIn("subprocess", content)
        bootstrap = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("bootstrap_ios.py | python3", bootstrap)
        self.assertNotIn("&& cd", bootstrap)
        self.assertIn("abre una nueva", bootstrap)

    def test_ios_bootstrap_requests_latest_installer_from_api(self):
        content = (ROOT / "bootstrap_ios.py").read_text(encoding="utf-8")
        self.assertIn("api.github.com/repos", content)
        self.assertIn("application/vnd.github.raw+json", content)
        self.assertIn('"Cache-Control": "no-cache"', content)

    def test_ashell_launcher_is_python(self):
        first_line = (ROOT / "scripts" / "flow_ios.py").read_text(
            encoding="utf-8"
        ).splitlines()[0]
        self.assertEqual(first_line, "#!/usr/bin/env python3")
        installer = (ROOT / "install_ios.py").read_text(encoding="utf-8")
        self.assertIn('launcher = bin_directory / "flow.py"', installer)
        self.assertIn('(bin_directory / "flow").unlink', installer)

    def test_ios_installer_replaces_legacy_flow_aliases(self):
        content = (ROOT / "install_ios.py").read_text(encoding="utf-8")
        self.assertIn("def _configure_profile(", content)
        self.assertIn('alias flow=\'python3', content)
        self.assertIn('r"^\\s*alias\\s+flow\\s*="', content)

    def test_profile_migration_points_to_flowmobile(self):
        with TemporaryDirectory() as temporary:
            documents = Path(temporary)
            profile = documents / ".profile"
            profile.write_text(
                "alias flow='python3 /old/FlowApp/main.py'\n"
                "alias keep='echo intacto'\n",
                encoding="utf-8",
            )
            _configure_profile(documents, documents / "FlowMobile")
            migrated = profile.read_text(encoding="utf-8")

        self.assertNotIn("FlowApp/main.py", migrated)
        self.assertIn("FlowMobile/main.py", migrated)
        self.assertIn("alias keep='echo intacto'", migrated)

    def test_clean_install_merges_data_and_removes_legacy_code(self):
        with TemporaryDirectory() as temporary:
            documents = Path(temporary)
            current = documents / "FlowMobile"
            legacy = documents / "FlowApp"
            (current / "Downloads").mkdir(parents=True)
            (legacy / "Downloads").mkdir(parents=True)
            (current / "Downloads" / "actual.txt").write_text("actual")
            (legacy / "Downloads" / "anterior.txt").write_text("anterior")
            (legacy / "main.py").write_text("código viejo")
            preserved = documents / "temporary" / "preserved"

            _clean_installations([current, legacy], preserved)
            destination = documents / "InstalledFlowMobile"
            _restore_preserved(preserved, destination)

            self.assertFalse(current.exists())
            self.assertFalse(legacy.exists())
            self.assertTrue((destination / "Downloads" / "actual.txt").is_file())
            self.assertTrue((destination / "Downloads" / "anterior.txt").is_file())

    def test_ios_installer_restores_data_saved_by_uninstaller(self):
        with TemporaryDirectory() as temporary:
            documents = Path(temporary)
            saved = documents / ".flowmobile-data"
            (saved / "Downloads").mkdir(parents=True)
            (saved / ".flowmobile").mkdir()
            (saved / "Downloads" / "video.mp4").write_bytes(b"video")
            (saved / ".flowmobile" / "settings.json").write_text("{}")
            preserved = documents / "temporary" / "preserved"

            _clean_installations([saved], preserved)
            destination = documents / "FlowMobile"
            _restore_preserved(preserved, destination)

            self.assertFalse(saved.exists())
            self.assertTrue((destination / "Downloads" / "video.mp4").is_file())
            self.assertTrue((destination / ".flowmobile" / "settings.json").is_file())


if __name__ == "__main__":
    unittest.main()
