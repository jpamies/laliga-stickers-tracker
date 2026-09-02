from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from generar_plantillas_html import generate


class SquadPageTests(unittest.TestCase):
    def test_embeds_squads_teams_and_themes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plantillas.html"
            total = generate(
                Path("laliga_plantillas.csv"), Path("laliga_equipos.csv"), output
            )
            html = output.read_text(encoding="utf-8")

        players = json.loads(
            re.search(r"window\.SQUAD_DATA = (.*?);</script>", html, re.DOTALL).group(1)
        )
        teams = json.loads(
            re.search(r"window\.SQUAD_TEAMS = (.*?);</script>", html, re.DOTALL).group(1)
        )
        themes = json.loads(
            re.search(r"window\.SQUAD_THEMES = (.*?);</script>", html, re.DOTALL).group(1)
        )

        self.assertEqual(total, len(players))
        self.assertEqual(len(teams), 20)
        self.assertEqual(len({player["clave"] for player in players}), len(players))
        self.assertEqual(len({player["seccion_album"] for player in players}), 20)
        self.assertIn("*", themes)
        self.assertIn("FC BARCELONA", themes)
        self.assertTrue(
            all(player["seccion_album"] in themes for player in players)
        )
        self.assertIn('src="plantillas.js?v=2"', html)
        self.assertIn('href="index.html"', html)
        self.assertIn('name="robots" content="noindex"', html)

    def test_fails_without_source_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "vacio.csv"
            empty.write_text("slug\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(empty, empty, Path(directory) / "out.html")


if __name__ == "__main__":
    unittest.main()
