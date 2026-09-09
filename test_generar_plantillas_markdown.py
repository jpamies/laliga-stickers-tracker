from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from generar_plantillas_markdown import age_on, generate, sort_key, tags


class AgeTests(unittest.TestCase):
    def test_birthday_not_reached_yet_counts_one_year_less(self) -> None:
        self.assertEqual(age_on("2000-12-31", date(2026, 9, 9)), "25")
        self.assertEqual(age_on("2000-01-01", date(2026, 9, 9)), "26")

    def test_missing_or_broken_dates_are_blank(self) -> None:
        self.assertEqual(age_on("", date(2026, 9, 9)), "")
        self.assertEqual(age_on("no-es-fecha", date(2026, 9, 9)), "")


class RowTests(unittest.TestCase):
    def test_squad_is_ordered_by_role_then_shirt_number(self) -> None:
        rows = [
            {"posicion_slug": "delantero", "dorsal": "9", "nombre": "Nueve"},
            {"posicion_slug": "portero", "dorsal": "13", "nombre": "Trece"},
            {"posicion_slug": "entrenador", "dorsal": "", "nombre": "Míster"},
            {"posicion_slug": "portero", "dorsal": "1", "nombre": "Uno"},
            {"posicion_slug": "defensa", "dorsal": "", "nombre": "Sin dorsal"},
        ]

        ordered = [row["nombre"] for row in sorted(rows, key=sort_key)]

        self.assertEqual(ordered, ["Míster", "Uno", "Trece", "Sin dorsal", "Nueve"])

    def test_loans_and_inactive_records_are_flagged(self) -> None:
        self.assertEqual(
            tags({"cedido": "true", "cedido_fuera": "false", "activo": "true"}),
            "cedido",
        )
        self.assertEqual(
            tags({"cedido": "false", "cedido_fuera": "false", "activo": "false"}),
            "ficha inactiva",
        )
        self.assertEqual(
            tags({"cedido": "false", "cedido_fuera": "false", "activo": "true"}),
            "",
        )


class DocumentTests(unittest.TestCase):
    def test_documents_every_club_from_the_real_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plantillas.md"
            players = generate(
                Path("laliga_plantillas.csv"),
                Path("laliga_equipos.csv"),
                output,
                date(2026, 9, 9),
            )
            text = output.read_text(encoding="utf-8")

        self.assertGreater(players, 500)
        self.assertIn("# Plantillas oficiales de LALIGA EA SPORTS 2026-27", text)
        self.assertIn(f"| **Jugadores registrados** | **{players}** |", text)
        self.assertIn("## FC BARCELONA", text)
        # Un apartado por club, más el resumen general.
        self.assertEqual(text.count("\n## "), 21)
        self.assertIn("jugadores registrados", text)

    def test_fails_without_source_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "vacio.csv"
            empty.write_text("slug\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(empty, empty, Path(directory) / "salida.md")


if __name__ == "__main__":
    unittest.main()
