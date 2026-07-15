from pathlib import Path
import tempfile
import unittest

from flow.application.real_tests import full_cases, verify_download
from flow.domain.models import DownloadChoice
from flow.infrastructure.ffmpeg import MediaProbe


class RealDownloadVerificationTests(unittest.TestCase):
    def test_full_matrix_contains_requested_video_and_audio_cases(self):
        self.assertEqual(
            [case.label for case in full_cases()],
            ["Video 360p", "Video 720p", "Video 1080p", "Video máxima", "Audio M4A", "Audio MP3"],
        )

    def test_video_verifies_resolution_codec_size_and_share_readiness(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "video.mp4"
            path.write_bytes(b"video")
            probe = MediaProbe(5, 10, 1280, 720, 30, "h264", "aac")

            result = verify_download(path, DownloadChoice("video", 720), probe)

            self.assertTrue(result.ok)
            self.assertTrue(result.share_ready)
            self.assertEqual(result.video_codec, "h264")

    def test_video_fails_if_real_resolution_exceeds_requested_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "video.mp4"
            path.write_bytes(b"video")
            probe = MediaProbe(5, 10, 1920, 1080, 30, "h264", "aac")
            result = verify_download(path, DownloadChoice("video", 720), probe)
            self.assertFalse(result.ok)

    def test_audio_verifies_requested_container_and_codec(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audio.mp3"
            path.write_bytes(b"audio")
            probe = MediaProbe(5, 10, None, None, None, None, "mp3")
            result = verify_download(path, DownloadChoice("audio", audio_format="mp3"), probe)
            self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
