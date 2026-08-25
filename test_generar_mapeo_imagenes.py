from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from generar_mapeo_imagenes import generate_mapping


class ImageMappingTests(unittest.TestCase):
    def test_generates_safe_name_and_club_matches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "imagenes.csv"
            methods = generate_mapping(
                Path("coleccion_panini_revisada.csv"),
                Path("panini_digital_collection_22.json"),
                output,
            )
            with output.open(encoding="utf-8-sig", newline="") as source:
                rows = {row["id"]: row for row in csv.DictReader(source)}

        matched = sum(bool(row["imagen_url"]) for row in rows.values())
        self.assertEqual(len(rows), 514)
        self.assertEqual(matched, 418)
        self.assertEqual(
            rows["FC-BARCELONA-08"]["digital_label"],
            "PAU CUBARSÍ",
        )
        self.assertEqual(
            rows["FC-BARCELONA-08"]["digital_recurso"],
            "134",
        )
        self.assertEqual(rows["REAL-MADRID-CF-11"]["imagen_url"], "")
        self.assertEqual(
            rows["FC-BARCELONA-01"]["imagen_url"],
            "https://tmssl.akamaized.net/images/wappen/head/131.png",
        )
        self.assertEqual(
            rows["FC-BARCELONA-01"]["metodo_coincidencia"],
            "escudo_transfermarkt",
        )
        self.assertEqual(methods["sin_coincidencia_segura"], 76)


if __name__ == "__main__":
    unittest.main()
