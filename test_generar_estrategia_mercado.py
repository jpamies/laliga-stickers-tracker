from __future__ import annotations

import unittest
from datetime import date

from generar_estrategia_mercado import (
    Movement,
    SquadPlayer,
    departure_status,
    parse_besoccer_transfers,
    parse_squad_details,
    strategy_rows,
)


class MarketStrategyTests(unittest.TestCase):
    def test_parses_squad_name_and_position(self) -> None:
        html = """
        <table class="items"><tbody><tr><td class="posrela">
          <table class="inline-table">
            <tr><td class="hauptlink">
              <a href="/jugador/profil/spieler/1">Jugador Nuevo</a>
            </td></tr>
            <tr><td>Centrocampista</td></tr>
          </table>
        </td></tr></tbody></table>
        """
        self.assertEqual(
            [("Jugador Nuevo", "Centrocampista")],
            [(player.name, player.position) for player in parse_squad_details(html)],
        )

    def test_parses_besoccer_arrival_and_departure(self) -> None:
        html = """
        <div id="transfers-panel">
          <div class="panel-head"><h3 class="panel-title">Real Madrid</h3></div>
          <div class="panel-body"><table><tr>
            <td><div class="table-head">Alta</div><ul><li class="sign-list">
              <p class="pl-name">Jugador Alta</p><p class="date">20 AGO 2026</p>
              <div class="right-content"><div class="shield"><img alt="Club Origen"></div>
              <div class="data-transfer"><p>Fichaje.</p><p>5,0M.€</p></div></div>
            </li></ul></td>
            <td><div class="table-head">Baja</div><ul><li class="sign-list">
              <p class="pl-name">Jugador Baja</p><p class="date">21 AGO 2026</p>
              <div class="right-content"><div class="shield"><img alt="Club Destino"></div>
              <div class="data-transfer"><p>Cesión.</p></div></div>
            </li></ul></td>
          </tr></table></div>
        </div>
        """
        movements = parse_besoccer_transfers(html)
        self.assertEqual(2, len(movements))
        self.assertEqual(("ALTA", "Club Origen", "Fichaje", "5,0M.€"), (
            movements[0].direction,
            movements[0].other_club,
            movements[0].movement_type,
            movements[0].amount,
        ))
        self.assertEqual("CEDIDO", departure_status(movements[1]))

    def test_marks_sale_and_appends_current_player_without_sticker(self) -> None:
        physical = [
            {
                "id": "DEPORTIVO-ALAVES-08",
                "seccion": "DEPORTIVO ALAVÉS",
                "numero": "8",
                "hueco_album": "8",
                "variante": "",
                "nombre": "Parada",
                "tipo": "defensa",
                "club_objetivo": "Deportivo Alavés",
                "accion": "REVISAR",
                "notas": "",
            },
            {
                "id": "DEPORTIVO-ALAVES-09",
                "seccion": "DEPORTIVO ALAVÉS",
                "numero": "9",
                "hueco_album": "9",
                "variante": "",
                "nombre": "Antonio Sivera",
                "tipo": "portero",
                "club_objetivo": "Deportivo Alavés",
                "accion": "PEGAR",
                "notas": "",
            },
        ]
        squads = {
            "Deportivo Alavés": [
                SquadPlayer("Antonio Sivera", "Portero"),
                SquadPlayer("Nuevo Fichaje", "Delantero"),
            ]
        }
        movements = [
            Movement(
                club="Deportivo Alavés",
                direction="BAJA",
                player="V. Parada",
                other_club="Club Destino",
                movement_type="Fichaje",
                amount="2M.€",
                movement_date="20 AGO 2026",
                source_url="https://example.test/movimientos",
            ),
            Movement(
                club="Deportivo Alavés",
                direction="ALTA",
                player="Nuevo Fichaje",
                other_club="Club Origen",
                movement_type="Fichaje",
                amount="3M.€",
                movement_date="21 AGO 2026",
                source_url="https://example.test/movimientos",
            ),
        ]

        rows = strategy_rows(
            physical,
            squads,
            movements,
            {"DEPORTIVO-ALAVES-08": {"state": "owned", "copies": 2}},
            date(2026, 8, 26),
        )

        self.assertEqual("VENDIDO", rows[0]["estado_mercado"])
        self.assertEqual("Club Destino", rows[0]["club_destino"])
        self.assertEqual("OWNED", rows[0]["estado_coleccion"])
        self.assertEqual("2", rows[0]["copias"])
        self.assertEqual("EN_PLANTILLA", rows[1]["estado_mercado"])
        self.assertEqual("PLANTILLA_SIN_CROMO", rows[2]["tipo_registro"])
        self.assertEqual("FICHAJE_SIN_CROMO", rows[2]["estado_mercado"])
        self.assertEqual("Club Origen", rows[2]["club_origen"])


if __name__ == "__main__":
    unittest.main()
