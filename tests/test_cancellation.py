from io import StringIO
import unittest
from unittest.mock import patch

from flow.application.media_service import MediaService
from flow.domain.cancellation import DownloadCancelled, cancellation_requested
from flow.domain.models import DownloadChoice, MediaInfo


class CancellationTests(unittest.TestCase):
    def test_ctrl_c_during_conversion_preserves_downloaded_source(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.m4a"
            source.write_bytes(b"audio")
            media = MediaInfo("https://example.com", "title", "author", "Web", 1, {})
            with patch(
                "flow.application.media_service.ytdlp_gateway.download",
                return_value=({"duration": 1}, source),
            ):
                with patch(
                    "flow.application.media_service.convert_audio",
                    side_effect=KeyboardInterrupt,
                ):
                    result = MediaService().download(
                        media,
                        DownloadChoice("audio"),
                        lambda _: None,
                        lambda _: None,
                    )
        self.assertFalse(result.ok)
        self.assertIsInstance(result.error, DownloadCancelled)
        self.assertEqual(result.file, source)

    def test_c_plus_enter_requests_cancellation(self):
        keyboard = StringIO("c\n")
        with patch("flow.domain.cancellation.sys.stdin", keyboard):
            with patch("flow.domain.cancellation.select.select", return_value=([keyboard], [], [])):
                self.assertTrue(cancellation_requested())

    def test_download_continues_when_no_key_is_ready(self):
        with patch("flow.domain.cancellation.select.select", return_value=([], [], [])):
            self.assertFalse(cancellation_requested())


if __name__ == "__main__":
    unittest.main()
