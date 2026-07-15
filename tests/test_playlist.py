import unittest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from flow.infrastructure import ytdlp_gateway
from flow.domain.cancellation import DownloadCancelled


class PlaylistTests(unittest.TestCase):
    def test_ctrl_c_becomes_clean_cancellation(self):
        downloader = MagicMock()
        downloader.__enter__.return_value.extract_info.side_effect = KeyboardInterrupt
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(ytdlp_gateway.yt_dlp, "YoutubeDL", return_value=downloader):
                with patch.object(ytdlp_gateway, "register_partial_files"):
                    with self.assertRaises(DownloadCancelled):
                        ytdlp_gateway.download(
                            "https://example.com/video",
                            "video",
                            720,
                            lambda _: None,
                            video_dir=root,
                        )

    def test_playlist_extracts_unique_web_urls(self):
        downloader = MagicMock()
        downloader.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"webpage_url": "https://example.com/1"},
                {"webpage_url": "https://example.com/1"},
                {"url": "https://example.com/2"},
            ]
        }
        with patch.object(ytdlp_gateway.yt_dlp, "YoutubeDL", return_value=downloader):
            urls = ytdlp_gateway.playlist_urls("https://example.com/list")
        self.assertEqual(urls, ["https://example.com/1", "https://example.com/2"])

    def test_download_options_keep_parts_and_use_private_cookies(self):
        with patch.object(ytdlp_gateway, "cookie_options", return_value={"cookiefile": "/private/cookies.txt"}):
            options = ytdlp_gateway.common_options(lambda _: None)
        self.assertTrue(options["continuedl"])
        self.assertFalse(options["nopart"])
        self.assertEqual(options["cookiefile"], "/private/cookies.txt")


if __name__ == "__main__":
    unittest.main()
