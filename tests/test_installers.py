import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bootstrap_ios import latest_stable_reference

from install_ios import (
    _activate_current_session,
    _clean_installations,
    _copy_preserved,
    _configure_profile,
    _restore_preserved,
    _valid_installation,
    _valid_launcher_configuration,
    install,
)


ROOT = Path(__file__).resolve().parents[1]


class InstallerCompatibilityTests(unittest.TestCase):
    def test_ios_bootstrap_refuses_unpublished_source(self):
        with patch("bootstrap_ios.urlopen", side_effect=OSError("offline")):
            self.assertEqual(latest_stable_reference("owner/repository"), "")

    def test_bootstrap_and_launcher_do_not_require_grep(self):
        for relative in ("install.sh", "scripts/flow"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("| grep", content)

    def test_ios_installer_explains_python_requirement(self):
        content = (ROOT / "install-ios.sh").read_text(encoding="utf-8")
        self.assertIn("a-Shell completa", content)
        self.assertIn("Python", content)

    def test_ashell_uses_a_python_installer_instead_of_dash(self):
        content = (ROOT / "install_ios.py").read_text(encoding="utf-8")
        self.assertIn("def install(", content)
        self.assertNotIn("subprocess", content)
        bootstrap = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("bootstrap_ios.py | python3", bootstrap)
        self.assertNotIn("&& cd", bootstrap)
        self.assertIn("abre una nueva", bootstrap)

    def test_termux_installer_supports_stable_tags(self):
        installer = (ROOT / "install-termux.sh").read_text(encoding="utf-8")
        self.assertIn("releases/download/$BRANCH", installer)
        self.assertIn("SHA256SUMS", installer)
        self.assertIn("FLOWMOBILE_ALLOW_UNVERIFIED", installer)

    def test_termux_installer_requires_public_android_downloads(self):
        installer = (ROOT / "install-termux.sh").read_text(encoding="utf-8")
        self.assertIn("shared_storage_ready", installer)
        self.assertIn(".flowmobile-write-test-$$", installer)
        self.assertIn('SHARED_DOWNLOAD_ROOT="$HOME/storage/downloads"', installer)
        self.assertIn('PUBLIC_DOWNLOAD_DIR="$SHARED_DOWNLOAD_ROOT/FlowMobile"', installer)
        self.assertIn('PUBLIC_VIDEO_DIR="$SHARED_MOVIE_ROOT/FlowMobile"', installer)
        self.assertIn('PUBLIC_AUDIO_DIR="$SHARED_MUSIC_ROOT/FlowMobile"', installer)
        self.assertIn("move_saved_media", installer)
        self.assertNotIn('"$APP_DIR/Downloads"', installer)

    def test_termux_sharing_uses_core_command_before_optional_api(self):
        installer = (ROOT / "install-termux.sh").read_text(encoding="utf-8")
        device = (ROOT / "flow" / "infrastructure" / "device.py").read_text(encoding="utf-8")
        self.assertIn("curl termux-tools", installer)
        self.assertIn('"termux-open",', device)
        self.assertIn('shutil.which("termux-share")', device)
        self.assertLess(device.index('"termux-open",'), device.index('shutil.which("termux-share")'))

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

    def test_launcher_validation_requires_profile_and_python_file(self):
        with TemporaryDirectory() as temporary:
            documents = Path(temporary)
            app = documents / "FlowMobile"
            (documents / "bin").mkdir()
            (documents / "bin" / "flow.py").write_text("# launcher")

            self.assertFalse(_valid_launcher_configuration(documents, app))
            _configure_profile(documents, app)
            self.assertTrue(_valid_launcher_configuration(documents, app))

    def test_ios_installer_explains_activation_in_current_window(self):
        content = (ROOT / "install_ios.py").read_text(encoding="utf-8")
        self.assertIn("Abre ahora con: flow", content)
        self.assertIn("cd && . ./.profile && flow", content)

    def test_current_ashell_session_receives_flow_alias(self):
        commands = []

        def executor(command):
            commands.append(command)
            return 0

        app = Path("/private/app/Documents/FlowMobile")
        self.assertTrue(_activate_current_session(app, executor))
        self.assertEqual(
            commands,
            [b'alias flow=\'python3 "/private/app/Documents/FlowMobile/main.py"\''],
        )

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

    def test_ios_update_restores_previous_version_when_dependency_install_fails(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            documents = root / "Documents"
            app = documents / "FlowMobile"
            (app / "flow").mkdir(parents=True)
            (app / "Downloads").mkdir()
            (app / "main.py").write_text("old-version", encoding="utf-8")
            (app / "VERSION").write_text("1.0.0", encoding="utf-8")
            (app / "Downloads" / "keep.mp4").write_bytes(b"keep")

            def fake_source(work_directory):
                source = work_directory / "new-source"
                (source / "flow").mkdir(parents=True)
                (source / "scripts").mkdir()
                (source / "main.py").write_text("new-version", encoding="utf-8")
                (source / "VERSION").write_text("2.0.0", encoding="utf-8")
                (source / "scripts" / "flow_ios.py").write_text("# launcher", encoding="utf-8")
                return source

            with patch("install_ios._download_source_archive"):
                with patch("install_ios._safe_extract"):
                    with patch("install_ios._find_source", side_effect=fake_source):
                        with patch("install_ios._verify_source_manifest"):
                            with patch(
                                "install_ios._install_python_dependencies",
                                side_effect=RuntimeError("pip failed"),
                            ):
                                with self.assertRaises(RuntimeError):
                                    install("owner/repository", home=root)

            self.assertEqual((app / "main.py").read_text(encoding="utf-8"), "old-version")
            self.assertTrue((app / "Downloads" / "keep.mp4").is_file())
            self.assertFalse((documents / ".flowmobile-rollback").exists())
            self.assertTrue(_valid_installation(app))

    def test_copy_preserved_merges_directories(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            saved = root / "saved"
            app = root / "app"
            (saved / ".flowmobile").mkdir(parents=True)
            (app / ".flowmobile").mkdir(parents=True)
            (saved / ".flowmobile" / "queue.json").write_text("{}")
            (app / ".flowmobile" / "settings.json").write_text("{}")

            _copy_preserved(saved, app)

            self.assertTrue((app / ".flowmobile" / "queue.json").is_file())
            self.assertTrue((app / ".flowmobile" / "settings.json").is_file())


if __name__ == "__main__":
    unittest.main()
