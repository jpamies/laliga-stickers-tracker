"""Documenta las plantillas oficiales de LALIGA en un Markdown legible.

`laliga_plantillas.csv` es la fuente que decide si un cromo se puede pegar,
así que conviene poder leerla sin abrir la hoja de cálculo: quién está
registrado en cada club, con qué dorsal y qué cromo del álbum le corresponde.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path

from extraer_checklist import CLUB_SECTIONS, markdown_escape


PLAYER_ROLE = "jugador"
POSITION_ORDER = {
    "entrenador": 0,
    "segundo-entrenador": 1,
    "portero": 2,
    "defensa": 3,
    "centrocampista": 4,
    "medio": 4,
    "delantero": 5,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    dorsal = row["dorsal"]
    return (
        POSITION_ORDER.get(row["posicion_slug"], 9),
        int(dorsal) if dorsal.isdigit() else 999,
        row["nombre"],
    )


def age_on(birth: str, today: date) -> str:
    if not birth:
        return ""
    try:
        born = date.fromisoformat(birth)
    except ValueError:
        return ""
    years = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        years -= 1
    return str(years) if 0 < years < 120 else ""


def anchor(section: str) -> str:
    return section.lower().replace(" / ", "--").replace(" ", "-")


def tags(row: dict[str, str]) -> str:
    marks = []
    if row["cedido"] == "true":
        marks.append("cedido")
    if row["cedido_fuera"] == "true":
        marks.append("cedido fuera")
    if row["activo"] != "true":
        marks.append("ficha inactiva")
    return ", ".join(marks)


def summary_lines(
    teams: list[dict[str, str]],
    squads: list[dict[str, str]],
    today: date,
) -> list[str]:
    players = [row for row in squads if row["rol_slug"] == PLAYER_ROLE]
    with_sticker = [row for row in players if row["cromo_id"]]
    loaned = [row for row in players if row["cedido"] == "true"]
    without_number = [row for row in players if not row["dorsal"]]
    positions = Counter(row["posicion"] for row in players)

    lines = [
        "# Plantillas oficiales de LALIGA EA SPORTS 2026-27",
        "",
        f"Generado el {today.isoformat()} por `generar_plantillas_markdown.py` "
        "a partir de `laliga_plantillas.csv`.",
        "",
        "Esta es la fuente que decide si un cromo del álbum se puede pegar: si el "
        "jugador impreso no aparece aquí, es que ya no está en el club.",
        "",
        "## Resumen",
        "",
        "| Dato | Valor |",
        "| --- | ---: |",
        f"| Equipos | {len(teams)} |",
        f"| **Jugadores registrados** | **{len(players)}** |",
        f"| Fichas totales (con cuerpo técnico) | {len(squads)} |",
        f"| Jugadores con cromo en el álbum | {len(with_sticker)} |",
        f"| Jugadores sin cromo | {len(players) - len(with_sticker)} |",
        f"| Cedidos | {len(loaned)} |",
        f"| Sin dorsal asignado | {len(without_number)} |",
        "",
        "### Por demarcación",
        "",
        "| Demarcación | Jugadores |",
        "| --- | ---: |",
    ]
    for position, total in sorted(positions.items(), key=lambda item: -item[1]):
        lines.append(f"| {markdown_escape(position)} | {total} |")

    lines.extend(
        [
            "",
            "### Por equipo",
            "",
            "| Equipo | Jugadores | Con cromo | Sin cromo | Cedidos |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for team in teams:
        section = team["seccion_album"]
        squad = [
            row
            for row in players
            if row["seccion_album"] == section
        ]
        owned = sum(1 for row in squad if row["cromo_id"])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[{markdown_escape(team['nombre_corto'])}](#{anchor(section)})",
                    str(len(squad)),
                    str(owned),
                    str(len(squad) - owned),
                    str(sum(1 for row in squad if row["cedido"] == "true")),
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def team_lines(
    team: dict[str, str],
    squad: list[dict[str, str]],
    today: date,
) -> list[str]:
    players = [row for row in squad if row["rol_slug"] == PLAYER_ROLE]
    lines = [
        f"## {team['seccion_album']}",
        "",
        f"**{team['nombre']}** · {team['estadio']} · "
        f"{len(players)} jugadores registrados",
        "",
        "| Dorsal | Jugador | Nombre completo | Demarcación | Edad | País | Cromo | Notas |",
        "| ---: | --- | --- | --- | ---: | :---: | --- | --- |",
    ]
    for row in sorted(squad, key=sort_key):
        lines.append(
            "| "
            + " | ".join(
                [
                    row["dorsal"] or "—",
                    markdown_escape(row["apodo"] or row["nombre"]),
                    markdown_escape(row["nombre"]),
                    markdown_escape(row["posicion"]),
                    age_on(row["fecha_nacimiento"], today) or "—",
                    row["pais"] or "—",
                    markdown_escape(row["cromos"] or "—"),
                    markdown_escape(tags(row) or ""),
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def generate(
    squads_path: Path,
    teams_path: Path,
    output_path: Path,
    today: date | None = None,
) -> int:
    squads = read_csv(squads_path)
    teams = read_csv(teams_path)
    if not squads or not teams:
        raise ValueError(
            "Faltan datos: ejecuta antes generar_plantillas_laliga.py."
        )
    today = today or date.today()

    order = {section: index for index, section in enumerate(CLUB_SECTIONS)}
    teams = sorted(teams, key=lambda team: order.get(team["seccion_album"], 99))

    lines = summary_lines(teams, squads, today)
    for team in teams:
        squad = [
            row
            for row in squads
            if row["seccion_album"] == team["seccion_album"]
        ]
        lines.extend(team_lines(team, squad, today))

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return sum(1 for row in squads if row["rol_slug"] == PLAYER_ROLE)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Documenta las plantillas oficiales de LALIGA en Markdown."
    )
    parser.add_argument(
        "--plantillas", type=Path, default=Path("laliga_plantillas.csv")
    )
    parser.add_argument("--equipos", type=Path, default=Path("laliga_equipos.csv"))
    parser.add_argument(
        "--salida", type=Path, default=Path("PLANTILLAS_LALIGA.md")
    )
    args = parser.parse_args()

    total = generate(args.plantillas, args.equipos, args.salida)
    print(f"Generado {args.salida} con {total} jugadores registrados.")


if __name__ == "__main__":
    main()
