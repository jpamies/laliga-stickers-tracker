"""Analiza si cada página de equipo se puede completar con jugadores activos.

Cada club tiene 20 huecos: escudo, entrenador y 18 jugadores. Algunos huecos
admiten dos cromos (variantes A/B o BIS) y sólo se pega uno. Cruzando el
checklist con las plantillas oficiales de LALIGA y con los minutos jugados se
puede saber, hueco a hueco, cuál de las dos variantes conviene pegar y qué
huecos se quedan sin nadie del club.

Los Últimos Fichajes no entran en el recuento: van pegados en su propia
sección, no tapando huecos de equipo.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from extraer_checklist import CLUB_CANONICAL, CLUB_SECTIONS, markdown_escape
from comprobar_plantillas_laliga import (
    AT_THE_CLUB,
    DOUBTFUL,
    IN_SQUAD,
    OUT_OF_SQUAD,
    UNLISTED,
)


# Estado de cada hueco una vez cruzado con LALIGA.
READY = "resuelto"
DEAD = "sin_jugador_activo"
REVIEW = "por_revisar"
PENDING = "pendiente"
NOT_APPLICABLE = "no_aplica"

SLOT_LABEL = {
    READY: "Resuelto",
    DEAD: "Sin jugador activo",
    REVIEW: "Por revisar",
    PENDING: "Pendiente",
    NOT_APPLICABLE: "No aplica",
}

# Un jugador con esta parte de los minutos de su equipo se ha ganado el cromo.
IMPORTANT_SHARE = 0.30
# Diferencia a partir de la cual una variante gana claramente a la otra.
CLEAR_MARGIN = 2.0


def as_number(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


@dataclass
class Stats:
    """Lo que ha jugado alguien en lo que va de competición."""

    minutos: int = 0
    partidos: int = 0
    titularidades: int = 0
    goles: int = 0
    asistencias: int = 0
    partidos_equipo: int = 0

    @property
    def known(self) -> bool:
        return self.partidos_equipo > 0

    @property
    def share(self) -> float:
        """Fracción de los minutos posibles que ha disputado."""
        posibles = self.partidos_equipo * 90
        return self.minutos / posibles if posibles else 0.0

    @property
    def important(self) -> bool:
        return self.known and self.share >= IMPORTANT_SHARE

    def summary(self) -> str:
        if not self.known:
            return "—"
        if not self.minutos:
            return "0′ · no ha jugado"
        partes = [f"{self.minutos}′", f"{self.partidos} pj"]
        if self.titularidades:
            partes.append(f"{self.titularidades} tit")
        if self.goles:
            partes.append(f"{self.goles} g")
        if self.asistencias:
            partes.append(f"{self.asistencias} a")
        return " · ".join(partes)


@dataclass
class Option:
    """Una de las variantes que pueden ocupar un hueco."""

    numero: str
    nombre: str
    variante: str
    edicion: str
    estado: str
    ficha: str
    dorsal: str
    posicion: str
    stats: Stats = field(default_factory=Stats)

    @property
    def active(self) -> bool:
        """Sigue en el club, aunque LALIGA no siempre le dé ficha."""
        return self.estado in AT_THE_CLUB


@dataclass
class Slot:
    hueco: str
    tipo: str
    options: list[Option] = field(default_factory=list)

    @property
    def state(self) -> str:
        if self.tipo == "escudo":
            return NOT_APPLICABLE
        if any(option.active for option in self.options):
            return READY
        if any(option.estado == DOUBTFUL for option in self.options):
            return REVIEW
        if all(not option.nombre for option in self.options):
            return PENDING
        if any(option.estado == OUT_OF_SQUAD for option in self.options):
            return DEAD
        return REVIEW

    @property
    def active_options(self) -> list[Option]:
        return [option for option in self.options if option.active]

    @property
    def pick(self) -> Option | None:
        """La variante que conviene pegar: la que más juega.

        El álbum sólo admite una, y quien acumula minutos envejece mejor que
        quien todavía no se ha estrenado."""
        candidatos = self.active_options
        if not candidatos:
            return None
        return max(candidatos, key=lambda option: option.stats.minutos)

    @property
    def is_choice(self) -> bool:
        """Dos variantes viables: hay algo que decidir."""
        return len(self.active_options) > 1

    @property
    def decided_by_minutes(self) -> bool:
        """Uno juega bastante más que el otro, así que la decisión está clara."""
        if not self.is_choice:
            return False
        minutos = sorted(
            (option.stats.minutos for option in self.active_options), reverse=True
        )
        if not minutos[0]:
            return False
        return minutos[1] == 0 or minutos[0] >= minutos[1] * CLEAR_MARGIN


@dataclass
class TeamReport:
    section: str
    club: str
    slots: list[Slot]
    without_sticker: list[dict[str, str]]
    unnumbered: list[Option] = field(default_factory=list)

    @property
    def player_slots(self) -> list[Slot]:
        return [slot for slot in self.slots if slot.tipo != "escudo"]

    def count(self, state: str) -> int:
        return sum(slot.state == state for slot in self.player_slots)

    def slots_in(self, state: str) -> list[Slot]:
        return [slot for slot in self.player_slots if slot.state == state]

    @property
    def choices(self) -> list[Slot]:
        return [slot for slot in self.player_slots if slot.is_choice]

    @property
    def deserve_sticker(self) -> list[dict[str, str]]:
        """Jugadores sin cromo que se lo han ganado en el campo."""
        return [
            row for row in self.without_sticker if stats_for(row).important
        ]

    @property
    def verdict(self) -> str:
        dead = self.count(DEAD)
        review = self.count(REVIEW)
        pending = self.count(PENDING)
        if not dead and not review and not pending:
            return (
                "✅ **Página completable.** Todos los huecos tienen un cromo de "
                "alguien que sigue en el club."
            )
        partes = []
        if dead:
            hueco = "hueco" if dead == 1 else "huecos"
            partes.append(
                f"⛔ **{dead} {hueco} sin jugador activo:** o lo dejas vacío, "
                "o pegas a alguien que ya se fue."
            )
        if review:
            partes.append(f"🔎 {review} por revisar a mano.")
        if pending:
            partes.append(f"⏳ {pending} que Panini no ha asignado.")
        return " ".join(partes)

    @property
    def plan(self) -> list[str]:
        """Qué hay que decidir a mano en esta página."""
        lines = []
        dead = self.slots_in(DEAD)
        if dead:
            names = ", ".join(
                f"{slot.hueco} ({slot.options[0].nombre})" for slot in dead
            )
            lines.append(f"- **Huecos sin solución:** {names}")
        claras = [slot for slot in self.choices if slot.decided_by_minutes]
        if claras:
            names = ", ".join(
                f"{slot.hueco} → **{slot.pick.numero}** ({slot.pick.nombre},"
                f" {slot.pick.stats.minutos}′)"
                for slot in claras
            )
            lines.append(f"- **Variante recomendada por minutos:** {names}")
        abiertas = [slot for slot in self.choices if not slot.decided_by_minutes]
        if abiertas:
            names = ", ".join(
                f"{slot.hueco} ({' o '.join(o.numero for o in slot.active_options)})"
                for slot in abiertas
            )
            lines.append(f"- **Elección abierta:** {names}")
        review = self.slots_in(REVIEW)
        if review:
            names = ", ".join(
                f"{slot.hueco} ({slot.options[0].nombre})" for slot in review
            )
            lines.append(f"- **Comprobar a mano:** {names}")
        pending = self.slots_in(PENDING)
        if pending:
            names = ", ".join(slot.hueco for slot in pending)
            lines.append(f"- **Sin asignar por Panini:** {names}")
        if self.unnumbered:
            names = ", ".join(
                markdown_escape(option.nombre) for option in self.unnumbered
            )
            lines.append(
                f"- **BIS pendientes de numeración:** {names}. Van al final de"
                " la tabla porque Panini no ha dicho a qué hueco pertenecen."
            )
        merecen = self.deserve_sticker
        if merecen:
            names = ", ".join(
                f"{row['apodo'] or row['nombre']} ({as_number(row['minutos'])}′)"
                for row in merecen
            )
            lines.append(f"- **Piden cromo a gritos:** {names}")
        return lines


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def stats_for(row: dict[str, str]) -> Stats:
    return Stats(
        minutos=as_number(row.get("minutos")),
        partidos=as_number(row.get("partidos")),
        titularidades=as_number(row.get("titularidades")),
        goles=as_number(row.get("goles")),
        asistencias=as_number(row.get("asistencias")),
        partidos_equipo=as_number(row.get("partidos_equipo")),
    )


def option_for(
    row: dict[str, str],
    check: dict[str, str],
    stats: dict[str, Stats],
) -> Option:
    return Option(
        numero=row["numero"],
        nombre=row["nombre"],
        variante=row["variante"],
        edicion=row.get("edicion", ""),
        estado=check.get("estado_laliga", ""),
        ficha=check.get("coincidencia_laliga", ""),
        dorsal=check.get("dorsal_laliga", ""),
        posicion=check.get("posicion_laliga", ""),
        stats=stats.get(check.get("clave_laliga", ""), Stats()),
    )


def slot_kind(row: dict[str, str]) -> str:
    if row["nombre"] == "Escudo":
        return "escudo"
    return row["tipo"] or "jugador"


def build_reports(
    collection: list[dict[str, str]],
    checks: dict[str, dict[str, str]],
    squads: list[dict[str, str]],
    stats_rows: list[dict[str, str]] | None = None,
) -> list[TeamReport]:
    stats = {row["clave"]: stats_for(row) for row in stats_rows or []}
    by_section: dict[str, dict[str, Slot]] = defaultdict(dict)
    unnumbered: dict[str, list[Option]] = defaultdict(list)

    for row in collection:
        # Los Últimos Fichajes se pegan en su propia sección, así que no
        # participan en el recuento de huecos de equipo.
        if row["seccion"] not in CLUB_CANONICAL:
            continue
        option = option_for(row, checks.get(row["id"], {}), stats)
        # Un BIS que Panini aún no ha numerado no se puede asignar a un hueco.
        # Agruparlos por su hueco vacío los convertiría en variantes del mismo
        # cromo, que es justo lo contrario de lo que son.
        if not row["hueco_album"]:
            unnumbered[row["seccion"]].append(option)
            continue
        slots = by_section[row["seccion"]]
        slot = slots.setdefault(
            row["hueco_album"], Slot(row["hueco_album"], slot_kind(row))
        )
        slot.options.append(option)

    stats_by_key = {row["clave"]: row for row in stats_rows or []}
    orphans: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in squads:
        if row.get("cromo_id") or row.get("rol_slug") != "jugador":
            continue
        marca = stats_by_key.get(row.get("clave", ""), {})
        orphans[row.get("seccion_album", "")].append({**row, **marca})

    reports = []
    for section in CLUB_SECTIONS:
        slots = sorted(
            by_section[section].values(), key=lambda slot: int(slot.hueco)
        )
        reports.append(
            TeamReport(
                section=section,
                club=CLUB_CANONICAL[section],
                slots=slots,
                without_sticker=sorted(
                    orphans[section],
                    key=lambda row: (-as_number(row.get("minutos")), row["nombre"]),
                ),
                unnumbered=sorted(unnumbered[section], key=lambda o: o.nombre),
            )
        )
    return reports


def anchor(section: str) -> str:
    return section.lower().replace(" / ", "--").replace(" ", "-")


def option_cell(option: Option) -> str:
    label = option.numero
    if option.edicion == "2ed":
        label += " (2ª ed)"
    return label


def summary_table(reports: list[TeamReport]) -> list[str]:
    lines = [
        "| Equipo | Resueltos | Sin jugador activo | Por revisar | Pendientes"
        " | Variantes a elegir | Piden cromo |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for report in reports:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[{markdown_escape(report.club)}](#{anchor(report.section)})",
                    f"{report.count(READY)}/19",
                    str(report.count(DEAD)),
                    str(report.count(REVIEW)),
                    str(report.count(PENDING)),
                    str(len(report.choices)),
                    str(len(report.deserve_sticker)),
                ]
            )
            + " |"
        )
    return lines


def slot_mark(slot: Slot, option: Option) -> str:
    if slot.state != READY:
        return SLOT_LABEL[slot.state]
    # Un cromo de alguien que ya no está nunca se recomienda, aunque su hueco
    # esté resuelto por la otra variante. Es el caso de los BIS que sustituyen
    # a un jugador traspasado.
    if not option.active:
        return "⛔ ya no está"
    if not slot.is_choice:
        return "**pegar**"
    if not slot.decided_by_minutes:
        return "elegir una"
    return "**pegar**" if option is slot.pick else "descartar"


def option_row(hueco: str, option: Option, mark: str) -> str:
    details = (
        option.ficha
        if option.estado == IN_SQUAD
        else "sin ficha, sigue en el club"
        if option.estado == UNLISTED
        else "—"
    )
    return (
        "| "
        + " | ".join(
            [
                hueco,
                markdown_escape(option_cell(option)),
                markdown_escape(option.nombre or "sin asignar"),
                markdown_escape(details),
                option.dorsal or "—",
                markdown_escape(option.stats.summary()),
                mark,
            ]
        )
        + " |"
    )


def slot_rows(report: TeamReport) -> list[str]:
    lines = [
        "| Hueco | Cromo | Nombre | Ficha en LALIGA | Dorsal | Minutos | Estado |",
        "| ---: | :---: | --- | --- | ---: | --- | --- |",
    ]
    for slot in report.slots:
        for index, option in enumerate(slot.options):
            lines.append(
                option_row(slot.hueco if not index else "", option, slot_mark(slot, option))
            )
    # Los BIS sin numerar cierran la tabla: son cromos de esta página, pero
    # Panini no ha dicho todavía en qué hueco van.
    for index, option in enumerate(report.unnumbered):
        mark = "🆕 sin numerar" if option.active else "⛔ ya no está"
        lines.append(option_row("BIS" if not index else "", option, mark))
    return lines


def orphan_rows(report: TeamReport) -> list[str]:
    if not report.without_sticker:
        return ["_Toda la plantilla oficial tiene cromo._"]
    lines = [
        "| Dorsal | Jugador | Posición | Minutos | ¿Merece cromo? |",
        "| ---: | --- | --- | --- | :---: |",
    ]
    for row in report.without_sticker:
        stats = stats_for(row)
        veredicto = (
            "**sí**"
            if stats.important
            else "no ha jugado"
            if stats.known and not stats.minutos
            else "—"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    row["dorsal"] or "—",
                    markdown_escape(row["apodo"] or row["nombre"]),
                    markdown_escape(row["posicion"]),
                    markdown_escape(stats.summary()),
                    veredicto,
                ]
            )
            + " |"
        )
    return lines


def render(reports: list[TeamReport], generated_on: date) -> str:
    total_dead = sum(report.count(DEAD) for report in reports)
    total_choices = sum(len(report.choices) for report in reports)
    decided = sum(
        1 for report in reports for slot in report.choices if slot.decided_by_minutes
    )
    deserve = sum(len(report.deserve_sticker) for report in reports)
    complete = sum(
        1
        for report in reports
        if not report.count(DEAD)
        and not report.count(REVIEW)
        and not report.count(PENDING)
    )

    lines = [
        "# Optimización de plantilla por equipo",
        "",
        f"Generado el {generated_on.isoformat()} por `analizar_optimizacion.py`.",
        "",
        "Cada club ocupa una página de **20 huecos**: escudo, entrenador y 18",
        "jugadores. Algunos huecos admiten dos cromos (variantes `A`/`B` o",
        "`BIS`) y sólo se pega uno. Este informe cruza el checklist con las",
        "plantillas oficiales de LALIGA y con los minutos jugados para responder",
        "a dos preguntas: **¿puedo llenar la página sólo con futbolistas que",
        "siguen en el club?** y **¿cuál de las dos variantes conviene pegar?**",
        "",
        "Los Últimos Fichajes no aparecen aquí: se pegan en su propia sección,",
        "no tapando huecos de equipo.",
        "",
        "## Cómo leerlo",
        "",
        "- **Resueltos:** el hueco tiene al menos un cromo de alguien que sigue",
        "  en la plantilla.",
        "- **Sin jugador activo:** ninguna variante sigue en el club. O lo dejas",
        "  vacío, o pegas a alguien que se fue.",
        "- **Por revisar:** el emparejamiento con LALIGA no es concluyente",
        "  (apodos cortos o apellidos compartidos). Hay que mirarlo a mano.",
        "- **Variantes a elegir:** huecos con dos jugadores en plantilla. Cuando",
        "  uno juega al menos el doble que el otro, se recomienda ese.",
        "- **Piden cromo:** jugadores inscritos y sin cromo que han disputado al",
        f"  menos el {IMPORTANT_SHARE:.0%} de los minutos de su equipo.",
        "- **BIS sin numerar:** cierran la tabla de huecos. Panini los ha",
        "  anunciado sin número, así que todavía no se sabe a qué hueco van.",
        "",
        "> El entrenador cuenta como hueco comprobable porque LALIGA también",
        "> publica su ficha. El escudo queda fuera del recuento.",
        "",
        "## Resumen",
        "",
        f"- **Equipos con la página completable:** {complete} de 20",
        f"- **Huecos sin ningún jugador activo:** {total_dead}",
        f"- **Huecos con dos variantes válidas:** {total_choices}"
        f" ({decided} con una recomendación clara por minutos)",
        f"- **Jugadores que piden cromo:** {deserve}",
        "",
    ]
    lines.extend(summary_table(reports))
    lines.append("")

    for report in reports:
        lines.extend([f"## {report.section}", "", report.verdict, ""])
        if report.plan:
            lines.extend(report.plan)
            lines.append("")
        lines.extend(["### Huecos del álbum", ""])
        lines.extend(slot_rows(report))
        lines.extend(["", "### Plantilla de LALIGA sin cromo", ""])
        lines.extend(orphan_rows(report))
        lines.append("")

    return "\n".join(lines)


def generate(
    collection_path: Path,
    check_path: Path,
    squads_path: Path,
    output_path: Path,
    stats_path: Path | None = None,
    generated_on: date | None = None,
) -> list[TeamReport]:
    collection = read_csv(collection_path)
    checks = {row["id"]: row for row in read_csv(check_path)}
    squads = read_csv(squads_path)
    stats_rows = read_csv(stats_path) if stats_path and stats_path.exists() else []
    reports = build_reports(collection, checks, squads, stats_rows)
    output_path.write_text(
        render(reports, generated_on or date.today()), encoding="utf-8"
    )
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analiza si cada página de equipo se puede completar con jugadores "
            "activos."
        )
    )
    parser.add_argument(
        "--coleccion", type=Path, default=Path("coleccion_panini_revisada.csv")
    )
    parser.add_argument(
        "--comprobacion", type=Path, default=Path("comprobacion_laliga.csv")
    )
    parser.add_argument(
        "--plantillas", type=Path, default=Path("laliga_plantillas.csv")
    )
    parser.add_argument(
        "--estadisticas", type=Path, default=Path("laliga_estadisticas.csv")
    )
    parser.add_argument(
        "--salida", type=Path, default=Path("OPTIMIZACION_PLANTILLAS.md")
    )
    args = parser.parse_args()

    reports = generate(
        args.coleccion,
        args.comprobacion,
        args.plantillas,
        args.salida,
        args.estadisticas,
    )
    dead = sum(report.count(DEAD) for report in reports)
    choices = sum(len(report.choices) for report in reports)
    deserve = sum(len(report.deserve_sticker) for report in reports)
    print(
        f"Generado {args.salida}: {len(reports)} equipos, {dead} huecos sin "
        f"jugador activo, {choices} variantes a elegir y {deserve} jugadores "
        "que piden cromo."
    )


if __name__ == "__main__":
    main()
