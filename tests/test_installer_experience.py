import errno
import hashlib
from io import BytesIO
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from install_ios import InstallerUI, _diagnose_install_error, _download


ROOT = Path(__file__).resolve().parents[1]


class IOSInstallerExperienceTests(unittest.TestCase):
    def test_known_failures_have_actionable_codes(self):
        cases = (
            (URLError("DNS unavailable"), "Descargando", "FM-IOS-NETWORK"),
            (HTTPError("https://github.com", 404, "missing", {}, None), "Descargando", "FM-IOS-HTTP-404"),
            (HTTPError("https://github.com", 429, "limited", {}, None), "Descargando", "FM-IOS-HTTP-429"),
            (OSError(errno.ENOSPC, "No space left"), "Instalando", "FM-IOS-SPACE"),
            (RuntimeError("pip failed"), "Dependencias", "FM-IOS-PIP"),
            (RuntimeError("SHA-256 mismatch"), "Verificando", "FM-IOS-INTEGRITY"),
            (PermissionError(errno.EACCES, "Permission denied"), "Instalando", "FM-IOS-PERMISSION"),
        )
        for error, stage, expected in cases:
            with self.subTest(expected):
                self.assertEqual(_diagnose_install_error(error, stage).code, expected)

    def test_private_log_is_replaced_on_each_attempt(self):
        with TemporaryDirectory() as temporary:
            log = Path(temporary) / ".flowmobile-install.log"
            log.write_text("old private output", encoding="utf-8")
            ui = InstallerUI(log)
            ui.write("new output\n")
            content = log.read_text(encoding="utf-8")
            self.assertNotIn("old private output", content)
            self.assertIn("new output", content)
            if os.name != "nt":
                self.assertEqual(log.stat().st_mode & 0o077, 0)

    def test_verbose_mode_is_opt_in(self):
        with TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"FLOWMOBILE_VERBOSE": "1"}):
                self.assertTrue(InstallerUI(Path(temporary) / "install.log").verbose)

    def test_network_download_retries_once(self):
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "asset"
            with patch("install_ios.time.sleep"):
                with patch(
                    "install_ios.urlopen",
                    side_effect=[URLError("temporary DNS"), BytesIO(b"verified")],
                ) as opened:
                    _download("https://github.com/asset", destination)
            self.assertEqual(opened.call_count, 2)
            self.assertEqual(destination.read_bytes(), b"verified")

    def test_http_404_is_not_retried(self):
        error = HTTPError("https://github.com/missing", 404, "missing", {}, None)
        with TemporaryDirectory() as temporary:
            with patch("install_ios.urlopen", side_effect=error) as opened:
                with self.assertRaises(HTTPError):
                    _download("https://github.com/missing", Path(temporary) / "asset")
            self.assertEqual(opened.call_count, 1)


@unittest.skipUnless(shutil.which("sh"), "se necesita un shell POSIX")
class TermuxInstallerExperienceTests(unittest.TestCase):
    def _shell_path(self, path: Path) -> str:
        if os.name != "nt":
            return str(path)
        return subprocess.check_output(
            ["cygpath", "-u", str(path)], text=True, encoding="utf-8"
        ).strip()

    def _command(self, directory: Path, name: str, body: str) -> None:
        target = directory / name
        target.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        target.chmod(0o755)

    def _run(
        self,
        pkg_body: str,
        curl_body: str = "exit 0\n",
        storage_body: str = 'mkdir -p "$HOME/storage/downloads" "$HOME/storage/movies" "$HOME/storage/music"\n',
        prepare=None,
        commands: dict[str, str] | None = None,
    ):
        temporary = TemporaryDirectory()
        root = Path(temporary.name)
        fake_bin = root / "bin"
        fake_bin.mkdir()
        self._command(fake_bin, "pkg", pkg_body)
        self._command(fake_bin, "curl", curl_body)
        self._command(fake_bin, "sleep", "exit 0\n")
        self._command(
            fake_bin,
            "termux-setup-storage",
            storage_body,
        )
        for name, body in (commands or {}).items():
            self._command(fake_bin, name, body)
        environment = os.environ.copy()
        environment.update(
            HOME=self._shell_path(root / "home"),
            PREFIX=self._shell_path(root / "prefix"),
            FLOWMOBILE_BRANCH="v7.6.19",
            FLOWMOBILE_INSTALL_LOG=self._shell_path(root / "install.log"),
        )
        (root / "home").mkdir()
        extra_environment = prepare(root) if prepare else {}
        if os.name == "nt":
            extra_environment = {
                key: self._shell_path(Path(value))
                for key, value in (extra_environment or {}).items()
            }
        environment.update(extra_environment or {})
        result = subprocess.run(
            [
                "sh",
                "-c",
                'PATH="$1:/usr/bin:/bin"; export PATH; exec sh "$2" "$3"',
                "flowmobile-test",
                self._shell_path(fake_bin),
                self._shell_path(ROOT / "install-termux.sh"),
                "owner/repository",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            check=False,
        )
        log = (root / "install.log").read_text(encoding="utf-8")
        installed_main = root / "home" / "FlowMobile" / "main.py"
        restored_content = (
            installed_main.read_text(encoding="utf-8") if installed_main.is_file() else None
        )
        preserved_download = (root / "home" / "FlowMobile" / "Downloads" / "keep.mp4").is_file()
        temporary.cleanup()
        return result, log, restored_content, preserved_download

    def test_pkg_noise_is_hidden_and_exact_failure_is_reported(self):
        result, log, _, _ = self._run(
            'i=0; while [ "$i" -lt 30 ]; do echo "PACKAGE NOISE"; i=$((i+1)); done\n'
            'echo "Unable to locate package python"\nexit 7\n'
        )
        visible = result.stdout + result.stderr
        self.assertNotIn("PACKAGE NOISE", visible)
        self.assertIn("FM-TERMUX-PKG", visible)
        self.assertIn("Unable to locate package python", visible)
        self.assertIn("PACKAGE NOISE", log)

    def test_network_failure_is_retried_once_and_explained(self):
        result, log, _, _ = self._run(
            "exit 0\n",
            'echo "curl: (6) Could not resolve host: github.com"\nexit 6\n',
        )
        visible = result.stdout + result.stderr
        self.assertIn("reintentando una vez", visible)
        self.assertIn("FM-TERMUX-NETWORK", visible)
        self.assertIn("Could not resolve host", visible)
        self.assertIn("Could not resolve host", log)

    def test_http_error_keeps_exact_status(self):
        result, _, _, _ = self._run(
            "exit 0\n",
            'echo "curl: (22) The requested URL returned error: 404"\nexit 22\n',
        )
        visible = result.stdout + result.stderr
        self.assertIn("FM-TERMUX-HTTP-404", visible)
        self.assertIn("error: 404", visible)

    def test_storage_permission_has_specific_solution(self):
        result, _, _, _ = self._run("exit 0\n", storage_body="exit 0\n")
        visible = result.stdout + result.stderr
        self.assertIn("FM-TERMUX-STORAGE", visible)
        self.assertIn("termux-setup-storage", visible)

    def test_pip_failure_restores_previous_termux_installation(self):
        def prepare(root: Path) -> dict[str, str]:
            previous = root / "home" / "FlowMobile"
            (previous / "Downloads").mkdir(parents=True)
            (previous / "main.py").write_text("previous-version", encoding="utf-8")
            (previous / "Downloads" / "keep.mp4").write_bytes(b"keep")

            package = root / "package" / "FlowMobile-7.6.19"
            (package / "flow").mkdir(parents=True)
            (package / "scripts").mkdir()
            (package / "main.py").write_text("new-version", encoding="utf-8")
            (package / "VERSION").write_text("7.6.19\n", encoding="utf-8")
            (package / "requirements.lock").write_text("", encoding="utf-8")
            (package / "scripts" / "flow").write_text("#!/bin/sh\n", encoding="utf-8")
            (package / "scripts" / "security_manifest.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
            archive = root / "FlowMobile-7.6.19.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(package, arcname=package.name)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            sums = root / "SHA256SUMS"
            sums.write_text(f"{digest}  FlowMobile-7.6.19.tar.gz\n", encoding="utf-8")
            return {"FAKE_ARCHIVE": str(archive), "FAKE_SUMS": str(sums)}

        curl = r'''
output=""
url=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o) shift; output=$1 ;;
        http*) url=$1 ;;
    esac
    shift
done
case "$url" in
    *SHA256SUMS) cp "$FAKE_SUMS" "$output" ;;
    *) cp "$FAKE_ARCHIVE" "$output" ;;
esac
'''
        python = r'''
case "$*" in
    *security_manifest.py*) exit 0 ;;
    *"-m pip"*) echo "ERROR: simulated pip failure"; exit 9 ;;
esac
exit 0
'''
        result, log, restored, kept = self._run(
            "exit 0\n",
            curl,
            prepare=prepare,
            commands={"python3": python},
        )
        visible = result.stdout + result.stderr
        self.assertIn("FM-TERMUX-PIP", visible, log)
        self.assertIn("se restauró la versión anterior", visible)
        self.assertEqual(restored, "previous-version")
        self.assertTrue(kept)


if __name__ == "__main__":
    unittest.main()
