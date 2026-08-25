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
        self.assertEqual(total, 514)
        self.assertEqual(len(stickers), 514)
        self.assertEqual(len({sticker["id"] for sticker in stickers}), 514)
        self.assertEqual(len({sticker["seccion"] for sticker in stickers}), 27)
        self.assertEqual(sum(bool(sticker["imagen_url"]) for sticker in stickers), 418)
        self.assertIn("Álbum completo", html)
        self.assertIn("Repetidos", html)


if __name__ == "__main__":
    unittest.main()
