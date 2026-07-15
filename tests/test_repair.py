import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flow.infrastructure.repair import clean_temporary_files


class RepairCleanupTests(unittest.TestCase):
    def test_preserves_parts_registered_for_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            partial = root / "resume.mp4.part"
            partial.write_bytes(b"partial")
            os.utime(partial, (100, 100))
            with patch(
                "flow.infrastructure.repair.protected_partial_files",
                return_value={partial.resolve()},
            ):
                result = clean_temporary_files((root,), minimum_age_seconds=300, now=1000)
            self.assertEqual(result.removed, 0)
            self.assertTrue(partial.exists())

    def test_removes_only_old_temporary_downloads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old_part = root / "video.mp4.part"
            old_conversion = root / "audio [convirtiendo].m4a"
            recent_part = root / "active.mp4.part"
            completed = root / "video.mp4"
            for path in (old_part, old_conversion, recent_part, completed):
                path.write_bytes(b"1234")
            os.utime(old_part, (100, 100))
            os.utime(old_conversion, (100, 100))
            os.utime(recent_part, (950, 950))
            os.utime(completed, (100, 100))

            result = clean_temporary_files((root,), minimum_age_seconds=300, now=1000)

            self.assertEqual(result.removed, 2)
            self.assertEqual(result.recovered_bytes, 8)
            self.assertTrue(recent_part.exists())
            self.assertTrue(completed.exists())


if __name__ == "__main__":
    unittest.main()
