import unittest
from unittest.mock import patch

from flow.presentation.cli import FlowCLI


class InteractiveMenuTests(unittest.TestCase):
    def test_closed_input_exits_without_traceback(self):
        cli = FlowCLI.__new__(FlowCLI)
        with patch("builtins.input", side_effect=EOFError):
            with self.assertRaises(SystemExit) as exit_context:
                cli.read_input("Selecciona › ")
        self.assertEqual(exit_context.exception.code, 0)

    def test_short_quality_list_is_preserved(self):
        values = [1080, 720, 480]
        self.assertEqual(FlowCLI.featured_resolutions(values), values)

    def test_long_quality_list_keeps_best_and_worst(self):
        values = [4320, 2160, 1440, 1080, 960, 720, 480, 360, 240, 144]
        featured = FlowCLI.featured_resolutions(values)

        self.assertEqual(featured[0], 4320)
        self.assertEqual(featured[-1], 144)
        self.assertLessEqual(len(featured), 8)
        self.assertEqual(featured, sorted(set(featured), reverse=True))


if __name__ == "__main__":
    unittest.main()
