import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flow.infrastructure import device


class DeviceIntegrationTests(unittest.TestCase):
    def test_termux_share_uses_android_send_action(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=True)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.subprocess, "run", return_value=completed) as run:
                self.assertTrue(device.open_share(Path("/tmp/audio.m4a")))
        self.assertEqual(
            run.call_args.args[0],
            ["termux-open", "--send", "/tmp/audio.m4a"],
        )

    def test_ashell_share_uses_open(self):
        completed = SimpleNamespace(returncode=0)
        platform = SimpleNamespace(is_termux=False)
        with patch.object(device, "PLATFORM", platform):
            with patch.object(device.subprocess, "run", return_value=completed) as run:
                self.assertTrue(device.open_share(Path("/tmp/video.mp4")))
        self.assertEqual(run.call_args.args[0], ["open", "/tmp/video.mp4"])


if __name__ == "__main__":
    unittest.main()
