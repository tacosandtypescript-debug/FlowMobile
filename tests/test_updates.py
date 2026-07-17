import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flow.infrastructure.platform import PlatformInfo

from flow.infrastructure.updates import (
    check_available_updates,
    is_newer,
    release_notes_for_version,
    release_notes_from_body,
    update_ytdlp,
    update_flowmobile,
)


class UpdateTests(unittest.TestCase):
    def test_desktop_updates_use_the_platform_specific_verified_asset(self):
        cases = (
            (PlatformInfo("windows", "Terminal", "Windows"), "install-windows.ps1"),
            (PlatformInfo("linux", "Terminal", "Linux"), "install-linux.sh"),
        )
        for platform, filename in cases:
            verified = Mock(return_value=b"installer")
            completed = SimpleNamespace(returncode=0)
            with self.subTest(platform=platform.key):
                with patch("flow.infrastructure.updates.PLATFORM", platform):
                    with patch("flow.infrastructure.updates._verified_release_asset", verified):
                        with patch("flow.infrastructure.updates.subprocess.run", return_value=completed):
                            result = update_flowmobile("owner/repository", "v8.0.0")
            self.assertTrue(result.ok)
            self.assertEqual(verified.call_args.args[2], filename)

    def test_lightweight_check_can_skip_termux_package_catalog(self):
        platform = SimpleNamespace(is_termux=True)
        with patch("flow.infrastructure.updates.PLATFORM", platform):
            with patch("flow.infrastructure.updates.configured_repository", return_value=None):
                with patch(
                    "flow.infrastructure.updates._read_url",
                    return_value='{"info":{"version":"1"}}',
                ):
                    with patch("flow.infrastructure.updates.subprocess.run") as run:
                        result = check_available_updates(include_package_manager=False)
        self.assertEqual(result.ytdlp_latest, "1")
        run.assert_not_called()

    def test_semantic_and_date_versions_are_compared(self):
        self.assertTrue(is_newer("7.1.0", "7.0.0"))
        self.assertTrue(is_newer("2026.07.01", "2026.06.09"))
        self.assertFalse(is_newer("7.0.0", "7.0.0"))

    def test_successful_check_reports_ok(self):
        completed = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch("flow.infrastructure.updates.version", side_effect=["1", "1"]):
            with patch("flow.infrastructure.updates.subprocess.run", return_value=completed):
                result = update_ytdlp()
        self.assertTrue(result.ok)
        self.assertFalse(result.changed)

    def test_version_change_is_detected(self):
        completed = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch("flow.infrastructure.updates.version", side_effect=["1", "2"]):
            with patch("flow.infrastructure.updates.subprocess.run", return_value=completed):
                result = update_ytdlp()
        self.assertTrue(result.ok)
        self.assertTrue(result.changed)

    def test_release_notes_are_read_from_requested_version(self):
        changelog = """# Historial

## 7.3.0 — hoy

- Avisos de actualización.
- Sección de novedades.

## 7.2.0 — ayer

- Instalador universal.
"""
        self.assertEqual(
            release_notes_for_version(changelog, "7.3.0"),
            ("Avisos de actualización.", "Sección de novedades."),
        )

    def test_release_body_notes_are_limited_and_clean(self):
        body = "# Cambios\n\n- Uno\n* Dos\nTexto\n- Tres"
        self.assertEqual(release_notes_from_body(body), ("Uno", "Dos", "Tres"))

    def test_latest_github_release_is_preferred_over_main(self):
        def read_url(url):
            if "pypi.org" in url:
                return '{"info":{"version":"1"}}'
            if url.endswith("/releases/latest"):
                return '{"tag_name":"v8.0.0","body":"- Estable"}'
            if url.endswith("/CHANGELOG.md"):
                return ""
            raise AssertionError(url)

        with patch("flow.infrastructure.updates._read_url", side_effect=read_url):
            with patch(
                "flow.infrastructure.updates.configured_repository",
                return_value="owner/repository",
            ):
                result = check_available_updates(include_package_manager=False)

        self.assertEqual(result.flow_latest, "8.0.0")
        self.assertEqual(result.flow_ref, "v8.0.0")
        self.assertEqual(result.release_notes, ("Estable",))


if __name__ == "__main__":
    unittest.main()
