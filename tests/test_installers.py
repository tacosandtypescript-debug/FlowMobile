import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
