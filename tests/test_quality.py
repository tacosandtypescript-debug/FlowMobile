import unittest

from flow.infrastructure.ytdlp_gateway import available_resolutions, estimate_size


class QualityDetectionTests(unittest.TestCase):
    def test_horizontal_and_vertical_video_use_short_dimension(self):
        info = {
            "formats": [
                {"width": 1920, "height": 1080, "vcodec": "h264", "protocol": "https"},
                {"width": 1080, "height": 1920, "vcodec": "h264", "protocol": "https"},
                {"width": 720, "height": 1280, "vcodec": "h264", "protocol": "https"},
            ]
        }
        self.assertEqual(available_resolutions(info), [1080, 720])

    def test_storyboards_are_not_presented_as_video_quality(self):
        info = {
            "formats": [
                {"width": 160, "height": 90, "vcodec": "images", "protocol": "mhtml"},
                {"width": 1280, "height": 720, "vcodec": "h264", "protocol": "https"},
            ]
        }
        self.assertEqual(available_resolutions(info), [720])

    def test_drm_formats_are_not_presented_as_downloadable(self):
        info = {
            "formats": [
                {
                    "width": 3840, "height": 2160, "vcodec": "h264",
                    "protocol": "https", "has_drm": True,
                },
                {"width": 1920, "height": 1080, "vcodec": "h264", "protocol": "https"},
            ]
        }
        self.assertEqual(available_resolutions(info), [1080])

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


if __name__ == "__main__":
    unittest.main()
