from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from convertir_manifest_panini import convert


class ManifestConversionTests(unittest.TestCase):
    def test_exports_all_stickers_groups_and_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "collection.csv"
            markdown_path = Path(directory) / "collection.md"
            counts = convert(
                Path("panini_digital_collection_22.json"),
                csv_path,
                markdown_path,
            )
            with csv_path.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(counts, (477, 30, 68))
        self.assertEqual(len(rows), 477)
        self.assertEqual(len({row["sticker_id"] for row in rows}), 477)
        self.assertTrue(all(row["pagina"] for row in rows))
        self.assertTrue(all(row["grupo"] for row in rows))

        cubarsi = next(row for row in rows if row["sticker_id"] == "8511")
        self.assertEqual(cubarsi["recurso_global"], "134")
        self.assertEqual(cubarsi["numero_grupo"], "4")
        self.assertEqual(cubarsi["grupo"], "FC BARCELONA")
        self.assertEqual(cubarsi["pagina"], "22")
        self.assertIn("## Grupos", markdown)
        self.assertIn("## Páginas", markdown)
        self.assertIn("## Cromos", markdown)
        self.assertIn("PAU CUBARSÍ", markdown)


if __name__ == "__main__":
    unittest.main()
