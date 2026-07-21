import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from flow.infrastructure.privacy import protect_private_path


class PrivacyTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "los bits POSIX se comprueban en Linux")
    def test_posix_private_file_removes_group_and_other_permissions(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "private.json"
            target.write_text("{}", encoding="utf-8")
            target.chmod(0o666)
            self.assertTrue(protect_private_path(target, platform_name="posix"))
            self.assertFalse(target.stat().st_mode & 0o077)

    def test_windows_private_directory_uses_current_user_acl(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "private"
            target.mkdir()
            completed = Mock(returncode=0)
            runner = Mock(return_value=completed)
            with patch.dict(
                os.environ,
                {"USERNAME": "flow-user", "USERDOMAIN": "FLOW-PC"},
            ):
                protected = protect_private_path(
                    target,
                    directory=True,
                    platform_name="nt",
                    runner=runner,
                )
            self.assertTrue(protected)
            command = runner.call_args.args[0]
            self.assertEqual(command[0], "icacls.exe")
            self.assertIn("/inheritance:r", command)
            self.assertIn("FLOW-PC\\flow-user:(OI)(CI)F", command)

    def test_windows_acl_failure_is_reported(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "private.txt"
            target.write_text("secret", encoding="utf-8")
            with patch.dict(os.environ, {"USERNAME": "flow-user"}):
                protected = protect_private_path(
                    target,
                    platform_name="nt",
                    runner=Mock(return_value=Mock(returncode=5)),
                )
            self.assertFalse(protected)


if __name__ == "__main__":
    unittest.main()
