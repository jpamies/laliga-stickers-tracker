from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

import pymupdf

from extraer_checklist import (
    Entry,
    CLUB_SECTIONS,
    SPECIAL_SECTIONS,
    WITHDRAWN_MARKER,
    build_stickers,
    club_and_name,
    extract_lines,
    load_known_ids,
    parse_entries,
    parse_number,
    split_sections,
    write_csv,
)


ATHLETIC_LINES = [
    "13",
    "Unai Gómez",
    "medio",
    "13BIS",
    "Prados",
    "medio",
    "2ªed",
    "14",
    "Sancet",
    "medio",
]

LATEST_SIGNINGS_LINES = [
    "UF1",
    "CANALES (Racing de Santander)",
    "medio",
    "2ªed",
    "UF2",
    "CALATRAVA (Espanyol)",
    "medio",
    "2ªed",
]


class NumberParsingTests(unittest.TestCase):
    def test_splits_slot_and_variant(self) -> None:
        self.assertEqual(parse_number("13"), ("13", ""))
        self.assertEqual(parse_number("18A"), ("18", "A"))
        self.assertEqual(parse_number("13BIS"), ("13", "BIS"))
        self.assertEqual(parse_number("UF7"), ("7", ""))


class EntryParsingTests(unittest.TestCase):
    def test_marks_second_edition_after_the_position(self) -> None:
        entries = parse_entries("ATHLETIC CLUB DE BILBAO", ATHLETIC_LINES)

        self.assertEqual(
            entries,
            [
                Entry("13", "Unai Gómez", "medio", ""),
                Entry("13BIS", "Prados", "medio", "2ed"),
                Entry("14", "Sancet", "medio", ""),
            ],
        )

    def test_reads_club_from_the_name_of_special_sections(self) -> None:
        entries = parse_entries("ÚLTIMOS FICHAJES", LATEST_SIGNINGS_LINES)

        self.assertEqual([entry.numero for entry in entries], ["UF1", "UF2"])
        self.assertEqual(
            club_and_name("ÚLTIMOS FICHAJES", entries[0].nombre),
            ("Racing de Santander", "Canales"),
        )
        self.assertEqual(
            club_and_name("ÚLTIMOS FICHAJES", entries[1].nombre),
            ("RCD Espanyol", "Calatrava"),
        )


class ThirdEditionFormatTests(unittest.TestCase):
    """La tercera edición cambia cómo escribe los números y las ediciones, y
    cada uno de esos cambios rompió el extractor la primera vez."""

    def test_reads_the_variant_written_with_a_space(self) -> None:
        # El checklist de la tercera edición pone «8 BIS» donde el de la
        # segunda ponía «8BIS».
        entries = parse_entries(
            "DEPORTIVO ALAVÉS",
            ["8", "Parada", "defensa", "8 BIS", "Garcés", "defensa", "3ª ed"],
        )

        self.assertEqual(
            entries,
            [
                Entry("8", "Parada", "defensa", ""),
                Entry("8BIS", "Garcés", "defensa", "3ed"),
            ],
        )

    def test_reads_the_latest_signing_written_with_a_space(self) -> None:
        entries = parse_entries(
            "ÚLTIMOS FICHAJES",
            ["UF 21", "BERNARDO SILVA (R. Madrid)", "medio", "3ª ed"],
        )

        self.assertEqual(entries[0].numero, "UF21")
        self.assertEqual(entries[0].edicion, "3ed")

    def test_each_edition_keeps_its_own_mark(self) -> None:
        # Antes sólo existía «2ª ed» y se daba por supuesta; con tres ediciones
        # hay que leer el número, o los cromos nuevos pasarían por antiguos.
        entries = parse_entries(
            "SEVILLA",
            [
                "4", "Fran González", "portero", "3ª ed",
                "5", "Kike Salas", "defensa", "2ªed",
                "6", "Juanlu", "defensa",
            ],
        )

        self.assertEqual(
            [entry.edicion for entry in entries], ["3ed", "2ed", ""]
        )

    def test_the_abbreviated_clubs_resolve(self) -> None:
        # Últimos Fichajes abrevia el club, y sin traducirlo el cromo no
        # encuentra su plantilla.
        self.assertEqual(
            club_and_name("ÚLTIMOS FICHAJES", "BERNARDO SILVA (R. Madrid)"),
            ("Real Madrid", "Bernardo Silva"),
        )
        self.assertEqual(
            club_and_name("ÚLTIMOS FICHAJES", "IVÁN MARTÍN (Racing)"),
            ("Racing de Santander", "Iván Martín"),
        )


class FourthEditionTests(unittest.TestCase):
    def sections(self) -> dict[str, list[str]]:
        return {section: [] for section in CLUB_SECTIONS + SPECIAL_SECTIONS}

    def test_reads_fourth_edition_and_keeps_withdrawal_separate_from_action(self) -> None:
        sections = self.sections()
        sections["SEVILLA"] = [
            "14", WITHDRAWN_MARKER, "Sow", "medio",
            "14BIS", "Nico Guillén", "medio", "4ªed",
        ]
        old, new = build_stickers(sections)

        self.assertEqual(old.baja_panini, "true")
        self.assertEqual(old.accion, "PEGAR")
        self.assertEqual(new.edicion, "4ed")
        self.assertEqual(new.baja_panini, "")
        self.assertEqual(new.accion, "PEGAR")

    def test_repeated_bis_names_do_not_replace_the_original_sticker(self) -> None:
        sections = self.sections()
        sections["DEPORTIVO"] = [
            "14 BIS", "Gijselhat", "medio", "3ª ed",
            "14BIS", "Casadó", "medio", "4ªed",
        ]
        known = {("DEPORTIVO", "14BIS", 1): "DEPORTIVO-BIS-2"}
        old, new = build_stickers(sections, known)

        self.assertEqual((old.id, old.nombre), ("DEPORTIVO-BIS-2", "Gijselhart"))
        self.assertEqual((new.nombre, new.edicion), ("Casadó", "4ed"))
        self.assertNotEqual(old.id, new.id)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "previous.csv"
            write_csv([old, new], path)
            regenerated = build_stickers(sections, load_known_ids(path))
        self.assertEqual([sticker.id for sticker in regenerated], [old.id, new.id])

    def test_top_signings_reuse_the_published_placeholder_identifiers(self) -> None:
        sections = self.sections()
        sections["TOP FICHAJES"] = ["67", "Rodri", "medio", "4ªed"]
        sections["ÚLTIMOS FICHAJES"] = ["UF 60", "Romero", "defensa", "4ªed"]
        stickers = build_stickers(sections, load_known_ids(None))
        by_number = {sticker.numero: sticker for sticker in stickers}
        self.assertEqual(by_number["67"].id, "TOP-FICHAJES-67")
        self.assertEqual(by_number["67"].club_objetivo, "FC Barcelona")
        self.assertEqual(by_number["UF60"].id, "ULTIMOS-FICHAJES-60")
        self.assertEqual(by_number["UF60"].club_objetivo, "Atlético de Madrid")

    def test_unlabelled_signing_needs_a_verified_name_not_just_a_number(self) -> None:
        sections = self.sections()
        sections["ÚLTIMOS FICHAJES"] = ["UF60", "Otro Romero", "defensa", "4ªed"]
        with self.assertRaisesRegex(ValueError, "Falta comprobar el club"):
            build_stickers(sections)

    def test_top_heading_is_separate_and_optional_for_older_editions(self) -> None:
        lines = [*CLUB_SECTIONS, *(s for s in SPECIAL_SECTIONS if s != "TOP FICHAJES")]
        self.assertNotIn("TOP FICHAJES", split_sections(lines))
        sections = split_sections([*lines, "3 TOP FICHAJES", "67", "Rodri", "medio", "4ªed"])
        self.assertEqual(parse_entries("TOP FICHAJES", sections["TOP FICHAJES"])[0].numero, "67")

    def test_madrid_abbreviation_uses_the_canonical_club(self) -> None:
        self.assertEqual(
            club_and_name("EXTRA STICKER ORO", "Bellingham (Madrid)"),
            ("Real Madrid", "Bellingham"),
        )

    def test_separated_red_rectangles_do_not_mark_the_white_rows_between_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checklist.pdf"
            with pymupdf.open() as document:
                page = document.new_page()
                shape = page.new_shape()
                for baseline in (110, 170):
                    shape.draw_rect(pymupdf.Rect(20, baseline - 14, 270, baseline + 4))
                shape.finish(fill=(0.875, 0.412, 0.392), color=None)
                shape.commit()
                page.insert_text((20, 70), "DEPORTIVO")
                for number, name, baseline in ((1, "Baja", 110), (2, "Sigue", 140), (3, "Otra baja", 170)):
                    page.insert_text((30, baseline), str(number))
                    page.insert_text((90, baseline), name)
                    page.insert_text((220, baseline), "medio")
                document.save(path)
            lines = extract_lines(path)
        entries = parse_entries("DEPORTIVO", lines[1:])
        self.assertEqual([entry.baja_panini for entry in entries], [True, False, True])
        self.assertEqual([entry.nombre for entry in entries], ["Baja", "Sigue", "Otra baja"])


class IdentifierTests(unittest.TestCase):
    def _sections(self) -> dict[str, list[str]]:
        sections = {
            section: []
            for section in (
                "DEPORTIVO ALAVÉS",
                "ATHLETIC CLUB DE BILBAO",
                "ATLÉTICO DE MADRID",
                "FC BARCELONA",
                "REAL BETIS",
                "RC CELTA DE VIGO",
                "DEPORTIVO",
                "ELCHE CF",
                "RCD ESPANYOL",
                "GETAFE CF",
                "LEVANTE UD",
                "REAL MADRID CF",
                "MALAGA CF",
                "OSASUNA",
                "RACING DE SANTANDER",
                "RAYO VALLECANO",
                "REAL SOCIEDAD",
                "SEVILLA",
                "VALENCIA",
                "VILLARREAL",
                "ÚLTIMOS FICHAJES",
                "ADN / LALIGA PRIME",
                "LALIGA FANTASY",
                "DRAFT 23",
                "DRAFT 23 KROMIX",
                "EXTRA STICKER BRONCE",
                "EXTRA STICKER PLATA",
                "EXTRA STICKER ORO",
            )
        }
        sections["ATHLETIC CLUB DE BILBAO"] = ATHLETIC_LINES
        sections["ÚLTIMOS FICHAJES"] = LATEST_SIGNINGS_LINES
        return sections

    def test_reuses_published_identifiers_and_appends_new_ones(self) -> None:
        known = {
            ("ATHLETIC CLUB DE BILBAO", "13", 1): "ATHLETIC-CLUB-DE-BILBAO-14",
            ("ATHLETIC CLUB DE BILBAO", "14", 1): "ATHLETIC-CLUB-DE-BILBAO-15",
            ("ÚLTIMOS FICHAJES", "UF1", 1): "ULTIMOS-FICHAJES-01",
            ("ÚLTIMOS FICHAJES", "UF2", 1): "ULTIMOS-FICHAJES-02",
        }

        stickers = build_stickers(self._sections(), known)
        by_number = {
            sticker.numero: sticker
            for sticker in stickers
            if sticker.seccion in {"ATHLETIC CLUB DE BILBAO", "ÚLTIMOS FICHAJES"}
        }

        self.assertEqual(by_number["13"].id, "ATHLETIC-CLUB-DE-BILBAO-14")
        self.assertEqual(by_number["14"].id, "ATHLETIC-CLUB-DE-BILBAO-15")
        self.assertEqual(by_number["13BIS"].id, "ATHLETIC-CLUB-DE-BILBAO-01")
        self.assertEqual(by_number["13BIS"].variante, "BIS")
        self.assertEqual(by_number["13BIS"].edicion, "2ed")
        self.assertEqual(by_number["UF1"].id, "ULTIMOS-FICHAJES-01")
        self.assertEqual(by_number["UF1"].club_objetivo, "Racing de Santander")
        self.assertEqual(len({sticker.id for sticker in stickers}), len(stickers))

    def test_only_recommends_sticking_or_waiting(self) -> None:
        stickers = build_stickers(self._sections())

        self.assertTrue(
            {sticker.accion for sticker in stickers} <= {"PEGAR", "ESPERAR"}
        )


if __name__ == "__main__":
    unittest.main()
