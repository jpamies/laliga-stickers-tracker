from __future__ import annotations

import re
import unittest
from pathlib import Path

from generar_plantillas_laliga import PLAYER_FIELDS, PLAYER_TABLE, TEAM_FIELDS, TEAM_TABLE


MIGRATIONS = Path("supabase/migrations")


def bare_name(table: str) -> str:
    return table.split(".")[-1]


def columns_in_migrations(table: str) -> set[str]:
    """Columnas que tendría la tabla tras aplicar todas las migraciones.

    Se leen en orden de fichero, que es el orden en que Supabase las aplica."""
    name = bare_name(table)
    columns: set[str] = set()
    for path in sorted(MIGRATIONS.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")

        if re.search(rf"drop table if exists\s+\S*{name}\b", sql):
            columns.clear()

        create = re.search(
            rf"create table (?:if not exists )?\S*{name} \((.*?)\n\);",
            sql,
            flags=re.DOTALL,
        )
        if create:
            for line in create.group(1).splitlines():
                line = line.strip()
                if not line or line.startswith("--") or line.startswith("constraint"):
                    continue
                columns.add(line.split()[0])

        for block in re.findall(
            rf"alter table \S*{name}\s+(.*?);", sql, flags=re.DOTALL
        ):
            for added in re.findall(
                r"add column (?:if not exists )?(\w+)", block
            ):
                columns.add(added)
    return columns


class MigrationCoverageTests(unittest.TestCase):
    """El volcado SQL inserta por nombre de columna, así que basta con que una
    falte en las migraciones para que la importación entera falle."""

    def test_every_generated_squad_column_exists(self) -> None:
        missing = set(PLAYER_FIELDS) - columns_in_migrations(PLAYER_TABLE)

        self.assertEqual(missing, set(), f"faltan columnas en {PLAYER_TABLE}")

    def test_every_generated_team_column_exists(self) -> None:
        missing = set(TEAM_FIELDS) - columns_in_migrations(TEAM_TABLE)

        self.assertEqual(missing, set(), f"faltan columnas en {TEAM_TABLE}")

    def test_the_dump_only_inserts_columns_the_tables_have(self) -> None:
        sql = Path("supabase/laliga_plantillas.sql").read_text(encoding="utf-8")

        for table in (PLAYER_TABLE, TEAM_TABLE):
            known = columns_in_migrations(table)
            for columns in re.findall(
                rf"insert into {re.escape(table)} \(([^)]+)\) values", sql
            ):
                with self.subTest(table=table):
                    self.assertEqual(
                        set(columns.split(", ")) - known,
                        set(),
                        f"el volcado inserta columnas que {table} no tiene",
                    )


if __name__ == "__main__":
    unittest.main()
