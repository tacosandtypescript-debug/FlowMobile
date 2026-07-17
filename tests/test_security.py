from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.security_manifest import manifest_text, verify_manifest


class SecurityManifestTests(unittest.TestCase):
    def test_manifest_detects_modified_executable(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "flow").mkdir()
            target = root / "flow" / "module.py"
            target.write_text("safe = True\n", encoding="utf-8")
            (root / "SECURITY_MANIFEST.sha256").write_text(
                manifest_text(root), encoding="utf-8"
            )
            self.assertEqual(verify_manifest(root), [])
            target.write_text("safe = False\n", encoding="utf-8")
            self.assertIn("Archivo modificado", verify_manifest(root)[0])

    def test_manifest_rejects_unsafe_path(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SECURITY_MANIFEST.sha256").write_text(
                f"{'0' * 64}  ../outside.py\n", encoding="utf-8"
            )
            self.assertIn("ruta no segura", verify_manifest(root)[0])


if __name__ == "__main__":
    unittest.main()
