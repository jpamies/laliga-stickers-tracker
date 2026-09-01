from __future__ import annotations

import unittest

from generar_plantillas_laliga import (
    PLAYER_FIELDS,
    TEAM_FIELDS,
    insert_statements,
    player_row,
    sql_literal,
    team_row,
)


TEAM = {
    "id": 4,
    "slug": "fc-barcelona",
    "name": "Fútbol Club Barcelona",
    "nickname": "FC Barcelona",
    "shortname": "BAR",
    "color": "#0f39b8",
    "color_secondary": "#bc161c",
    "venue": {"name": "Spotify Camp Nou"},
    "shield": {
        "url": "https://assets.laliga.com/x/large/barcelona.png",
        "resizes": {"medium": "https://assets.laliga.com/x/medium/barcelona.png"},
    },
}

MEMBER = {
    "id": 84308,
    "shirt_number": 1,
    "current": True,
    "loan": False,
    "loan_to": False,
    "position": {"name": "Portero", "slug": "portero"},
    "role": {"name": "Jugador", "slug": "jugador"},
    "person": {
        "id": 15102,
        "name": "Joan García",
        "nickname": "Joan Garcia",
        "firstname": "Joan",
        "lastname": "García",
        "date_of_birth": "2001-05-04T00:00:00+00:00",
        "place_of_birth": "Sallent",
        "weight": 85,
        "height": 193,
        "international": False,
        "country": {"id": "ES"},
    },
    "photos": {
        "001": {
            "512x556": "https://assets.laliga.com/p/512x556/p.png",
            "1024x1113": "https://assets.laliga.com/p/1024x1113/p.png",
        },
        "002": {"512x512": "https://assets.laliga.com/p/512x512/p.jpg"},
    },
    "opta_id": "p449928",
}


class RowMappingTests(unittest.TestCase):
    def test_team_row_keeps_album_section_and_medium_crest(self) -> None:
        row = team_row(TEAM, 2026)

        self.assertEqual(set(row), set(TEAM_FIELDS))
        self.assertEqual(row["seccion_album"], "FC BARCELONA")
        self.assertEqual(
            row["escudo_url"], "https://assets.laliga.com/x/medium/barcelona.png"
        )
        self.assertEqual(row["estadio"], "Spotify Camp Nou")

    def test_player_row_flattens_every_useful_field(self) -> None:
        row = player_row(MEMBER, TEAM, 2026)

        self.assertEqual(set(row), set(PLAYER_FIELDS))
        self.assertEqual(row["squad_id"], 84308)
        self.assertEqual(row["dorsal"], 1)
        self.assertEqual(row["fecha_nacimiento"], "2001-05-04")
        self.assertEqual(row["posicion_slug"], "portero")
        self.assertEqual(row["pais"], "ES")
        self.assertEqual(row["altura_cm"], 193)
        self.assertEqual(row["activo"], "true")
        self.assertEqual(row["cedido"], "false")
        self.assertEqual(row["foto_url"], "https://assets.laliga.com/p/512x556/p.png")
        self.assertEqual(
            row["foto_cuadrada_url"], "https://assets.laliga.com/p/512x512/p.jpg"
        )

    def test_missing_shirt_number_becomes_null(self) -> None:
        row = player_row({**MEMBER, "shirt_number": None}, TEAM, 2026)

        self.assertEqual(row["dorsal"], "")
        self.assertEqual(sql_literal(row["dorsal"], "dorsal"), "null")


class SqlTests(unittest.TestCase):
    def test_quotes_text_and_escapes_apostrophes(self) -> None:
        self.assertEqual(sql_literal("O'Neill", "nombre"), "'O''Neill'")
        self.assertEqual(sql_literal("", "nombre"), "null")
        self.assertEqual(sql_literal(193, "altura_cm"), "193")
        self.assertEqual(sql_literal("no-numero", "altura_cm"), "null")
        self.assertEqual(sql_literal("true", "activo"), "true")
        self.assertEqual(sql_literal("false", "activo"), "false")

    def test_inserts_are_batched(self) -> None:
        rows = [{"squad_id": index, "nombre": "x"} for index in range(5)]

        statements = insert_statements(rows, ["squad_id", "nombre"], "public.t", chunk=2)

        self.assertEqual(len(statements), 3)
        self.assertTrue(
            statements[0].startswith("insert into public.t (squad_id, nombre) values")
        )
        self.assertTrue(statements[-1].endswith(";"))
        self.assertIn("(4, 'x')", statements[-1])


if __name__ == "__main__":
    unittest.main()
