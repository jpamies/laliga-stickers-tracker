"""Analiza si cada página de equipo se puede completar con jugadores activos.

Cada club tiene 20 huecos: escudo, entrenador y 18 jugadores. Algunos huecos
admiten dos cromos (variantes A/B o BIS) y sólo se pega uno. Cruzando el
checklist con las plantillas oficiales de LALIGA se puede saber, hueco a hueco,
si existe al menos una opción que siga en el club, cuántos Últimos Fichajes hay
para tapar los que no y a qué jugadores de la plantilla real no les corresponde
ningún cromo.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from extraer_checklist import CLUB_CANONICAL, CLUB_SECTIONS, markdown_escape


LATEST_SIGNINGS = "ÚLTIMOS FICHAJES"
CREST_SLOT = "1"
COACH_SLOT = "2"

IN_SQUAD = "en_plantilla"
OUT_OF_SQUAD = "fuera_plantilla"
DOUBTFUL = "coincidencia_dudosa"

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

    @property
    def active(self) -> bool:
        return self.estado == IN_SQUAD


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
    def pick(self) -> Option | None:
        for option in self.options:
            if option.active:
                return option
        return None

    @property
    def active_options(self) -> list[Option]:
        return [option for option in self.options if option.active]


@dataclass
class TeamReport:
    section: str
    club: str
    slots: list[Slot]
    signings: list[Option]
    without_sticker: list[dict[str, str]]

    @property
    def player_slots(self) -> list[Slot]:
        return [slot for slot in self.slots if slot.tipo != "escudo"]

    def count(self, state: str) -> int:
        return sum(slot.state == state for slot in self.player_slots)

    @property
    def active_signings(self) -> list[Option]:
        return [signing for signing in self.signings if signing.active]

    def slots_in(self, state: str) -> list[Slot]:
        return [slot for slot in self.player_slots if slot.state == state]

    @property
    def deficit(self) -> int:
        return max(0, self.count(DEAD) - len(self.active_signings))

    @property
    def plan(self) -> list[str]:
        """Qué hay que decidir a mano en esta página."""
        lines = []
        dead = self.slots_in(DEAD)
        if dead:
            names = ", ".join(
                f"{slot.hueco} ({slot.options[0].nombre})" for slot in dead
            )
            lines.append(f"- **Huecos a resolver:** {names}")
        signings = self.active_signings
        if signings:
            names = ", ".join(
                f"{signing.numero} ({signing.nombre})" for signing in signings
            )
            lines.append(f"- **Últimos Fichajes que sirven:** {names}")
        elif dead:
            lines.append(
                "- **Últimos Fichajes que sirven:** ninguno para este equipo"
            )
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
        double = [slot for slot in self.player_slots if len(slot.active_options) > 1]
        if double:
            names = ", ".join(
                f"{slot.hueco} ({' o '.join(option.numero for option in slot.active_options)})"
                for slot in double
            )
            lines.append(f"- **Puedes elegir variante:** {names}")
        return lines

    @property
    def verdict(self) -> str:
        dead = self.count(DEAD)
        review = self.count(REVIEW)
        pending = self.count(PENDING)
        if not dead and not review and not pending:
            return (
                "✅ **Página completa sin Últimos Fichajes.** Todos los huecos "
                "tienen un cromo de alguien que sigue en el club."
            )
        parts = []
        if dead:
            available = len(self.active_signings)
            if self.deficit:
                parts.append(
                    f"⛔ **{dead} huecos sin jugador activo** y sólo "
                    f"{available} Últimos Fichajes: quedan **{self.deficit} "
                    "sin solución**."
                )
            else:
                parts.append(
                    f"🔄 **{dead} huecos sin jugador activo**, cubiertos con "
                    f"{dead} de los {available} Últimos Fichajes disponibles."
                )
        if review:
            parts.append(f"🔎 {review} huecos por revisar a mano.")
        if pending:
            parts.append(f"⏳ {pending} huecos que Panini no ha asignado.")
        return " ".join(parts)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def option_for(row: dict[str, str], check: dict[str, str]) -> Option:
    return Option(
        numero=row["numero"],
        nombre=row["nombre"],
        variante=row["variante"],
        edicion=row.get("edicion", ""),
        estado=check.get("estado_laliga", ""),
        ficha=check.get("coincidencia_laliga", ""),
        dorsal=check.get("dorsal_laliga", ""),
        posicion=check.get("posicion_laliga", ""),
    )


def slot_kind(row: dict[str, str]) -> str:
    if row["nombre"] == "Escudo":
        return "escudo"
    return row["tipo"] or "jugador"


def build_reports(
    collection: list[dict[str, str]],
    checks: dict[str, dict[str, str]],
    squads: list[dict[str, str]],
) -> list[TeamReport]:
    by_section: dict[str, dict[str, Slot]] = defaultdict(dict)
    signings: dict[str, list[Option]] = defaultdict(list)

    for row in collection:
        check = checks.get(row["id"], {})
        if row["seccion"] in CLUB_CANONICAL:
            slots = by_section[row["seccion"]]
            slot = slots.setdefault(
                row["hueco_album"], Slot(row["hueco_album"], slot_kind(row))
            )
            slot.options.append(option_for(row, check))
        elif row["seccion"] == LATEST_SIGNINGS and row["club_objetivo"]:
            section = next(
                (
                    name
                    for name, club in CLUB_CANONICAL.items()
                    if club == row["club_objetivo"]
                ),
                "",
            )
            if section:
                signings[section].append(option_for(row, check))

    orphans: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in squads:
        if row.get("cromo_id") or row.get("rol_slug") != "jugador":
            continue
        orphans[row.get("seccion_album", "")].append(row)

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
                signings=sorted(signings[section], key=lambda item: item.numero),
                without_sticker=sorted(
                    orphans[section],
                    key=lambda row: (
                        int(row["dorsal"]) if row["dorsal"].isdigit() else 999,
                        row["nombre"],
                    ),
                ),
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
        "| Equipo | Resueltos | Sin jugador activo | Por revisar | Pendientes | Últimos Fichajes | Déficit |",
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
                    f"{len(report.active_signings)}/{len(report.signings)}",
                    str(report.deficit) if report.deficit else "—",
                ]
            )
            + " |"
        )
    return lines


def slot_rows(report: TeamReport) -> list[str]:
    lines = [
        "| Hueco | Cromo | Nombre | Ficha en LALIGA | Dorsal | Estado |",
        "| ---: | :---: | --- | --- | ---: | --- |",
    ]
    for slot in report.slots:
        state = slot.state
        chosen = slot.pick
        choices = len(slot.active_options)
        for index, option in enumerate(slot.options):
            if state != READY:
                mark = SLOT_LABEL[state]
            elif choices > 1:
                mark = "elegir una"
            elif option is chosen:
                mark = "**pegar**"
            else:
                mark = "descartar"
            details = (
                f"{option.ficha}"
                if option.estado == IN_SQUAD
                else "—"
            )
            lines.append(
                "| "
                + " | ".join(
                    [
                        slot.hueco if not index else "",
                        markdown_escape(option_cell(option)),
                        markdown_escape(option.nombre or "sin asignar"),
                        markdown_escape(details),
                        option.dorsal or "—",
                        mark,
                    ]
                )
                + " |"
            )
    return lines


def signing_rows(report: TeamReport) -> list[str]:
    if not report.signings:
        return ["_Este equipo no tiene ningún cromo de Últimos Fichajes._"]
    lines = [
        "| Cromo | Nombre | Ficha en LALIGA | Dorsal | Estado |",
        "| :---: | --- | --- | ---: | --- |",
    ]
    for signing in report.signings:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(signing.numero),
                    markdown_escape(signing.nombre),
                    markdown_escape(signing.ficha if signing.active else "—"),
                    signing.dorsal or "—",
                    "**sirve para tapar un hueco**" if signing.active else "no está en el club",
                ]
            )
            + " |"
        )
    return lines


def orphan_rows(report: TeamReport) -> list[str]:
    if not report.without_sticker:
        return ["_Toda la plantilla oficial tiene cromo._"]
    lines = [
        "| Dorsal | Jugador | Posición |",
        "| ---: | --- | --- |",
    ]
    for row in report.without_sticker:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["dorsal"] or "—",
                    markdown_escape(row["apodo"] or row["nombre"]),
                    markdown_escape(row["posicion"]),
                ]
            )
            + " |"
        )
    return lines


def render(reports: list[TeamReport], generated_on: date) -> str:
    total_dead = sum(report.count(DEAD) for report in reports)
    total_deficit = sum(report.deficit for report in reports)
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
        "jugadores. Algunos huecos admiten dos cromos (variantes `A`/`B` o `BIS`)",
        "y sólo se pega uno. Este informe cruza el checklist con las plantillas",
        "oficiales de LALIGA para responder a una pregunta por equipo: **¿puedo",
        "dejar la página llena sólo con futbolistas que siguen en el club?**",
        "",
        "## Cómo leerlo",
        "",
        "- **Resueltos:** el hueco tiene al menos un cromo de alguien que sigue",
        "  en la plantilla. Si hay dos variantes, se indica cuál pegar.",
        "- **Sin jugador activo:** ninguna variante sigue en el club. O lo dejas",
        "  vacío, o pegas a alguien que se fue, o tapas el hueco con un cromo de",
        "  Últimos Fichajes.",
        "- **Por revisar:** el emparejamiento con LALIGA no es concluyente",
        "  (apodos cortos o apellidos compartidos). Hay que mirarlo a mano.",
        "- **Déficit:** huecos sin jugador activo que tampoco puede cubrir un",
        "  Último Fichaje del mismo equipo.",
        "",
        "> El entrenador cuenta como hueco comprobable porque LALIGA también",
        "> publica su ficha. El escudo queda fuera del recuento.",
        "",
        "## Resumen",
        "",
        f"- **Equipos con la página completable sin Últimos Fichajes:** {complete} de 20",
        f"- **Huecos sin ningún jugador activo:** {total_dead}",
        f"- **Huecos que ni con Últimos Fichajes se pueden salvar:** {total_deficit}",
        "",
    ]
    lines.extend(summary_table(reports))
    lines.append("")

    for report in reports:
        lines.extend(
            [
                f"## {report.section}",
                "",
                report.verdict,
                "",
            ]
        )
        if report.plan:
            lines.extend(report.plan)
            lines.append("")
        lines.extend(["### Huecos del álbum", ""])
        lines.extend(slot_rows(report))
        lines.extend(["", "### Últimos Fichajes de este equipo", ""])
        lines.extend(signing_rows(report))
        lines.extend(
            [
                "",
                "### Condicional: plantilla de LALIGA sin cromo",
                "",
            ]
        )
        lines.extend(orphan_rows(report))
        lines.append("")

    return "\n".join(lines)


def generate(
    collection_path: Path,
    check_path: Path,
    squads_path: Path,
    output_path: Path,
    generated_on: date | None = None,
) -> list[TeamReport]:
    collection = read_csv(collection_path)
    checks = {row["id"]: row for row in read_csv(check_path)}
    squads = read_csv(squads_path)
    reports = build_reports(collection, checks, squads)
    output_path.write_text(
        render(reports, generated_on or date.today()), encoding="utf-8"
    )
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analiza si cada página de equipo se puede completar con jugadores activos."
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
        "--salida", type=Path, default=Path("OPTIMIZACION_PLANTILLAS.md")
    )
    args = parser.parse_args()

    reports = generate(
        args.coleccion, args.comprobacion, args.plantillas, args.salida
    )
    dead = sum(report.count(DEAD) for report in reports)
    deficit = sum(report.deficit for report in reports)
    print(
        f"Generado {args.salida}: {len(reports)} equipos, "
        f"{dead} huecos sin jugador activo y {deficit} sin solución."
    )


if __name__ == "__main__":
    main()
