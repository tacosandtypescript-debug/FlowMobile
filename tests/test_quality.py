import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flow.infrastructure.ffmpeg import probe_media
from flow.infrastructure.ytdlp_gateway import (
    _TIKTOK_API_HOSTS,
    _tiktok_fallback_options,
    available_resolutions,
    common_options,
    estimate_size,
    retry_delay,
    video_format_selector,
)


class QualityDetectionTests(unittest.TestCase):
    def test_tiktok_fallback_covers_multiple_hosts_without_fixed_device(self):
        attempts = list(_tiktok_fallback_options({}))
        hosts = [
            attempt["extractor_args"]["tiktok"]["api_hostname"]
            for attempt in attempts
            if "extractor_args" in attempt
        ]
        self.assertGreaterEqual(len(attempts), 1 + len(_TIKTOK_API_HOSTS))
        for host in _TIKTOK_API_HOSTS:
            self.assertIn(host, hosts)
        device_ids = [
            attempt["extractor_args"]["tiktok"]["device_id"]
            for attempt in attempts
            if "device_id" in attempt.get("extractor_args", {}).get("tiktok", {})
        ]
        self.assertTrue(device_ids)
        self.assertNotIn("7379690547022071302", device_ids)

    def test_download_options_back_off_between_retries(self):
        options = common_options(lambda _: None)
        self.assertEqual(options["sleep_interval_requests"], 0.75)
        self.assertEqual(retry_delay(0), 1.0)
        self.assertEqual(retry_delay(10), 30.0)
        self.assertIn("http", options["retry_sleep_functions"])

    def test_horizontal_and_vertical_video_use_short_dimension(self):
        info = {
            "formats": [
                {"width": 1920, "height": 1080, "vcodec": "h264", "protocol": "https", "url": "https://cdn/a"},
                {"width": 1080, "height": 1920, "vcodec": "h264", "protocol": "https", "url": "https://cdn/b"},
                {"width": 720, "height": 1280, "vcodec": "h264", "protocol": "https", "url": "https://cdn/c"},
            ]
        }
        self.assertEqual(available_resolutions(info), [1080, 720])

    def test_storyboards_are_not_presented_as_video_quality(self):
        info = {
            "formats": [
                {"width": 160, "height": 90, "vcodec": "images", "protocol": "mhtml", "url": "https://cdn/sb"},
                {"width": 1280, "height": 720, "vcodec": "h264", "protocol": "https", "url": "https://cdn/v"},
            ]
        }
        self.assertEqual(available_resolutions(info), [720])

    def test_drm_formats_are_not_presented_as_downloadable(self):
        info = {
            "formats": [
                {
                    "width": 3840, "height": 2160, "vcodec": "h264",
                    "protocol": "https", "has_drm": True, "url": "https://cdn/drm",
                },
                {"width": 1920, "height": 1080, "vcodec": "h264", "protocol": "https", "url": "https://cdn/ok"},
            ]
        }
        self.assertEqual(available_resolutions(info), [1080])

    def test_formats_without_url_are_not_invented_as_qualities(self):
        info = {
            "formats": [
                {"width": 1920, "height": 1080, "vcodec": "h264", "protocol": "https"},
                {"width": 640, "height": 360, "vcodec": "h264", "protocol": "https", "url": "https://cdn/360"},
            ]
        }
        self.assertEqual(available_resolutions(info), [360])

    def test_hls_manifest_is_treated_as_downloadable(self):
        info = {
            "formats": [
                {
                    "width": 1280, "height": 720, "vcodec": "h264",
                    "protocol": "m3u8_native", "manifest_url": "https://cdn/720.m3u8",
                },
            ]
        }
        self.assertEqual(available_resolutions(info), [720])

    def test_video_selector_caps_requested_height(self):
        selector = video_format_selector(720)
        self.assertIn("width=720", selector)
        self.assertIn("height=720", selector)
        self.assertIn("width<=720", selector)
        self.assertNotIn("/bestvideo*+bestaudio/best", selector)
        self.assertEqual(video_format_selector(None), "bestvideo*+bestaudio/best")

    def test_estimate_respects_vertical_resolution_limit(self):
        info = {
            "formats": [
                {
                    "width": 1080, "height": 1920, "vcodec": "h264",
                    "acodec": "none", "filesize": 10_000,
                },
                {
                    "width": 720, "height": 1280, "vcodec": "h264",
                    "acodec": "none", "filesize": 5_000,
                },
            ]
        }
        self.assertEqual(estimate_size(info, 720), 5_000)

    def test_audio_estimate_does_not_use_combined_video_size(self):
        info = {
            "formats": [
                {
                    "vcodec": "h264", "acodec": "aac", "height": 720,
                    "width": 1280, "filesize": 50_000,
                },
                {
                    "vcodec": "none", "acodec": "aac", "filesize": 4_000,
                },
            ]
        }
        self.assertEqual(estimate_size(info, None, audio_only=True), 4_000)

    def test_ffprobe_reads_real_stream_metadata(self):
        completed = SimpleNamespace(
            returncode=0,
            stdout=(
                '{"streams":['
                '{"codec_type":"video","codec_name":"h264","width":1280,"height":720,"r_frame_rate":"30/1"},'
                '{"codec_type":"audio","codec_name":"aac"}'
                '],"format":{"duration":"12.5"}}'
            ),
        )
        with patch("flow.infrastructure.ffmpeg.subprocess.run", return_value=completed):
            with patch.object(Path, "stat", return_value=SimpleNamespace(st_size=1234)):
                result = probe_media(Path("video.mp4"))
        self.assertIsNotNone(result)
        self.assertEqual(result.width, 1280)
        self.assertEqual(result.audio_codec, "aac")
        self.assertEqual(result.size, 1234)


if __name__ == "__main__":
    unittest.main()
