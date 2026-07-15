import unittest

from flow.domain.progress import DownloadProgress


class DownloadProgressTests(unittest.TestCase):
    def test_calculates_speed_and_eta_when_site_omits_them(self):
        progress = DownloadProgress()
        progress.update(
            {"filename": "video.part", "downloaded_bytes": 100, "total_bytes": 1000},
            now=1.0,
        )
        snapshot = progress.update(
            {"filename": "video.part", "downloaded_bytes": 300, "total_bytes": 1000},
            now=2.0,
        )

        self.assertIsNotNone(snapshot)
        self.assertAlmostEqual(snapshot.percent, 30.0)
        self.assertAlmostEqual(snapshot.speed, 200.0)
        self.assertAlmostEqual(snapshot.eta, 3.5)

    def test_new_download_stage_resets_previous_speed(self):
        progress = DownloadProgress()
        progress.update(
            {"filename": "video.part", "downloaded_bytes": 100, "total_bytes": 1000, "speed": 500},
            now=1.0,
        )
        snapshot = progress.update(
            {"filename": "audio.part", "downloaded_bytes": 10, "total_bytes": 100, "speed": 20},
            now=2.0,
        )

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.speed, 20.0)
        self.assertEqual(snapshot.percent, 10.0)


if __name__ == "__main__":
    unittest.main()
