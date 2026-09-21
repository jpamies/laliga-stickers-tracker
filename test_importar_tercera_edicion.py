from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from importar_tercera_edicion import (
    BIS_NUMBERS,
    BIS_STICKERS,
    CSV_FIELDS,
    EDITION,
    LATEST_SIGNINGS,
    PENDING_SLOTS,
    SECTION_CLUBS,
    add_bis,
    add_latest_signings,
    bis_id,
    fill_pending,
)


class SourceTests(unittest.TestCase):
    """La lista viene de un anuncio en prosa, así que conviene comprobar que al
    pasarla a código no se ha colado un duplicado ni se ha perdido una línea."""

    def test_the_announced_numbers_are_a_clean_run(self) -> None:
        numbers = [number for number, *_ in LATEST_SIGNINGS]

        self.assertEqual(numbers, list(range(21, 41)))

    def test_no_player_is_announced_twice(self) -> None:
        names = [name for _, name, *_ in LATEST_SIGNINGS]
        self.assertEqual(len(set(names)), len(names))

        bis = [(section, name) for section, name, _ in BIS_STICKERS]
        self.assertEqual(len(set(bis)), len(bis))

    def test_every_bis_section_has_a_club(self) -> None:
        # El club es lo que usa `comprobar_plantillas.py` para saber contra qué
        # plantilla comparar; sin él la comprobación aborta.
        for section, _, _ in BIS_STICKERS:
            self.assertIn(section, SECTION_CLUBS)

    def test_only_the_published_bis_carries_a_number(self) -> None:
        self.assertEqual(list(BIS_NUMBERS), [("FC BARCELONA", "Hamza Abdelkarim")])


class IdentifierTests(unittest.TestCase):
    def test_the_identifier_does_not_depend_on_the_file(self) -> None:
        # El progreso del álbum se guarda por identificador. Si saliera de un
        # contador sobre las filas existentes, regenerar el checklist desde el
        # PDF movería los cromos y el usuario perdería lo que ya tenía pegado.
        self.assertEqual(bis_id("DEPORTIVO ALAVÉS", 1), "DEPORTIVO-ALAVES-BIS-1")
        self.assertEqual(bis_id("RCD ESPANYOL", 3), "RCD-ESPANYOL-BIS-3")

    def test_identifiers_do_not_collide_with_the_numbered_stickers(self) -> None:
        self.assertNotEqual(bis_id("SEVILLA", 4), "SEVILLA-04")


class ImportTests(unittest.TestCase):
    def rows(self) -> list[dict[str, str]]:
        with Path("coleccion_panini.csv").open(encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))

    def test_every_pending_slot_exists_and_gets_filled(self) -> None:
        rows = self.rows()
        by_slot = {(row["seccion"], row["numero"]): row for row in rows}
        for section, number, name, _ in PENDING_SLOTS:
            row = by_slot.get((section, number))
            self.assertIsNotNone(row, f"No existe el hueco {section} {number}")
            self.assertEqual(row["nombre"], name)

    def test_running_it_again_changes_nothing(self) -> None:
        # Va detrás de `extraer_checklist.py`, que rehace el fichero desde el
        # PDF, así que se ejecuta una y otra vez sobre el mismo CSV.
        rows = self.rows()
        before = len(rows)

        self.assertEqual(fill_pending(rows), 0)
        self.assertEqual(add_latest_signings(rows), 0)
        self.assertEqual(add_bis(rows), 0)
        self.assertEqual(len(rows), before)

    def test_the_unnumbered_bis_have_no_slot(self) -> None:
        # Inventarles un hueco los colocaría donde no van, y el analizador los
        # trataría como variantes del mismo cromo.
        for row in self.rows():
            if row["numero"] != "BIS":
                continue
            self.assertEqual(row["hueco_album"], "")
            self.assertEqual(row["variante"], "BIS")
            self.assertTrue(row["nombre"].strip())

    def test_the_new_stickers_carry_the_edition(self) -> None:
        rows = self.rows()
        third = [row for row in rows if row["edicion"] == "3ed"]

        self.assertEqual(
            len(third), len(PENDING_SLOTS) + len(LATEST_SIGNINGS) + len(BIS_STICKERS)
        )

    def test_the_album_order_is_not_alphabetical(self) -> None:
        # El fichero va en el orden de las páginas del álbum: los equipos
        # primero y luego las secciones temáticas. Reordenarlo al insertar
        # cromos nuevos cambia la navegación, que es lo que se recorre cromo
        # a cromo delante del álbum de papel.
        rows = self.rows()
        sections: list[str] = []
        for row in rows:
            if row["seccion"] not in sections:
                sections.append(row["seccion"])

        self.assertEqual(sections[0], "DEPORTIVO ALAVÉS")
        self.assertEqual(sections[1], "ATHLETIC CLUB DE BILBAO")
        # Los equipos van delante y las secciones temáticas detrás.
        self.assertEqual(sections[-1], "EXTRA STICKER ORO")
        self.assertLess(
            sections.index("VILLARREAL"), sections.index("ÚLTIMOS FICHAJES")
        )
        self.assertNotEqual(sections, sorted(sections))
        # Cada sección aparece de una pieza, sin filas sueltas más abajo.
        self.assertEqual(len(sections), len(set(sections)))

    def test_the_new_stickers_go_inside_their_section(self) -> None:
        rows = self.rows()
        for row in rows:
            if row["edicion"] != EDITION:
                continue
            index = rows.index(row)
            neighbours = {rows[max(0, index - 1)]["seccion"], rows[min(len(rows) - 1, index + 1)]["seccion"]}
            self.assertIn(row["seccion"], neighbours)

    def test_the_fields_match_the_checklist(self) -> None:
        with Path("coleccion_panini.csv").open(encoding="utf-8-sig", newline="") as source:
            header = next(csv.reader(source))

        self.assertEqual(tuple(header), CSV_FIELDS)


if __name__ == "__main__":
    unittest.main()
