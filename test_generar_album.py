from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from generar_album import generate


class AlbumGenerationTests(unittest.TestCase):
    def test_generates_self_contained_collection_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.html"
            total = generate(Path("coleccion_panini_revisada.csv"), output)
            html = output.read_text(encoding="utf-8")

        match = re.search(
            r"window\.ALBUM_DATA = (.*?);</script>",
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        stickers = json.loads(match.group(1))
        themes_match = re.search(
            r"window\.ALBUM_PLACEHOLDERS = (.*?);</script>",
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(themes_match)
        themes = json.loads(themes_match.group(1))
        self.assertEqual(total, 593)
        self.assertEqual(len(stickers), 593)
        self.assertEqual(len({sticker["id"] for sticker in stickers}), 593)
        self.assertEqual(len({sticker["seccion"] for sticker in stickers}), 29)
        self.assertEqual(
            sum(sticker["imagen_provisional"] != "true" for sticker in stickers),
            423,
        )
        self.assertEqual(
            sum(sticker["imagen_provisional"] == "true" for sticker in stickers),
            170,
        )
        self.assertEqual(
            sum(bool(sticker["foto_url"]) for sticker in stickers),
            85,
        )
        self.assertEqual(
            sum(sticker["accion"] == "NO PEGAR" for sticker in stickers),
            0,
        )
        self.assertEqual({sticker["accion"] for sticker in stickers}, {"PEGAR", "ESPERAR"})
        # La ausencia en la plantilla oficial viaja como dato, nunca como una
        # recomendación pública de no pegar.
        self.assertEqual(
            sum(sticker["estado_laliga"] == "fuera_plantilla" for sticker in stickers),
            65,
        )
        self.assertTrue(
            all(
                sticker["accion"] == "PEGAR"
                for sticker in stickers
                if sticker["estado_laliga"] == "fuera_plantilla"
            )
        )
        self.assertEqual(
            sum(sticker["edicion"] == "2ed" for sticker in stickers),
            44,
        )
        alaves_placeholder = next(
            sticker for sticker in stickers if sticker["id"] == "ATHLETIC-CLUB-DE-BILBAO-11"
        )
        self.assertIn("img.a.transfermarkt.technology", alaves_placeholder["foto_url"])
        self.assertIn("tmssl.akamaized.net", alaves_placeholder["escudo_url"])
        weak_match = next(
            sticker for sticker in stickers if sticker["id"] == "DEPORTIVO-ALAVES-08"
        )
        self.assertEqual(weak_match["foto_url"], "")
        self.assertIn("tmssl.akamaized.net", weak_match["escudo_url"])
        self.assertIn("*", themes)
        self.assertIn("DEPORTIVO ALAVÉS", themes)
        self.assertEqual(themes["DEPORTIVO ALAVÉS"]["code"], "ALA")
        updates = [
            sticker
            for sticker in stickers
            if sticker["seccion"] in {"ÚLTIMOS FICHAJES", "TOP FICHAJES"}
        ]
        self.assertEqual(len(updates), 69)
        self.assertEqual(
            [sticker["numero"] for sticker in updates[:2]],
            ["UF1", "UF2"],
        )
        self.assertEqual(
            [sticker["numero"] for sticker in updates[-3:]],
            ["67", "68", "69"],
        )
        published = [sticker for sticker in updates if sticker["nombre"]]
        pending = [sticker for sticker in updates if not sticker["nombre"]]
        self.assertEqual(len(published), 20)
        self.assertEqual(len(pending), 49)
        self.assertTrue(all(sticker["edicion"] == "2ed" for sticker in published))
        self.assertTrue(all(sticker["accion"] == "PEGAR" for sticker in published))
        self.assertTrue(
            all(sticker["estado_plantilla"] == "pendiente_publicacion" for sticker in pending)
        )
        self.assertTrue(all(sticker["accion"] == "ESPERAR" for sticker in pending))
        self.assertTrue(all(not sticker["foto_url"] for sticker in pending))
        self.assertIn("Álbum completo", html)
        self.assertIn("Repetidos", html)
        self.assertNotIn('id="summary-stuck"', html)
        self.assertNotIn('data-filter="stuck"', html)
        self.assertIn('id="auth-button"', html)
        self.assertIn('id="section-menu"', html)
        self.assertIn('id="section-prev"', html)
        self.assertIn('id="section-next"', html)
        self.assertIn('id="section-current"', html)
        self.assertNotIn("Tu colección, bajo control.", html)
        self.assertIn('id="figuritas-text"', html)
        self.assertIn('id="figuritas-preview"', html)
        self.assertIn('id="section-clear"', html)
        self.assertIn('id="import-json"', html)
        self.assertIn('src="app.js?v=43"', html)
        self.assertIn('href="styles.css?v=25"', html)
        self.assertIn('src="cloud-config.js?v=15"', html)
        self.assertIn('src="cloud-sync.js?v=14"', html)
        self.assertIn('src="social.js?v=16"', html)
        self.assertIn('data-view="friends"', html)


if __name__ == "__main__":
    unittest.main()
