from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flow.domain.models import DownloadChoice
from flow.infrastructure import batches


class BatchQueueTests(unittest.TestCase):
    def test_queue_is_private_persistent_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(batches, "QUEUE_DIR", root / "state"):
                with patch.object(batches, "BATCH_DIR", root / "legacy"):
                    with patch.object(batches, "VIDEO_BATCH_DIR", root / "movies"):
                        with patch.object(batches, "AUDIO_BATCH_DIR", root / "music"):
                            batches.QUEUE_DIR.mkdir()
                            queue = batches.create_queue(
                                ["https://example.com/1", "https://example.com/1", "https://example.com/2"],
                                DownloadChoice("video", 720),
                            )
                            queue_folder = queue.folder
                            loaded = batches.load_queue(batches.QUEUE_DIR / f"{queue.queue_id}.json")
            self.assertEqual(len(queue.items), 2)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.choice.height, 720)
            self.assertEqual(queue_folder.parent, root / "movies")

    def test_paused_and_failed_items_remain_pending(self):
        queue = batches.DownloadQueue(
            "queue", "today", DownloadChoice("audio"),
            [
                batches.QueueItem("a", "completed"),
                batches.QueueItem("b", "paused"),
                batches.QueueItem("c", "error"),
            ],
        )
        self.assertEqual(queue.completed, 1)
        self.assertEqual(queue.pending, 2)


if __name__ == "__main__":
    unittest.main()
