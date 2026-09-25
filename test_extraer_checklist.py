from __future__ import annotations

import unittest

from extraer_checklist import (
    Entry,
    build_stickers,
    club_and_name,
    parse_entries,
    parse_number,
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
