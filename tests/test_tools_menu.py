import unittest
from contextlib import contextmanager
from types import SimpleNamespace

from flow.presentation.tools_menu import show_tools


class ToolsMenuTests(unittest.TestCase):
    def test_menu_prioritizes_feedback_and_removes_redundant_entries(self):
        items: list[tuple[str, str]] = []
        sections: list[str] = []

        @contextmanager
        def buffered_screen():
            yield

        cli = SimpleNamespace(
            buffered_screen=buffered_screen,
            logo=lambda _: None,
            section=sections.append,
            menu_item=lambda key, title, detail=None: items.append((key, title)),
            prompt_choice=lambda *_: "0",
        )
        show_tools(cli)

        self.assertEqual(items[0], ("1", "Sugerencias y reportes"))
        self.assertIn(("3", "Centro de seguridad"), items)
        self.assertIn(("6", "Sistema y reparación"), items)
        self.assertIn(("7", "Diagnóstico y pruebas"), items)
        self.assertNotIn("Sistema", {title for _, title in items})
        self.assertNotIn("Modo Reparar", {title for _, title in items})
        self.assertEqual(
            sections,
            ["AYUDA", "PRIVACIDAD Y PREFERENCIAS", "MANTENIMIENTO"],
        )
