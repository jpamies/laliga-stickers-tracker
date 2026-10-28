from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from generar_mapeo_imagenes import (
    Candidate,
    build_candidates,
    choose_match,
    generate_mapping,
    load_collection,
)


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
        self.assertEqual(len(rows), 661)
        self.assertEqual(matched, 427)
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
        self.assertEqual(methods["sin_coincidencia_segura"], 234)

    def test_short_names_do_not_select_photos_of_another_player(self) -> None:
        candidates = build_candidates(load_collection(Path("panini_digital_collection_22.json"), 22))
        for name, club in (("Junior", "Real Betis"), ("Rodri", "FC Barcelona")):
            with self.subTest(name=name):
                result = choose_match(
                    {"nombre": name, "tipo": "medio", "club_objetivo": club},
                    candidates,
                )
                self.assertIsNone(result.candidate)
                self.assertEqual(result.method, "sin_coincidencia_segura")

    def test_a_real_image_of_the_confirmed_player_still_matches(self) -> None:
        for name, club, group, full_name in (
            ("Junior", "Real Betis", 666, "junior firpo"),
            ("Rodri", "FC Barcelona", 665, "rodrigo hernandez cascante"),
        ):
            with self.subTest(name=name):
                correct = Candidate(
                    sticker={"group_id": group},
                    normalized_name=full_name,
                    group_label=club,
                    resource_number="test",
                )
                result = choose_match(
                    {"nombre": name, "tipo": "medio", "club_objetivo": club},
                    [correct],
                )
                self.assertIs(result.candidate, correct)
                self.assertEqual(result.method, "exacta_grupo")

    def test_luiz_junior_and_rodri_mendoza_keep_their_own_images(self) -> None:
        candidates = build_candidates(load_collection(Path("panini_digital_collection_22.json"), 22))
        for name, club, expected in (
            ("Luiz Júnior", "Villarreal CF", "luiz junior"),
            ("Rodri Mendoza", "Atlético de Madrid", "rodri mendoza"),
        ):
            with self.subTest(name=name):
                result = choose_match(
                    {"nombre": name, "tipo": "medio", "club_objetivo": club},
                    candidates,
                )
                self.assertIsNotNone(result.candidate)
                self.assertEqual(result.candidate.normalized_name, expected)


if __name__ == "__main__":
    unittest.main()
