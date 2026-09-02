from __future__ import annotations

import unittest

from comprobar_plantillas_laliga import (
    DOUBTFUL,
    IN_SQUAD,
    OUT_OF_SQUAD,
    SquadMember,
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

    def test_first_and_last_word_nickname_matches(self) -> None:
        match = match_member("Luiz Júnior", SQUAD)

        self.assertEqual(match.estado, IN_SQUAD)
        self.assertEqual(match.candidato, "Luiz Lúcio Reis Júnior")

    def test_missing_player_is_reported_as_gone(self) -> None:
        match = match_member("Ferran Torres", SQUAD)

        self.assertEqual(match.estado, OUT_OF_SQUAD)
        self.assertLess(match.confianza, 0.68)

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
        squads = load_squads(__import__("pathlib").Path("laliga_plantillas.csv"))

        self.assertEqual(len(squads), 20)
        self.assertIn("FC BARCELONA", squads)
        self.assertTrue(all(squad for squad in squads.values()))
        self.assertTrue(
            all(member.keys for squad in squads.values() for member in squad)
        )


if __name__ == "__main__":
    unittest.main()
