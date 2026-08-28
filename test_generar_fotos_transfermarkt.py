from __future__ import annotations

import unittest

from generar_fotos_transfermarkt import normalize_name, parse_squad_photos

SQUAD_HTML = """
<html><body>
<h1>Elche CF</h1>
<table class="items"><tbody>
  <tr>
    <td class="zentriert"><div class="rn_nummer">9</div></td>
    <td class="posrela">
      <table class="inline-table">
        <tr>
          <td rowspan="2">
            <img src="data:image/gif;base64,AAA"
                 data-src="https://img.a.transfermarkt.technology/portrait/medium/618801-1731931020.jpg?lm=4711"
                 class="bilderrahmen-fixed lazy" />
          </td>
          <td class="hauptlink">
            <a href="/alejandro-iturbe/profil/spieler/618801" title="Alejandro Iturbe">Alejandro Iturbe</a>
          </td>
        </tr>
        <tr><td>Delantero centro</td></tr>
      </table>
    </td>
  </tr>
  <tr>
    <td class="posrela">
      <table class="inline-table">
        <tr>
          <td rowspan="2">
            <img src="data:image/gif;base64,AAA"
                 data-src="https://img.a.transfermarkt.technology/portrait/medium/618801-1731931020.jpg"
                 class="bilderrahmen-fixed lazy" />
          </td>
          <td class="hauptlink">
            <a href="/alejandro-iturbe/profil/spieler/618801" title="Alejandro Iturbe">Alejandro Iturbe</a>
          </td>
        </tr>
        <tr><td>Delantero centro</td></tr>
      </table>
    </td>
  </tr>
</tbody></table>
</body></html>
"""


class PlayerPhotoTests(unittest.TestCase):
    def test_normalizes_names_without_accents_or_symbols(self) -> None:
        self.assertEqual(normalize_name("Youssef Enríquez"), "youssef enriquez")
        self.assertEqual(normalize_name("  Jonny  Otto "), "jonny otto")

    def test_extracts_club_and_players_without_duplicates(self) -> None:
        club, players = parse_squad_photos(SQUAD_HTML)

        self.assertEqual(club, "Elche CF")
        self.assertEqual(len(players), 1)
        player = players[0]
        self.assertEqual(player["jugador"], "Alejandro Iturbe")
        self.assertEqual(player["jugador_normalizado"], "alejandro iturbe")
        self.assertEqual(player["dorsal"], "9")
        self.assertEqual(player["posicion"], "Delantero centro")
        self.assertEqual(
            player["foto_url"],
            "https://img.a.transfermarkt.technology/portrait/medium/618801-1731931020.jpg",
        )


    def test_ignores_generic_transfermarkt_placeholder_photo(self) -> None:
        html = SQUAD_HTML.replace(
            "https://img.a.transfermarkt.technology/portrait/medium/618801-1731931020.jpg?lm=4711",
            "https://img.a.transfermarkt.technology/portrait/medium/default.jpg?lm=4711",
        )
        _, players = parse_squad_photos(html)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["foto_url"], "")


if __name__ == "__main__":
    unittest.main()
