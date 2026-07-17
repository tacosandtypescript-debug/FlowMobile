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
        for name in (
            "LICENSE",
            "NOTICE",
            "LICENSING.md",
            "TRADEMARKS.md",
            "SECURITY.md",
            "CONTRIBUTING.md",
        ):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_current_license_is_polyform_strict(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(license_text.startswith("# PolyForm Strict License 1.0.0"))
        self.assertIn("other than distributing the software", license_text)

    def test_license_transition_and_trademark_are_documented(self):
        licensing = (ROOT / "LICENSING.md").read_text(encoding="utf-8")
        trademarks = (ROOT / "TRADEMARKS.md").read_text(encoding="utf-8")
        self.assertIn("7.6.0 a 7.6.13", licensing)
        self.assertIn("7.6.14 y posteriores", licensing)
        self.assertIn("tacosandtypescript-debug", trademarks)

    def test_windows_release_check_prefers_actions_python(self):
        script = (ROOT / "scripts" / "check-release.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("$env:pythonLocation", script)
        self.assertLess(
            script.index("$env:pythonLocation"), script.index("Get-Command py")
        )

    def test_local_codex_attachments_are_ignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.codex-remote-attachments/", gitignore)

    def test_publishing_uses_a_private_github_email(self):
        publishing = (ROOT / "PUBLISHING.md").read_text(encoding="utf-8")
        self.assertIn("@users.noreply.github.com", publishing)

    def test_mobile_copy_buttons_use_official_install_commands(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ios = (ROOT / "docs" / "COPIAR_IOS.md").read_text(encoding="utf-8")
        android = (ROOT / "docs" / "COPIAR_ANDROID.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("github.io/FlowMobile/?device=apple", readme)
        self.assertIn("github.io/FlowMobile/?device=android", readme)
        self.assertIn("docs/COPIAR_IOS.md", readme)
        self.assertIn("docs/COPIAR_ANDROID.md", readme)
        self.assertIn("bootstrap_ios.py | python3 -", ios)
        self.assertIn("install.sh | sh -s --", android)

    def test_mobile_copy_site_has_clipboard_and_legacy_support(self):
        site = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("navigator.clipboard.writeText(command)", site)
        self.assertIn("document.execCommand('copy')", site)
        self.assertIn("bootstrap_ios.py | python3 -", site)
        self.assertIn("install.sh | sh -s --", site)
        self.assertIn("actions/deploy-pages@v4", workflow)

    def test_readme_stays_short_and_links_to_detailed_guide(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(readme.splitlines()), 75)
        self.assertIn("docs/GUIA_COMPLETA.md", readme)
        self.assertIn("github.io/FlowMobile/?device=apple", readme)
        self.assertIn("github.io/FlowMobile/?device=android", readme)


if __name__ == "__main__":
    unittest.main()
