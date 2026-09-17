from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from generar_estadisticas_laliga import (
    CSV_FIELDS,
    as_number,
    fetch_stats,
    fetch_team_games,
    player_row,
)


MIEMBRO = {
    "clave": "fc-barcelona-84308",
    "slug": "j-garcia",
    "seccion_album": "FC BARCELONA",
    "equipo": "FC Barcelona",
    "nombre": "Joan García",
    "apodo": "Joan Garcia",
    "dorsal": "1",
    "posicion": "Portero",
    "cromo_id": "FC-BARCELONA-03",
    "cromos": "FC BARCELONA 3",
}


class CacheReadingTests(unittest.TestCase):
    """La descarga se cachea, así que basta con leer lo que hay en disco."""

    def _cache(self, directory: str, nombre: str, payload: object) -> Path:
        cache = Path(directory)
        (cache / nombre).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return cache

    def test_reads_the_tracked_metrics(self) -> None:
        payload = {
            "player_stats": {
                "stats": [
                    {"name": "time_played", "stat": 495},
                    {"name": "appearances", "stat": 6},
                    {"name": "starts", "stat": 6},
                    {"name": "goals", "stat": 2},
                    {"name": "team_games_played", "stat": 6},
                    {"name": "unsuccessful_short_passes", "stat": 1},
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            cache = self._cache(directory, "stats_j-garcia.json", payload)
            stats = fetch_stats(None, "j-garcia", cache, refresh=False)

        self.assertEqual(stats["minutos"], 495)
        self.assertEqual(stats["partidos"], 6)
        self.assertEqual(stats["goles"], 2)
        # Las métricas de detalle no se arrastran.
        self.assertNotIn("unsuccessful_short_passes", stats)

    def test_an_empty_answer_means_the_player_never_played(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = self._cache(directory, "stats_e-militao.json", {})
            stats = fetch_stats(None, "e-militao", cache, refresh=False)

        self.assertEqual(stats, {})
        self.assertIsNotNone(stats)

    def test_a_missing_player_is_not_the_same_as_one_without_minutes(self) -> None:
        # LALIGA responde 404 cuando el slug no existe, y `{}` cuando existe
        # pero no ha jugado: darlos por iguales inventaría un dato.
        with tempfile.TemporaryDirectory() as directory:
            cache = self._cache(
                directory, "stats_nadie.json", {"no_encontrado": True}
            )
            self.assertIsNone(fetch_stats(None, "nadie", cache, refresh=False))

    def test_reads_the_games_the_team_has_played(self) -> None:
        payload = {
            "team_stats": {
                "stats": [
                    {"name": "points", "stat": 7},
                    {"name": "games_played", "stat": 6},
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            cache = self._cache(directory, "teamstats_athletic-club.json", payload)
            self.assertEqual(
                fetch_team_games(None, "athletic-club", cache, refresh=False), 6
            )


class RowTests(unittest.TestCase):
    def test_every_column_is_filled(self) -> None:
        row = player_row(MIEMBRO, {"minutos": 495, "partidos_equipo": 6}, 6, "2026-09-17")

        self.assertEqual(set(row), set(CSV_FIELDS))
        self.assertEqual(row["minutos"], 495)
        self.assertEqual(row["minutos_por_partido_equipo"], "82.5")

    def test_a_player_without_minutes_still_gets_the_team_games(self) -> None:
        # Sin ese dato no se podría comparar a quien no juega con quien sí.
        row = player_row(MIEMBRO, {}, 6, "2026-09-17")

        self.assertEqual(row["minutos"], 0)
        self.assertEqual(row["partidos_equipo"], 6)
        self.assertEqual(row["minutos_por_partido_equipo"], "0.0")

    def test_a_player_that_could_not_be_found_leaves_the_columns_empty(self) -> None:
        row = player_row(MIEMBRO, None, 6, "2026-09-17")

        self.assertEqual(row["minutos"], "")
        self.assertEqual(row["partidos_equipo"], "")


class NumberTests(unittest.TestCase):
    def test_reads_whatever_the_api_sends(self) -> None:
        self.assertEqual(as_number("495"), 495)
        self.assertEqual(as_number(495.0), 495)
        self.assertEqual(as_number(None), 0)
        self.assertEqual(as_number("—"), 0)


if __name__ == "__main__":
    unittest.main()
