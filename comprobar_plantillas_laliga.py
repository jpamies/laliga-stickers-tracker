"""Contrasta el checklist Panini con las plantillas oficiales de LALIGA.

Genera un CSV auxiliar por identificador de cromo (igual que
`imagenes_panini.csv` o `fotos_transfermarkt.csv`) que el álbum consume para
saber qué jugadores ya no aparecen en la plantilla de su club. El CSV maestro
no se toca: la recomendación pública sigue siendo siempre «pegar» y sólo el
dueño del álbum ve la sugerencia de no pegar.
"""

from __future__ import annotations

import argparse
import csv
import difflib
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

from comprobar_plantillas import NAME_ALIASES, normalize_name
from extraer_checklist import CLUB_CANONICAL


SECTION_BY_CLUB = {club: section for section, club in CLUB_CANONICAL.items()}

# LALIGA usa el nombre del registro civil y Panini el nombre deportivo.
LALIGA_ALIASES = {
    "quique sanchez flores": "enrique sanchez flores",
    "cholo simeone": "diego pablo simeone",
}

CSV_FIELDS = [
    "id",
    "seccion",
    "numero",
    "nombre",
    "club_objetivo",
    "estado_laliga",
    "coincidencia_laliga",
    "dorsal_laliga",
    "posicion_laliga",
    "confianza_laliga",
    "comprobado_en",
    "notas_laliga",
]

IN_SQUAD = "en_plantilla"
OUT_OF_SQUAD = "fuera_plantilla"
DOUBTFUL = "coincidencia_dudosa"
NOT_APPLICABLE = "no_aplica"
NO_SQUAD = "plantilla_no_disponible"
UNPUBLISHED = "pendiente_publicacion"

# Longitud mínima para fiarnos de una coincidencia parcial y, sobre todo, para
# atrevernos a decir que un jugador ya no está: con apodos como «Oso» o «Yusi»
# el parecido entre nombres deja de ser informativo.
MIN_PARTIAL_LENGTH = 4
MIN_ABSENCE_LENGTH = 5


@dataclass(frozen=True)
class SquadMember:
    nombre: str
    apodo: str
    dorsal: str
    posicion: str
    keys: frozenset[str]


@dataclass(frozen=True)
class Match:
    estado: str
    candidato: str
    dorsal: str
    posicion: str
    confianza: float
    notas: str


def member_keys(row: dict[str, str]) -> frozenset[str]:
    """Todas las formas en que Panini puede imprimir a este jugador."""
    surname = row.get("apellidos", "")
    given = row.get("nombre_pila", "")
    candidates = {
        row.get("nombre", ""),
        row.get("apodo", ""),
        surname,
        f"{given} {surname}".strip(),
    }
    keys = {
        normalized
        for candidate in candidates
        if (normalized := normalize_name(candidate))
    }
    # «Luiz Lúcio Reis Júnior» se imprime como «Luiz Júnior», así que los
    # nombres largos también se indexan por su primera y su última palabra.
    for key in list(keys):
        words = key.split()
        if len(words) > 2:
            keys.add(f"{words[0]} {words[-1]}")
    return frozenset(keys)


def load_squads(path: Path) -> dict[str, list[SquadMember]]:
    squads: dict[str, list[SquadMember]] = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            section = row.get("seccion_album", "")
            if not section:
                continue
            squads.setdefault(section, []).append(
                SquadMember(
                    nombre=row.get("nombre", ""),
                    apodo=row.get("apodo", ""),
                    dorsal=row.get("dorsal", ""),
                    posicion=row.get("posicion", ""),
                    keys=member_keys(row),
                )
            )
    if not squads:
        raise ValueError(f"{path} no contiene plantillas; ejecuta antes generar_plantillas_laliga.py.")
    return squads


def hit(member: SquadMember, confidence: float, notes: str) -> Match:
    return Match(
        IN_SQUAD,
        member.nombre or member.apodo,
        member.dorsal,
        member.posicion,
        confidence,
        notes,
    )


def match_member(name: str, squad: list[SquadMember]) -> Match:
    raw_target = normalize_name(name)
    if not raw_target:
        return Match(UNPUBLISHED, "", "", "", 0.0, "Cromo sin nombre.")

    targets = [raw_target]
    for aliases in (LALIGA_ALIASES, NAME_ALIASES):
        alias = aliases.get(raw_target)
        if alias and alias not in targets:
            targets.append(alias)

    for index, target in enumerate(targets):
        exact = [member for member in squad if target in member.keys]
        if len(exact) == 1:
            notes = "Coincidencia exacta." if not index else "Coincidencia por alias conocido."
            return hit(exact[0], 1.0 if not index else 0.99, notes)
        if len(exact) > 1:
            candidates = ", ".join(member.nombre for member in exact)
            return Match(
                DOUBTFUL,
                candidates,
                "",
                "",
                0.5,
                "El nombre coincide con varios jugadores de la plantilla.",
            )

    for target in targets:
        if len(target) < MIN_PARTIAL_LENGTH:
            continue
        contained = [
            member
            for member in squad
            if any(target in key or key in target for key in member.keys)
        ]
        if len(contained) == 1:
            return hit(contained[0], 0.96, "Coincidencia única por nombre parcial.")
        if len(contained) > 1:
            candidates = ", ".join(member.nombre for member in contained)
            return Match(
                DOUBTFUL,
                candidates,
                "",
                "",
                0.5,
                "El nombre parcial coincide con varios jugadores.",
            )

    best_score = 0.0
    best_member: SquadMember | None = None
    for member in squad:
        for key in member.keys:
            for target in targets:
                score = difflib.SequenceMatcher(None, target, key).ratio()
                if score > best_score:
                    best_score, best_member = score, member
    if best_member is None:
        return Match(NO_SQUAD, "", "", "", 0.0, "La plantilla llegó vacía.")
    if best_score >= 0.86:
        return hit(best_member, best_score, "Coincidencia aproximada de alta confianza.")
    if best_score >= 0.68:
        return Match(
            DOUBTFUL,
            best_member.nombre,
            "",
            "",
            best_score,
            "Posible coincidencia; confírmala antes de descartar el cromo.",
        )
    if len(raw_target) < MIN_ABSENCE_LENGTH:
        return Match(
            DOUBTFUL,
            best_member.nombre,
            "",
            "",
            best_score,
            "Nombre demasiado corto para descartarlo con seguridad.",
        )
    return Match(
        OUT_OF_SQUAD,
        best_member.nombre,
        "",
        "",
        best_score,
        "No aparece en la plantilla oficial de LALIGA.",
    )


def section_for(row: dict[str, str], squads: dict[str, list[SquadMember]]) -> str:
    if row["seccion"] in squads:
        return row["seccion"]
    return SECTION_BY_CLUB.get(row.get("club_objetivo", ""), "")


def check_rows(
    rows: list[dict[str, str]],
    squads: dict[str, list[SquadMember]],
    checked_on: date,
) -> list[dict[str, str]]:
    checked_on_text = checked_on.isoformat()
    results: list[dict[str, str]] = []
    for row in rows:
        name = row.get("nombre", "")
        if not name:
            match = Match(UNPUBLISHED, "", "", "", 0.0, "Hueco sin jugador.")
        elif name == "Escudo":
            match = Match(NOT_APPLICABLE, "", "", "", 0.0, "El escudo no es un jugador.")
        else:
            section = section_for(row, squads)
            match = (
                match_member(name, squads[section])
                if section
                else Match(NO_SQUAD, "", "", "", 0.0, "Sin club que comprobar.")
            )
        results.append(
            {
                "id": row["id"],
                "seccion": row["seccion"],
                "numero": row["numero"],
                "nombre": name,
                "club_objetivo": row.get("club_objetivo", ""),
                "estado_laliga": match.estado,
                "coincidencia_laliga": match.candidato,
                "dorsal_laliga": match.dorsal,
                "posicion_laliga": match.posicion,
                "confianza_laliga": f"{match.confianza:.4f}",
                "comprobado_en": checked_on_text,
                "notas_laliga": match.notas,
            }
        )
    return results


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def generate(
    collection_path: Path,
    squads_path: Path,
    output_path: Path,
    checked_on: date | None = None,
) -> dict[str, int]:
    with collection_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    squads = load_squads(squads_path)
    results = check_rows(rows, squads, checked_on or date.today())
    write_csv(results, output_path)
    counts: dict[str, int] = {}
    for result in results:
        counts[result["estado_laliga"]] = counts.get(result["estado_laliga"], 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Marca qué cromos ya no están en la plantilla oficial de LALIGA."
    )
    parser.add_argument(
        "--coleccion", type=Path, default=Path("coleccion_panini_revisada.csv")
    )
    parser.add_argument(
        "--plantillas", type=Path, default=Path("laliga_plantillas.csv")
    )
    parser.add_argument("--salida", type=Path, default=Path("comprobacion_laliga.csv"))
    args = parser.parse_args()

    counts = generate(args.coleccion, args.plantillas, args.salida)
    print(f"Generado {args.salida}:")
    for estado, total in sorted(counts.items()):
        print(f"- {estado}: {total}")


if __name__ == "__main__":
    main()
