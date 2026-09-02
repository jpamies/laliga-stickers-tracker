from __future__ import annotations

import unittest
from pathlib import Path

from comprobar_plantillas import normalize_name

from comprobar_plantillas_laliga import (
    DOUBTFUL,
    IN_SQUAD,
    OUT_OF_SQUAD,
    SquadMember,
    link_stickers,
    load_squads,
    match_member,
    member_keys,
)


def member(nombre: str, apodo: str = "", nombre_pila: str = "", apellidos: str = "") -> SquadMember:
    row = {
        "nombre": nombre,
        "apodo": apodo,
        "nombre_pila": nombre_pila,
        "apellidos": apellidos,
        "dorsal": "9",
        "posicion": "Delantero",
    }
    return SquadMember(
        clave=f"equipo-{normalize_name(nombre).replace(' ', '-')}",
        nombre=nombre,
        apodo=apodo,
        dorsal="9",
        posicion="Delantero",
        keys=member_keys(row),
    )


SQUAD = [
    member("Vinícius José Paixão de Oliveira Júnior", "Vini Jr.", "Vinícius", "José Paixão de Oliveira Júnior"),
    member("Fermín López", "Fermin", "Fermín", "López"),
    member("Luiz Lúcio Reis Júnior", "Luiz Júnior", "Luiz", "Lúcio Reis Júnior"),
    member("Iñaki Williams", "Williams", "Iñaki", "Williams"),
    member("Nico Williams", "Nico Williams", "Nico", "Williams"),
]


class MemberKeyTests(unittest.TestCase):
    def test_long_names_also_index_first_and_last_word(self) -> None:
        keys = member_keys(
            {
                "nombre": "Luiz Lúcio Reis Júnior",
                "apodo": "",
                "nombre_pila": "",
                "apellidos": "",
            }
        )

        self.assertIn("luiz lucio reis junior", keys)
        self.assertIn("luiz junior", keys)


class MatchTests(unittest.TestCase):
    def test_short_printed_name_matches_the_full_legal_name(self) -> None:
        match = match_member("Vinícius", SQUAD)

        self.assertEqual(match.estado, IN_SQUAD)
        self.assertEqual(match.candidato, "Vinícius José Paixão de Oliveira Júnior")
        self.assertTrue(match.clave)

    def test_first_and_last_word_nickname_matches(self) -> None:
        match = match_member("Luiz Júnior", SQUAD)

        self.assertEqual(match.estado, IN_SQUAD)
        self.assertEqual(match.candidato, "Luiz Lúcio Reis Júnior")

    def test_missing_player_is_reported_as_gone(self) -> None:
        match = match_member("Ferran Torres", SQUAD)

        self.assertEqual(match.estado, OUT_OF_SQUAD)
        self.assertLess(match.confianza, 0.68)
        # Sin ficha oficial no hay clave con la que enlazar el cromo.
        self.assertEqual(match.clave, "")

    def test_ambiguous_surname_is_never_reported_as_gone(self) -> None:
        match = match_member("Williams", SQUAD)

        self.assertEqual(match.estado, DOUBTFUL)
        self.assertIn("Iñaki Williams", match.candidato)
        self.assertIn("Nico Williams", match.candidato)

    def test_very_short_nicknames_are_never_reported_as_gone(self) -> None:
        # «Oso» o «Yusi» se parecen a demasiados nombres para descartarlos.
        match = match_member("Oso", SQUAD)

        self.assertEqual(match.estado, DOUBTFUL)


class SquadLoadingTests(unittest.TestCase):
    def test_reads_the_generated_squads_grouped_by_album_section(self) -> None:
        rows, squads = load_squads(Path("laliga_plantillas.csv"))

        self.assertEqual(len(squads), 20)
        self.assertIn("FC BARCELONA", squads)
        self.assertEqual(len(rows), sum(len(squad) for squad in squads.values()))
        self.assertTrue(all(squad for squad in squads.values()))
        self.assertTrue(
            all(member.keys and member.clave for squad in squads.values() for member in squad)
        )


class ReverseIndexTests(unittest.TestCase):
    def _result(self, sticker_id: str, section: str, numero: str, clave: str) -> dict[str, str]:
        return {
            "id": sticker_id,
            "seccion": section,
            "numero": numero,
            "nombre": "Jugador",
            "clave_laliga": clave,
        }

    def test_links_the_club_sticker_before_the_latest_signing_one(self) -> None:
        squad_rows = [{"clave": "equipo-1"}, {"clave": "equipo-2"}]
        results = [
            self._result("UF-01", "ÚLTIMOS FICHAJES", "UF1", "equipo-1"),
            self._result("BAR-05", "FC BARCELONA", "5", "equipo-1"),
            self._result("UF-02", "ÚLTIMOS FICHAJES", "UF2", "equipo-2"),
        ]

        linked = link_stickers(squad_rows, results)

        self.assertEqual(linked[0]["cromo_id"], "BAR-05")
        self.assertEqual(linked[0]["cromo_seccion"], "FC BARCELONA")
        self.assertEqual(
            linked[0]["cromos"], "FC BARCELONA 5; ÚLTIMOS FICHAJES UF1"
        )
        self.assertEqual(linked[1]["cromo_id"], "UF-02")
        self.assertEqual(linked[1]["cromo_numero"], "UF2")

    def test_ignores_themed_sections_and_unmatched_stickers(self) -> None:
        squad_rows = [{"clave": "equipo-1"}, {"clave": "equipo-2"}]
        results = [
            self._result("ADN-01", "ADN / LALIGA PRIME", "1", "equipo-1"),
            self._result("D23-01", "DRAFT 23", "1", "equipo-1"),
            self._result("LF-01", "LALIGA FANTASY", "1", "equipo-1"),
            self._result("ORO-01", "EXTRA STICKER ORO", "1", "equipo-1"),
            self._result("BAR-09", "FC BARCELONA", "9", ""),
        ]

        linked = link_stickers(squad_rows, results)

        self.assertTrue(all(not row["cromo_id"] for row in linked))
        self.assertTrue(all(not row["cromos"] for row in linked))


if __name__ == "__main__":
    unittest.main()
