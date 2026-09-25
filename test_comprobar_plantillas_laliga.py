from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from comprobar_plantillas import normalize_name

from comprobar_plantillas_laliga import (
    AT_THE_CLUB,
    DOUBTFUL,
    IN_SQUAD,
    KNOWN_ABSENCES,
    KNOWN_UNLISTED,
    OUT_OF_SQUAD,
    UNLISTED,
    SquadMember,
    check_rows,
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
    member("Youssef Enriquez", "Youssef", "Youssef", "Enriquez"),
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

    def test_an_ambiguous_surname_is_settled_by_its_alias(self) -> None:
        # El cromo 19 del Athletic dice «Williams» a secas y en la plantilla
        # hay dos. El alias dice a cuál se refiere; antes se descartaba por
        # ambiguo sin llegar a mirarlo.
        match = match_member("Williams", SQUAD)

        self.assertEqual(match.estado, IN_SQUAD)
        self.assertEqual(match.candidato, "Iñaki Williams")

    def test_very_short_nicknames_are_never_reported_as_gone(self) -> None:
        # «Oso» o «Yusi» se parecen a demasiados nombres para descartarlos.
        match = match_member("Oso", SQUAD)

        self.assertEqual(match.estado, DOUBTFUL)

    def test_known_alias_rescues_a_nickname_laliga_does_not_print(self) -> None:
        # El cromo del Alavés dice «Yusi» y LALIGA «Youssef Enriquez».
        match = match_member("Yusi", SQUAD)

        self.assertEqual(match.estado, IN_SQUAD)
        self.assertEqual(match.candidato, "Youssef Enriquez")

    def test_alias_links_names_that_share_nothing(self) -> None:
        # El cromo 11 del Alavés lleva impreso «Benavidez» y el jugador es
        # Carlos Protesoni: sin el alias no hay una sola letra que los una.
        squad = [
            member("Carlos Protesoni", "C. Protesoni", "Carlos", "Protesoni"),
            member("Izei Hernández", "Izei", "Izei", "Hernández"),
        ]

        match = match_member("Benavidez", squad)

        self.assertEqual(match.estado, IN_SQUAD)
        self.assertEqual(match.candidato, "Carlos Protesoni")


    def test_an_ambiguous_name_without_an_alias_stays_doubtful(self) -> None:
        # Sin alias que lo resuelva, dos candidatos siguen siendo dos: no se
        # elige uno al azar ni se da por perdido el cromo.
        squad = [
            member("Mikel Rodríguez", "Mikel R.", "Mikel", "Rodríguez"),
            member("Miguel Rodríguez", "Miguel", "Miguel", "Rodríguez"),
        ]

        match = match_member("Rodríguez", squad)

        self.assertEqual(match.estado, DOUBTFUL)
        self.assertIn("Mikel Rodríguez", match.candidato)
        self.assertIn("Miguel Rodríguez", match.candidato)

    def test_a_nickname_reaches_the_civil_name(self) -> None:
        # LALIGA inscribe a Ximo Navarro como Joaquín Navarro Jiménez, y el
        # parecido entre los dos textos se queda por debajo del umbral.
        squad = [
            member(
                "Joaquín Navarro Jiménez", "X. Navarro", "Joaquín", "Navarro"
            ),
        ]

        match = match_member("Ximo Navarro", squad)

        self.assertEqual(match.estado, IN_SQUAD)
        self.assertEqual(match.candidato, "Joaquín Navarro Jiménez")


class ManualVerdictTests(unittest.TestCase):
    """Hay dos motivos distintos para no encontrar a alguien en LALIGA, y sólo
    uno significa que se haya ido del club."""

    def _fila(self, club: str, nombre: str) -> dict[str, str]:
        return {
            "id": "X-01", "seccion": "SECCION", "numero": "1",
            "nombre": nombre, "club_objetivo": club,
        }

    def test_a_confirmed_departure_is_reported_as_gone(self) -> None:
        club, nombre = next(iter(KNOWN_ABSENCES))

        [row] = check_rows([self._fila(club, nombre)], {}, date(2026, 9, 9))

        self.assertEqual(row["estado_laliga"], OUT_OF_SQUAD)

    def test_a_player_without_a_licence_still_counts_as_at_the_club(self) -> None:
        club, nombre = next(iter(KNOWN_UNLISTED))

        [row] = check_rows([self._fila(club, nombre)], {}, date(2026, 9, 9))

        self.assertEqual(row["estado_laliga"], UNLISTED)
        self.assertIn(UNLISTED, AT_THE_CLUB)
        self.assertNotIn(OUT_OF_SQUAD, AT_THE_CLUB)

    def test_a_shared_surname_is_not_enough_to_claim_the_same_player(self) -> None:
        # «Mario García» no es «Pablo García» sólo por compartir apellido.
        squad = [member("Pablo García", "Pablo G.", "Pablo", "García")]

        match = match_member("Mario García", squad)

        self.assertNotEqual(match.estado, IN_SQUAD)

    def test_abbreviations_and_typos_still_match(self) -> None:
        squad = [
            member("Rodrigo Mendoza", "Rodrigo", "Rodrigo", "Mendoza"),
            member("Adrià Alti", "Alti", "Adrià", "Alti"),
            member("Juan Francisco Funes Arjona", "Funes", "Juan Francisco", "Funes Arjona"),
        ]

        for printed, expected in [
            ("Rodri Mendoza", "Rodrigo Mendoza"),
            ("Adrià Altimira", "Adrià Alti"),
            ("Juan Franisco Funes", "Juan Francisco Funes Arjona"),
        ]:
            with self.subTest(printed=printed):
                match = match_member(printed, squad)
                self.assertEqual(match.estado, IN_SQUAD)
                self.assertEqual(match.candidato, expected)


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
