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
    Stats,
    build_reports,
    generate,
)


def option(
    nombre: str,
    estado: str,
    numero: str = "5",
    minutos: int = 0,
    partidos_equipo: int = 6,
) -> Option:
    return Option(
        numero=numero,
        nombre=nombre,
        variante="",
        edicion="",
        estado=estado,
        ficha=nombre,
        dorsal="7",
        posicion="Delantero",
        stats=Stats(
            minutos=minutos,
            partidos=minutos // 90,
            partidos_equipo=partidos_equipo,
        ),
    )


class StatsTests(unittest.TestCase):
    def test_share_is_measured_against_the_minutes_the_team_played(self) -> None:
        self.assertAlmostEqual(Stats(minutos=270, partidos_equipo=6).share, 0.5)
        self.assertEqual(Stats(minutos=0, partidos_equipo=6).share, 0.0)

    def test_a_regular_starter_deserves_a_sticker(self) -> None:
        self.assertTrue(Stats(minutos=450, partidos_equipo=6).important)
        self.assertFalse(Stats(minutos=30, partidos_equipo=6).important)

    def test_never_played_reads_differently_from_no_data(self) -> None:
        # Ambos suman cero minutos, pero sólo uno es un hecho comprobado.
        self.assertEqual(
            Stats(minutos=0, partidos_equipo=6).summary(), "0′ · no ha jugado"
        )
        self.assertEqual(Stats().summary(), "—")


class SlotStateTests(unittest.TestCase):
    def test_one_active_variant_is_enough_to_solve_the_slot(self) -> None:
        slot = Slot("5", "delantero", [
            option("Se fue", "fuera_plantilla", "5A"),
            option("Sigue", "en_plantilla", "5B", minutos=200),
        ])

        self.assertEqual(slot.state, READY)
        self.assertEqual(slot.pick.nombre, "Sigue")
        self.assertFalse(slot.is_choice)

    def test_slot_is_dead_when_every_variant_left(self) -> None:
        slot = Slot("5", "delantero", [
            option("Se fue", "fuera_plantilla", "5A"),
            option("También se fue", "fuera_plantilla", "5B"),
        ])

        self.assertEqual(slot.state, DEAD)
        self.assertIsNone(slot.pick)

    def test_a_player_without_a_licence_still_fills_the_slot(self) -> None:
        slot = Slot("5", "delantero", [option("Lesionado", "sin_ficha")])

        self.assertEqual(slot.state, READY)

    def test_doubtful_variant_needs_a_manual_check(self) -> None:
        slot = Slot("5", "delantero", [option("Quizá", "coincidencia_dudosa")])

        self.assertEqual(slot.state, REVIEW)

    def test_slot_without_a_published_name_is_pending(self) -> None:
        slot = Slot("5", "delantero", [option("", "pendiente_publicacion")])

        self.assertEqual(slot.state, PENDING)

    def test_the_crest_is_left_out_of_the_count(self) -> None:
        slot = Slot("1", "escudo", [option("Escudo", "no_aplica", "1")])

        self.assertEqual(slot.state, "no_aplica")


class VariantChoiceTests(unittest.TestCase):
    """Con dos jugadores en plantilla sólo se pega uno, y quien acumula
    minutos envejece mejor en el álbum."""

    def test_the_one_who_plays_is_recommended(self) -> None:
        slot = Slot("5", "delantero", [
            option("Suplente", "en_plantilla", "5A", minutos=30),
            option("Titular", "en_plantilla", "5B", minutos=480),
        ])

        self.assertTrue(slot.is_choice)
        self.assertTrue(slot.decided_by_minutes)
        self.assertEqual(slot.pick.nombre, "Titular")

    def test_someone_who_never_played_loses_against_anyone_who_did(self) -> None:
        slot = Slot("5", "delantero", [
            option("Nunca juega", "en_plantilla", "5A", minutos=0),
            option("Algo juega", "en_plantilla", "5B", minutos=45),
        ])

        self.assertTrue(slot.decided_by_minutes)
        self.assertEqual(slot.pick.nombre, "Algo juega")

    def test_two_regulars_leave_the_choice_open(self) -> None:
        slot = Slot("5", "delantero", [
            option("Uno", "en_plantilla", "5A", minutos=400),
            option("Otro", "en_plantilla", "5B", minutos=380),
        ])

        self.assertTrue(slot.is_choice)
        self.assertFalse(slot.decided_by_minutes)

    def test_two_players_without_minutes_cannot_be_ranked(self) -> None:
        slot = Slot("5", "delantero", [
            option("Uno", "en_plantilla", "5A", minutos=0),
            option("Otro", "en_plantilla", "5B", minutos=0),
        ])

        self.assertFalse(slot.decided_by_minutes)


class TeamReportTests(unittest.TestCase):
    def _collection(self) -> list[dict[str, str]]:
        rows = [
            {
                "id": "BAR-01", "seccion": "FC BARCELONA", "numero": "1",
                "hueco_album": "1", "variante": "", "nombre": "Escudo",
                "tipo": "", "club_objetivo": "FC Barcelona", "edicion": "",
            }
        ]
        for slot in range(2, 21):
            rows.append({
                "id": f"BAR-{slot:02d}", "seccion": "FC BARCELONA",
                "numero": str(slot), "hueco_album": str(slot), "variante": "",
                "nombre": f"Jugador {slot}", "tipo": "delantero",
                "club_objetivo": "FC Barcelona", "edicion": "",
            })
        rows.append({
            "id": "UF-01", "seccion": "ÚLTIMOS FICHAJES", "numero": "UF1",
            "hueco_album": "1", "variante": "", "nombre": "Refuerzo",
            "tipo": "delantero", "club_objetivo": "FC Barcelona", "edicion": "2ed",
        })
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
                "estado_laliga": (
                    "fuera_plantilla" if sticker in gone else "en_plantilla"
                ),
                "coincidencia_laliga": f"Jugador {slot}",
                "dorsal_laliga": str(slot),
            }
        return checks

    def test_a_full_page_is_reported_as_complete(self) -> None:
        reports = build_reports(self._collection(), self._checks(set()), [])
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(barcelona.count(READY), 19)
        self.assertEqual(barcelona.count(DEAD), 0)
        self.assertIn("Página completable", barcelona.verdict)

    def test_latest_signings_do_not_patch_team_slots(self) -> None:
        # El cromo de Últimos Fichajes se pega en su sección, así que no
        # rescata el hueco que dejó un jugador que se fue.
        reports = build_reports(self._collection(), self._checks({"BAR-05"}), [])
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(barcelona.count(DEAD), 1)
        self.assertEqual(len(barcelona.slots), 20)
        self.assertIn("Huecos sin solución:** 5", "\n".join(barcelona.plan))

    def test_squad_members_without_a_sticker_are_listed(self) -> None:
        squads = [
            {
                "clave": "bar-30", "seccion_album": "FC BARCELONA",
                "rol_slug": "jugador", "cromo_id": "", "dorsal": "30",
                "nombre": "Cantera Uno", "apodo": "Uno", "posicion": "Defensa",
            },
            {
                "clave": "bar-05", "seccion_album": "FC BARCELONA",
                "rol_slug": "jugador", "cromo_id": "BAR-05", "dorsal": "5",
                "nombre": "Jugador 5", "apodo": "Cinco", "posicion": "Defensa",
            },
            {
                "clave": "bar-ayu", "seccion_album": "FC BARCELONA",
                "rol_slug": "segundo-entrenador", "cromo_id": "", "dorsal": "",
                "nombre": "Ayudante", "apodo": "Ayudante",
                "posicion": "Segundo entrenador",
            },
        ]

        reports = build_reports(self._collection(), self._checks(set()), squads)
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(len(barcelona.without_sticker), 1)
        self.assertEqual(barcelona.without_sticker[0]["apodo"], "Uno")

    def test_only_the_regulars_without_a_sticker_are_flagged(self) -> None:
        squads = [
            {
                "clave": "bar-30", "seccion_album": "FC BARCELONA",
                "rol_slug": "jugador", "cromo_id": "", "dorsal": "30",
                "nombre": "Titular", "apodo": "Titular", "posicion": "Defensa",
            },
            {
                "clave": "bar-31", "seccion_album": "FC BARCELONA",
                "rol_slug": "jugador", "cromo_id": "", "dorsal": "31",
                "nombre": "Nunca juega", "apodo": "Nunca", "posicion": "Defensa",
            },
        ]
        stats = [
            {"clave": "bar-30", "minutos": "450", "partidos": "5",
             "titularidades": "5", "goles": "1", "asistencias": "0",
             "partidos_equipo": "6"},
            {"clave": "bar-31", "minutos": "0", "partidos": "0",
             "titularidades": "0", "goles": "0", "asistencias": "0",
             "partidos_equipo": "6"},
        ]

        reports = build_reports(
            self._collection(), self._checks(set()), squads, stats
        )
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")

        self.assertEqual(len(barcelona.without_sticker), 2)
        self.assertEqual(
            [row["apodo"] for row in barcelona.deserve_sticker], ["Titular"]
        )
        self.assertIn("Piden cromo a gritos:** Titular", "\n".join(barcelona.plan))


class ReportFileTests(unittest.TestCase):
    def test_renders_every_club_from_the_real_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "informe.md"
            reports = generate(
                Path("coleccion_panini_revisada.csv"),
                Path("comprobacion_laliga.csv"),
                Path("laliga_plantillas.csv"),
                output,
                Path("laliga_estadisticas.csv"),
                date(2026, 9, 17),
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(len(reports), 20)
        self.assertIn("# Optimización de plantilla por equipo", text)
        self.assertIn("## FC BARCELONA", text)
        self.assertIn("### Plantilla de LALIGA sin cromo", text)
        self.assertNotIn("Últimos Fichajes que sirven", text)
        for report in reports:
            self.assertEqual(len(report.player_slots), 19)
            self.assertEqual(len(report.slots), 20)
        # Las estadísticas tienen que llegar al informe.
        self.assertIn("′ ·", text)
        self.assertTrue(any(report.deserve_sticker for report in reports))

    def test_a_sticker_without_a_slot_does_not_break_the_report(self) -> None:
        """Panini anunció la tercera edición sin numerar los BIS, y volverá a
        pasar. Sin este tratamiento el informe revienta al ordenar los huecos,
        porque el número llega vacío."""
        reports = build_reports(
            [
                {
                    "id": "SEV-01", "seccion": "SEVILLA", "numero": "1",
                    "hueco_album": "1", "variante": "", "nombre": "Escudo",
                    "tipo": "", "club_objetivo": "Sevilla FC", "edicion": "",
                },
                {
                    "id": "SEV-BIS-1", "seccion": "SEVILLA", "numero": "BIS",
                    "hueco_album": "", "variante": "BIS", "nombre": "Por numerar",
                    "tipo": "defensa", "club_objetivo": "Sevilla FC",
                    "edicion": "3ed",
                },
            ],
            {},
            [],
        )

        sevilla = next(r for r in reports if r.section == "SEVILLA")
        self.assertEqual([o.nombre for o in sevilla.unnumbered], ["Por numerar"])
        # No se cuela en ningún hueco: eso lo convertiría en una variante.
        self.assertTrue(all(slot.hueco for slot in sevilla.slots))

    def test_a_numbered_bis_sits_in_its_slot(self) -> None:
        # Desde la tercera edición todos los BIS llevan número, así que compiten
        # por el hueco en lugar de quedar sueltos al final.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "informe.md"
            reports = generate(
                Path("coleccion_panini_revisada.csv"),
                Path("comprobacion_laliga.csv"),
                Path("laliga_plantillas.csv"),
                output,
                Path("laliga_estadisticas.csv"),
                date(2026, 9, 25),
            )

        self.assertEqual([r.section for r in reports if r.unnumbered], [])
        barcelona = next(r for r in reports if r.section == "FC BARCELONA")
        slot = next(slot for slot in barcelona.slots if slot.hueco == "18")

        self.assertEqual(
            [option.numero for option in slot.options], ["18", "18BIS"]
        )

    def test_a_sticker_of_someone_who_left_is_never_recommended(self) -> None:
        # Un hueco con dos cromos donde sólo uno sigue en el club no es una
        # elección, pero el que se fue tampoco se pega: decía «pegar» en las dos
        # filas.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "informe.md"
            generate(
                Path("coleccion_panini_revisada.csv"),
                Path("comprobacion_laliga.csv"),
                Path("laliga_plantillas.csv"),
                output,
                Path("laliga_estadisticas.csv"),
                date(2026, 9, 25),
            )
            text = output.read_text(encoding="utf-8")

        fila = next(
            line
            for line in text.splitlines()
            if line.startswith("|") and "Sergio Martínez" in line
        )
        self.assertIn("ya no está", fila)
        self.assertNotIn("**pegar**", fila)


if __name__ == "__main__":
    unittest.main()
