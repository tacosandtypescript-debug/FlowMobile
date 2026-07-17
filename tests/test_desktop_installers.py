import os
import hashlib
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import runpy
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class DesktopInstallerTests(unittest.TestCase):
    def _shell_path(self, path: Path) -> str:
        if os.name != "nt":
            return str(path)
        return subprocess.check_output(
            ["cygpath", "-u", str(path)], text=True, encoding="utf-8"
        ).strip()

    def _fake_command(self, directory: Path, name: str, body: str) -> None:
        target = directory / name
        target.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        target.chmod(0o755)

    def _linux_fixture(self, root: Path) -> tuple[Path, Path]:
        package = root / "package" / "FlowMobile-8.0.0"
        (package / "flow").mkdir(parents=True)
        (package / "scripts").mkdir()
        (package / "main.py").write_text("new-version", encoding="utf-8")
        (package / "VERSION").write_text("8.0.0\n", encoding="utf-8")
        (package / "requirements.lock").write_text("", encoding="utf-8")
        (package / "SECURITY_MANIFEST.sha256").write_text("fixture\n", encoding="utf-8")
        (package / "scripts" / "security_manifest.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        archive = root / "FlowMobile-8.0.0.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(package, arcname=package.name)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        sums = root / "SHA256SUMS"
        sums.write_text(f"{digest}  FlowMobile-8.0.0.tar.gz\n", encoding="utf-8")
        return archive, sums

    def _run_linux_fixture(self, fail_pip: bool = False, previous: bool = False):
        temporary = TemporaryDirectory()
        root = Path(temporary.name)
        home = root / "home"
        fake_bin = root / "bin"
        home.mkdir()
        fake_bin.mkdir()
        archive, sums = self._linux_fixture(root)
        if previous:
            app = home / ".local" / "share" / "flowmobile"
            (app / "flow").mkdir(parents=True)
            (app / "main.py").write_text("previous-version", encoding="utf-8")
            (app / ".flowmobile").mkdir()
            (app / ".flowmobile" / "settings.json").write_text("{}", encoding="utf-8")

        self._fake_command(fake_bin, "ffmpeg", "exit 0\n")
        self._fake_command(fake_bin, "ffprobe", "exit 0\n")
        self._fake_command(fake_bin, "sleep", "exit 0\n")
        self._fake_command(
            fake_bin,
            "curl",
            'output=""; url=""\n'
            'while [ "$#" -gt 0 ]; do case "$1" in -o) shift; output=$1 ;; http*) url=$1 ;; esac; shift; done\n'
            'case "$url" in *SHA256SUMS) cp "$FAKE_SUMS" "$output" ;; *) cp "$FAKE_ARCHIVE" "$output" ;; esac\n',
        )
        self._fake_command(
            fake_bin,
            "python3",
            'if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then\n'
            '  destination=$3; mkdir -p "$destination/bin"\n'
            '  printf \'%s\\n\' \'#!/bin/sh\' \'case "$*" in *"-m pip"*) [ "${FAKE_PIP_FAIL:-0}" = 1 ] && { echo "ERROR: simulated pip failure"; exit 9; } ;; esac\' \'exit 0\' > "$destination/bin/python"\n'
            '  chmod +x "$destination/bin/python"; exit 0\n'
            'fi\nexit 0\n',
        )
        environment = os.environ.copy()
        environment.update(
            HOME=self._shell_path(home),
            FLOWMOBILE_BRANCH="v8.0.0",
            FLOWMOBILE_INSTALL_LOG=self._shell_path(root / "install.log"),
            FAKE_ARCHIVE=self._shell_path(archive),
            FAKE_SUMS=self._shell_path(sums),
            FAKE_PIP_FAIL="1" if fail_pip else "0",
        )
        command = [
            "sh",
            "-c",
            'PATH="$1:/usr/bin:/bin"; export PATH; exec sh "$2" "$3"',
            "flowmobile-linux-test",
            self._shell_path(fake_bin),
            self._shell_path(ROOT / "install-linux.sh"),
            "owner/repository",
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment, check=False)
        app = home / ".local" / "share" / "flowmobile"
        content = (app / "main.py").read_text(encoding="utf-8") if (app / "main.py").is_file() else None
        launcher = (home / ".local" / "bin" / "flow").is_file()
        state = (app / ".flowmobile" / "settings.json").is_file()
        log = (root / "install.log").read_text(encoding="utf-8")
        temporary.cleanup()
        return result, content, launcher, state, log

    def test_desktop_installers_have_six_stages_and_rollback(self):
        linux = (ROOT / "install-linux.sh").read_text(encoding="utf-8-sig")
        windows = (ROOT / "install-windows.ps1").read_text(encoding="utf-8-sig")
        for stage in (
            "Preparando",
            "Dependencias",
            "Descargando",
            "Verificando",
            "Instalando",
            "Activando flow",
        ):
            self.assertIn(stage, linux)
            self.assertIn(stage, windows)
        self.assertIn("rollback", linux)
        self.assertIn("$BackupReady", windows)
        self.assertIn("--health-check", linux)
        self.assertIn("--health-check", windows)

    def test_windows_uses_verified_release_and_official_winget_ids(self):
        installer = (ROOT / "install-windows.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("Python.Python.3.13", installer)
        self.assertIn("Gyan.FFmpeg", installer)
        self.assertIn("Get-FileHash -Algorithm SHA256", installer)
        self.assertIn("SECURITY_MANIFEST", installer)
        self.assertIn("FM-WINDOWS-INTEGRITY", installer)

    def test_linux_supports_common_package_managers_and_verification(self):
        installer = (ROOT / "install-linux.sh").read_text(encoding="utf-8")
        for manager in ("apt-get", "dnf", "pacman", "zypper"):
            self.assertIn(manager, installer)
        self.assertIn("sha256sum", installer)
        self.assertIn("security_manifest.py", installer)
        self.assertIn("FM-LINUX-INTEGRITY", installer)

    def test_release_publishes_both_desktop_installers(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("install-windows.ps1", workflow)
        self.assertIn("install-linux.sh", workflow)

    def test_health_check_validates_multimedia_tools_without_opening_menu(self):
        output = StringIO()
        with patch("sys.argv", ["main.py", "--health-check"]):
            with patch("flow.infrastructure.ffmpeg.tools_status", return_value=(True, True)):
                with redirect_stdout(output), self.assertRaises(SystemExit) as stopped:
                    runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("FlowMobile 8.0.0: OK", output.getvalue())

    def test_health_check_rejects_missing_ffmpeg(self):
        error = StringIO()
        with patch("sys.argv", ["main.py", "--health-check"]):
            with patch("flow.infrastructure.ffmpeg.tools_status", return_value=(False, False)):
                with redirect_stderr(error), self.assertRaises(SystemExit) as stopped:
                    runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
        self.assertEqual(stopped.exception.code, 1)
        self.assertIn("FFmpeg", error.getvalue())

    @unittest.skipUnless(shutil.which("sh"), "se necesita un shell POSIX")
    def test_linux_invalid_repository_is_a_short_exact_error(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = os.environ.copy()
            environment.update(
                HOME=self._shell_path(root),
                FLOWMOBILE_INSTALL_LOG=self._shell_path(root / "install.log"),
            )
            result = subprocess.run(
                ["sh", self._shell_path(ROOT / "install-linux.sh"), "repositorio-invalido"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                check=False,
            )
            visible = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FM-LINUX-PREPARE", visible)
            self.assertIn("Repositorio inválido", visible)
            self.assertTrue((root / "install.log").is_file())

    @unittest.skipUnless(shutil.which("sh"), "se necesita un shell POSIX")
    def test_linux_clean_install_activates_flow(self):
        result, content, launcher, _, log = self._run_linux_fixture()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + log)
        self.assertEqual(content, "new-version")
        self.assertTrue(launcher)
        self.assertIn("FlowMobile 8.0.0 instalado correctamente", result.stdout)

    @unittest.skipUnless(shutil.which("sh"), "se necesita un shell POSIX")
    def test_linux_pip_failure_restores_previous_version_and_state(self):
        result, content, _, state, log = self._run_linux_fixture(fail_pip=True, previous=True)
        visible = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FM-LINUX-PIP", visible, log)
        self.assertIn("Se restauró la versión anterior", visible)
        self.assertEqual(content, "previous-version")
        self.assertTrue(state)

    @unittest.skipUnless(shutil.which("powershell"), "se necesita Windows PowerShell")
    def test_windows_installer_parses_and_reports_invalid_repository(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = os.environ.copy()
            environment.update(
                HOME=str(root),
                LOCALAPPDATA=str(root / "local"),
                FLOWMOBILE_INSTALL_LOG=str(root / "install.log"),
            )
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ROOT / "install-windows.ps1"),
                    "-Repository",
                    "repositorio-invalido",
                    "-Auto",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                check=False,
            )
            visible = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FM-WINDOWS-PREPARE", visible)
            self.assertTrue((root / "install.log").is_file())


if __name__ == "__main__":
    unittest.main()
