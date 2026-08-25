from __future__ import annotations

import unittest

from comprobar_plantillas import match_player, parse_squad


class SquadParsingTests(unittest.TestCase):
    def test_parse_squad_extracts_unique_player_names(self) -> None:
        html = """
        <table class="items"><tbody>
          <tr class="odd"><td class="hauptlink">
            <a title="Kylian Mbappé" href="/kylian-mbappe/profil/spieler/342229">
              Kylian Mbappé
            </a>
          </td></tr>
          <tr class="even"><td class="hauptlink">
            <a title="Vinicius Junior" href="/vinicius/profil/spieler/371998">
              Vinicius Junior
            </a>
          </td></tr>
        </tbody></table>
        """

        self.assertEqual(
            parse_squad(html),
            ["Kylian Mbappé", "Vinicius Junior"],
        )

    def test_alias_matches_full_transfermarkt_name(self) -> None:
        match = match_player("Vinícius", ["Vinicius Junior", "Kylian Mbappé"])

        self.assertEqual(match.action, "PEGAR")
        self.assertEqual(match.candidate, "Vinicius Junior")

    def test_clear_absence_is_marked_do_not_stick(self) -> None:
        match = match_player("Jugador Ausente", ["Kylian Mbappé", "Pedri"])

        self.assertEqual(match.action, "NO PEGAR")

    def test_doubtful_match_requires_review(self) -> None:
        match = match_player(
            "García",
            ["Raúl García de Haro", "Rubén García", "Pedri"],
        )

        self.assertEqual(match.action, "REVISAR")


if __name__ == "__main__":
    unittest.main()
