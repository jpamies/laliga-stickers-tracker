"""Contrasta el checklist Panini con las plantillas oficiales de LALIGA.

Emparejar cromos y fichas sirve en las dos direcciones, así que un único
recorrido produce los dos índices:

- `comprobacion_laliga.csv`, por identificador de cromo, dice si el jugador
  sigue en su club. El álbum lo consume para mostrar la ficha oficial y, sólo
  al dueño, la sugerencia de no pegar. El CSV maestro no se toca: la
  recomendación pública sigue siendo siempre «pegar».
- `laliga_plantillas.csv` recibe de vuelta el cromo asociado a cada ficha, para
  saber quién de la plantilla real tiene cromo y cuál es.
"""

from __future__ import annotations

import argparse
import csv
import difflib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from comprobar_plantillas import NAME_ALIASES, normalize_name
from extraer_checklist import CLUB_CANONICAL, CLUB_SECTIONS
from generar_plantillas_laliga import (
    PLAYER_FIELDS,
    TEAM_FIELDS,
    write_csv as write_squad_csv,
    write_sql,
)


SECTION_BY_CLUB = {club: section for section, club in CLUB_CANONICAL.items()}

# Sólo los cromos del equipo y los de Últimos Fichajes representan a un
# jugador en su club. Las secciones temáticas (ADN, Fantasy, Draft, Extra)
# repiten jugadores con otro diseño y ensuciarían el índice inverso.
SQUAD_SECTIONS = frozenset(CLUB_SECTIONS) | {"ÚLTIMOS FICHAJES"}

# LALIGA usa el nombre del registro civil y Panini el nombre deportivo.
LALIGA_ALIASES = {
    "quique sanchez flores": "enrique sanchez flores",
    "cholo simeone": "diego pablo simeone",
    "yusi": "youssef enriquez",
    # LALIGA no registra el nombre por el que se les conoce.
    "ilaix moriba": "moriba kourouma kourouma",
}

# Cromos que comparten apellido con un fichaje posterior, así que el
# emparejamiento por texto no puede distinguirlos. Comprobado a mano.
KNOWN_ABSENCES = {
    # El «García» del Racing es ahora Pablo, un fichaje de última hora.
    ("Racing de Santander", "mario garcia"),
}

CSV_FIELDS = [
    "id",
    "seccion",
    "numero",
    "nombre",
    "club_objetivo",
    "estado_laliga",
    "clave_laliga",
    "coincidencia_laliga",
    "dorsal_laliga",
    "posicion_laliga",
    "confianza_laliga",
    "comprobado_en",
    "notas_laliga",
]

# Columnas que este script devuelve a `laliga_plantillas.csv`.
STICKER_FIELDS = [
    "cromo_id",
    "cromo_seccion",
    "cromo_numero",
    "cromo_nombre",
    "cromos",
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
    clave: str
    nombre: str
    apodo: str
    dorsal: str
    posicion: str
    keys: frozenset[str]


@dataclass(frozen=True)
class Match:
    estado: str
    clave: str
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


def load_squads(path: Path) -> tuple[list[dict[str, str]], dict[str, list[SquadMember]]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    squads: dict[str, list[SquadMember]] = {}
    for row in rows:
        section = row.get("seccion_album", "")
        if not section:
            continue
        squads.setdefault(section, []).append(
            SquadMember(
                clave=row.get("clave", ""),
                nombre=row.get("nombre", ""),
                apodo=row.get("apodo", ""),
                dorsal=row.get("dorsal", ""),
                posicion=row.get("posicion", ""),
                keys=member_keys(row),
            )
        )
    if not squads:
        raise ValueError(f"{path} no contiene plantillas; ejecuta antes generar_plantillas_laliga.py.")
    return rows, squads


def miss(estado: str, candidato: str, confianza: float, notas: str) -> Match:
    return Match(estado, "", candidato, "", "", confianza, notas)


def hit(member: SquadMember, confidence: float, notes: str) -> Match:
    return Match(
        IN_SQUAD,
        member.clave,
        member.nombre or member.apodo,
        member.dorsal,
        member.posicion,
        confidence,
        notes,
    )


def member_words(member: SquadMember) -> set[str]:
    return {word for key in member.keys for word in key.split()}


def similar_word(word: str, known: set[str]) -> bool:
    """¿Esta palabra del cromo describe al mismo jugador?

    Panini abrevia («Rodri» por «Rodrigo»), recorta («Alti» por «Altimira») y a
    veces se equivoca al teclear («Franisco»). Lo que no hace es cambiar el
    nombre por otro distinto, así que un «Mario» que no se parece a nada de la
    ficha significa que es otra persona."""
    for other in known:
        if word == other:
            return True
        if len(word) >= 3 and len(other) >= 3 and (
            word.startswith(other) or other.startswith(word)
        ):
            return True
        if difflib.SequenceMatcher(None, word, other).ratio() >= 0.85:
            return True
    return False


def describes_member(target: str, member: SquadMember) -> bool:
    known = member_words(member)
    return all(similar_word(word, known) for word in target.split())


def match_member(name: str, squad: list[SquadMember]) -> Match:
    raw_target = normalize_name(name)
    if not raw_target:
        return miss(UNPUBLISHED, "", 0.0, "Cromo sin nombre.")

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
            return miss(
                DOUBTFUL,
                ", ".join(member.nombre for member in exact),
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
            and describes_member(target, member)
        ]
        if len(contained) == 1:
            return hit(contained[0], 0.96, "Coincidencia única por nombre parcial.")
        if len(contained) > 1:
            return miss(
                DOUBTFUL,
                ", ".join(member.nombre for member in contained),
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
        return miss(NO_SQUAD, "", 0.0, "La plantilla llegó vacía.")
    if best_score >= 0.86:
        return hit(best_member, best_score, "Coincidencia aproximada de alta confianza.")
    if best_score >= 0.68:
        return miss(
            DOUBTFUL,
            best_member.nombre,
            best_score,
            "Posible coincidencia; confírmala antes de descartar el cromo.",
        )
    if len(raw_target) < MIN_ABSENCE_LENGTH:
        return miss(
            DOUBTFUL,
            best_member.nombre,
            best_score,
            "Nombre demasiado corto para descartarlo con seguridad.",
        )
    return miss(
        OUT_OF_SQUAD,
        best_member.nombre,
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
            match = miss(UNPUBLISHED, "", 0.0, "Hueco sin jugador.")
        elif name == "Escudo":
            match = miss(NOT_APPLICABLE, "", 0.0, "El escudo no es un jugador.")
        elif (row.get("club_objetivo", ""), normalize_name(name)) in KNOWN_ABSENCES:
            match = miss(
                OUT_OF_SQUAD,
                "",
                0.0,
                "Comprobado a mano: otro jugador con el mismo apellido ocupa su sitio.",
            )
        else:
            section = section_for(row, squads)
            match = (
                match_member(name, squads[section])
                if section
                else miss(NO_SQUAD, "", 0.0, "Sin club que comprobar.")
            )
        results.append(
            {
                "id": row["id"],
                "seccion": row["seccion"],
                "numero": row["numero"],
                "nombre": name,
                "club_objetivo": row.get("club_objetivo", ""),
                "estado_laliga": match.estado,
                "clave_laliga": match.clave,
                "coincidencia_laliga": match.candidato,
                "dorsal_laliga": match.dorsal,
                "posicion_laliga": match.posicion,
                "confianza_laliga": f"{match.confianza:.4f}",
                "comprobado_en": checked_on_text,
                "notas_laliga": match.notas,
            }
        )
    return results


def stickers_by_member(results: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Índice inverso: qué cromos representan a cada ficha de LALIGA.

    Un jugador puede tener el cromo de su equipo y además el de Últimos
    Fichajes; el del equipo manda porque es el hueco fijo del álbum."""
    by_member: dict[str, list[dict[str, str]]] = {}
    for result in results:
        if not result["clave_laliga"] or result["seccion"] not in SQUAD_SECTIONS:
            continue
        by_member.setdefault(result["clave_laliga"], []).append(result)
    for stickers in by_member.values():
        stickers.sort(key=lambda item: item["seccion"] == "ÚLTIMOS FICHAJES")
    return by_member


def link_stickers(
    squad_rows: list[dict[str, str]],
    results: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_member = stickers_by_member(results)
    linked: list[dict[str, str]] = []
    for row in squad_rows:
        stickers = by_member.get(row.get("clave", ""), [])
        primary = stickers[0] if stickers else {}
        linked.append(
            {
                **row,
                "cromo_id": primary.get("id", ""),
                "cromo_seccion": primary.get("seccion", ""),
                "cromo_numero": primary.get("numero", ""),
                "cromo_nombre": primary.get("nombre", ""),
                "cromos": "; ".join(
                    f"{sticker['seccion']} {sticker['numero']}" for sticker in stickers
                ),
            }
        )
    return linked


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def generate(
    collection_path: Path,
    squads_path: Path,
    output_path: Path,
    teams_path: Path | None = None,
    sql_path: Path | None = None,
    checked_on: date | None = None,
) -> dict[str, int]:
    rows = read_csv(collection_path)
    squad_rows, squads = load_squads(squads_path)
    results = check_rows(rows, squads, checked_on or date.today())
    write_csv(results, output_path)

    linked = link_stickers(squad_rows, results)
    write_squad_csv(linked, PLAYER_FIELDS, squads_path)
    if teams_path and sql_path and teams_path.exists():
        write_sql(
            read_csv(teams_path), linked, sql_path, datetime.now(timezone.utc)
        )

    counts: dict[str, int] = {}
    for result in results:
        counts[result["estado_laliga"]] = counts.get(result["estado_laliga"], 0) + 1
    counts["fichas_con_cromo"] = sum(bool(row["cromo_id"]) for row in linked)
    counts["fichas_sin_cromo"] = sum(not row["cromo_id"] for row in linked)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Empareja el checklist Panini con las plantillas oficiales de LALIGA "
            "en las dos direcciones."
        )
    )
    parser.add_argument(
        "--coleccion", type=Path, default=Path("coleccion_panini_revisada.csv")
    )
    parser.add_argument(
        "--plantillas", type=Path, default=Path("laliga_plantillas.csv")
    )
    parser.add_argument("--equipos", type=Path, default=Path("laliga_equipos.csv"))
    parser.add_argument("--salida", type=Path, default=Path("comprobacion_laliga.csv"))
    parser.add_argument(
        "--sql", type=Path, default=Path("supabase/laliga_plantillas.sql")
    )
    args = parser.parse_args()

    counts = generate(
        args.coleccion, args.plantillas, args.salida, args.equipos, args.sql
    )
    print(f"Generados {args.salida}, {args.plantillas} y {args.sql}:")
    for estado, total in sorted(counts.items()):
        print(f"- {estado}: {total}")


if __name__ == "__main__":
    main()
