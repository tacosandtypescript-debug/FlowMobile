from pathlib import Path
import unittest

from scripts.release_notes import notes_for_version


ROOT = Path(__file__).resolve().parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_release_workflow_publishes_checksums(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("SHA256SUMS", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn('tags:', workflow)

    def test_current_version_has_release_notes(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertGreater(len(notes_for_version(changelog, version)), 2)

    def test_public_project_documents_exist(self):
        for name in ("LICENSE", "SECURITY.md", "CONTRIBUTING.md"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_windows_release_check_prefers_actions_python(self):
        script = (ROOT / "scripts" / "check-release.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("$env:pythonLocation", script)
        self.assertLess(
            script.index("$env:pythonLocation"), script.index("Get-Command py")
        )


if __name__ == "__main__":
    unittest.main()
