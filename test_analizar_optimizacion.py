from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from analizar_optimizacion import (
    DEAD,
    PENDING,
    READY,
    REVIEW,
    Option,
    Slot,
    build_reports,
    generate,
)


def option(nombre: str, estado: str, numero: str = "5", variante: str = "") -> Option:
    return Option(
        numero=numero,
        nombre=nombre,
        variante=variante,
        edicion="",
        estado=estado,
        ficha=nombre,
        dorsal="7",
        posicion="Delantero",
    )


class SlotStateTests(unittest.TestCase):
    def test_one_active_variant_is_enough_to_solve_the_slot(self) -> None:
        slot = Slot("5", "delantero", [
            option("Se fue", "fuera_plantilla", "5A"),
            option("Sigue", "en_plantilla", "5B"),
        ])

        self.assertEqual(slot.state, READY)
        self.assertEqual(slot.pick.nombre, "Sigue")
        self.assertEqual(len(slot.active_options), 1)

    def test_slot_is_dead_when_every_variant_left(self) -> None:
        slot = Slot("5", "delantero", [
            option("Se fue", "fuera_plantilla", "5A"),
            option("También se fue", "fuera_plantilla", "5B"),
        ])

        self.assertEqual(slot.state, DEAD)
        self.assertIsNone(slot.pick)

    def test_doubtful_variant_needs_a_manual_check(self) -> None:
        slot = Slot("5", "delantero", [option("Quizá", "coincidencia_dudosa")])

        self.assertEqual(slot.state, REVIEW)

    def test_slot_without_a_published_name_is_pending(self) -> None:
        slot = Slot("5", "delantero", [option("", "pendiente_publicacion")])

        self.assertEqual(slot.state, PENDING)

    def test_the_crest_is_left_out_of_the_count(self) -> None:
        slot = Slot("1", "escudo", [option("Escudo", "no_aplica", "1")])

        self.assertEqual(slot.state, "no_aplica")


class TeamReportTests(unittest.TestCase):
    def _collection(self) -> list[dict[str, str]]:
        rows = [
            {
                "id": "BAR-01",
                "seccion": "FC BARCELONA",
                "numero": "1",
                "hueco_album": "1",
                "variante": "",
                "nombre": "Escudo",
                "tipo": "",
                "club_objetivo": "FC Barcelona",
                "edicion": "",
            }
        ]
        for slot in range(2, 21):
            rows.append(
                {
                    "id": f"BAR-{slot:02d}",
                    "seccion": "FC BARCELONA",
                    "numero": str(slot),
                    "hueco_album": str(slot),
                    "variante": "",
                    "nombre": f"Jugador {slot}",
                    "tipo": "delantero",
                    "club_objetivo": "FC Barcelona",
                    "edicion": "",
                }
            )
        rows.append(
            {
                "id": "UF-01",
                "seccion": "ÚLTIMOS FICHAJES",
                "numero": "UF1",
                "hueco_album": "1",
                "variante": "",
                "nombre": "Refuerzo",
                "tipo": "delantero",
                "club_objetivo": "FC Barcelona",
                "edicion": "2ed",
            }
        )
        return rows

    def _checks(self, gone: set[str]) -> dict[str, dict[str, str]]:
        checks = {
            "BAR-01": {"estado_laliga": "no_aplica"},
            "UF-01": {
                "estado_laliga": "en_plantilla",
                "coincidencia_laliga": "Refuerzo",
                "dorsal_laliga": "9",
            },
        }
        for slot in range(2, 21):
            sticker = f"BAR-{slot:02d}"
            checks[sticker] = {
                "estado_laliga": "fuera_plantilla" if sticker in gone else "en_plantilla",
                "coincidencia_laliga": f"Jugador {slot}",
                "dorsal_laliga": str(slot),
            }
        return checks

    def test_a_full_page_needs_no_signings(self) -> None:
        reports = build_reports(self._collection(), self._checks(set()), [])
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(barcelona.count(READY), 19)
        self.assertEqual(barcelona.count(DEAD), 0)
        self.assertEqual(barcelona.deficit, 0)
        self.assertIn("Página completa sin Últimos Fichajes", barcelona.verdict)

    def test_a_signing_covers_a_slot_whose_player_left(self) -> None:
        reports = build_reports(self._collection(), self._checks({"BAR-05"}), [])
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(barcelona.count(DEAD), 1)
        self.assertEqual(len(barcelona.active_signings), 1)
        self.assertEqual(barcelona.deficit, 0)
        self.assertIn("Huecos a resolver:** 5", "\n".join(barcelona.plan))

    def test_more_empty_slots_than_signings_leaves_a_deficit(self) -> None:
        gone = {"BAR-05", "BAR-06", "BAR-07"}
        reports = build_reports(self._collection(), self._checks(gone), [])
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(barcelona.count(DEAD), 3)
        self.assertEqual(barcelona.deficit, 2)
        self.assertIn("sin solución", barcelona.verdict)

    def test_squad_members_without_a_sticker_are_listed(self) -> None:
        squads = [
            {
                "seccion_album": "FC BARCELONA",
                "rol_slug": "jugador",
                "cromo_id": "",
                "dorsal": "30",
                "nombre": "Cantera Uno",
                "apodo": "Uno",
                "posicion": "Defensa",
            },
            {
                "seccion_album": "FC BARCELONA",
                "rol_slug": "jugador",
                "cromo_id": "BAR-05",
                "dorsal": "5",
                "nombre": "Jugador 5",
                "apodo": "Cinco",
                "posicion": "Defensa",
            },
            {
                "seccion_album": "FC BARCELONA",
                "rol_slug": "segundo-entrenador",
                "cromo_id": "",
                "dorsal": "",
                "nombre": "Ayudante",
                "apodo": "Ayudante",
                "posicion": "Segundo entrenador",
            },
        ]

        reports = build_reports(self._collection(), self._checks(set()), squads)
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(len(barcelona.without_sticker), 1)
        self.assertEqual(barcelona.without_sticker[0]["apodo"], "Uno")


class ReportFileTests(unittest.TestCase):
    def test_renders_every_club_from_the_real_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "informe.md"
            reports = generate(
                Path("coleccion_panini_revisada.csv"),
                Path("comprobacion_laliga.csv"),
                Path("laliga_plantillas.csv"),
                output,
                date(2026, 9, 2),
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(len(reports), 20)
        self.assertIn("# Optimización de plantilla por equipo", text)
        self.assertIn("## FC BARCELONA", text)
        self.assertIn("### Últimos Fichajes de este equipo", text)
        self.assertIn("### Condicional: plantilla de LALIGA sin cromo", text)
        # Cada club aporta 19 huecos comprobables más el escudo.
        for report in reports:
            self.assertEqual(len(report.player_slots), 19)
            self.assertEqual(len(report.slots), 20)


if __name__ == "__main__":
    unittest.main()
