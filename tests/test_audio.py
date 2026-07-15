import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flow.infrastructure.ffmpeg import convert_audio, convert_video


class AudioConversionTests(unittest.TestCase):
    def test_missing_ffmpeg_preserves_download(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "media.mp4"
            source.write_bytes(b"download")

            with patch(
                "flow.infrastructure.ffmpeg.subprocess.run",
                side_effect=OSError("no accesible"),
            ):
                with self.assertRaisesRegex(RuntimeError, "No se pudo iniciar FFmpeg"):
                    convert_audio(source)

            self.assertTrue(source.exists())

    def test_aac_is_extracted_without_reencoding(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "media.mp4"
            source.write_bytes(b"download")

            def successful_copy(command, **kwargs):
                Path(command[-1]).write_bytes(b"audio")
                return SimpleNamespace(returncode=0, stderr="")

            with patch("flow.infrastructure.ffmpeg.subprocess.run", side_effect=successful_copy):
                result = convert_audio(source)

            self.assertEqual(result.suffix, ".m4a")
            self.assertTrue(result.exists())
            self.assertFalse(source.exists())


class VideoConversionTests(unittest.TestCase):
    def test_progress_output_finishes_without_separate_stderr_pipe(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "media.webm"
            source.write_bytes(b"download")
            progress: list[float] = []

            def fake_popen(command, **kwargs):
                Path(command[-1]).write_bytes(b"video")
                return SimpleNamespace(
                    stdout=["out_time_ms=1000000\n", "progress=end\n"],
                    wait=lambda: 0,
                )

            with (
                patch("flow.infrastructure.ffmpeg.is_ios_compatible", return_value=False),
                patch("flow.infrastructure.ffmpeg.has_encoder", return_value=True),
                patch("flow.infrastructure.ffmpeg.subprocess.Popen", side_effect=fake_popen),
            ):
                result = convert_video(source, 2, progress.append)

            self.assertTrue(result.exists())
            self.assertFalse(source.exists())
            self.assertEqual(progress[-1], 100.0)


if __name__ == "__main__":
    unittest.main()
