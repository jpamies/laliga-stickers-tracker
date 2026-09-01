from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

import pymupdf


CLUB_SECTIONS = [
    "DEPORTIVO ALAVÉS",
    "ATHLETIC CLUB DE BILBAO",
    "ATLÉTICO DE MADRID",
    "FC BARCELONA",
    "REAL BETIS",
    "RC CELTA DE VIGO",
    "DEPORTIVO",
    "ELCHE CF",
    "RCD ESPANYOL",
    "GETAFE CF",
    "LEVANTE UD",
    "REAL MADRID CF",
    "MALAGA CF",
    "OSASUNA",
    "RACING DE SANTANDER",
    "RAYO VALLECANO",
    "REAL SOCIEDAD",
    "SEVILLA",
    "VALENCIA",
    "VILLARREAL",
]

SPECIAL_SECTIONS = [
    "ÚLTIMOS FICHAJES",
    "ADN / LALIGA PRIME",
    "LALIGA FANTASY",
    "DRAFT 23",
    "DRAFT 23 KROMIX",
    "EXTRA STICKER BRONCE",
    "EXTRA STICKER PLATA",
    "EXTRA STICKER ORO",
]

CLUB_CANONICAL = {
    "DEPORTIVO ALAVÉS": "Deportivo Alavés",
    "ATHLETIC CLUB DE BILBAO": "Athletic Club",
    "ATLÉTICO DE MADRID": "Atlético de Madrid",
    "FC BARCELONA": "FC Barcelona",
    "REAL BETIS": "Real Betis",
    "RC CELTA DE VIGO": "RC Celta de Vigo",
    "DEPORTIVO": "Deportivo de La Coruña",
    "ELCHE CF": "Elche CF",
    "RCD ESPANYOL": "RCD Espanyol",
    "GETAFE CF": "Getafe CF",
    "LEVANTE UD": "Levante UD",
    "REAL MADRID CF": "Real Madrid",
    "MALAGA CF": "Málaga CF",
    "OSASUNA": "CA Osasuna",
    "RACING DE SANTANDER": "Racing de Santander",
    "RAYO VALLECANO": "Rayo Vallecano",
    "REAL SOCIEDAD": "Real Sociedad",
    "SEVILLA": "Sevilla FC",
    "VALENCIA": "Valencia CF",
    "VILLARREAL": "Villarreal CF",
}

SPECIAL_CLUB_ALIASES = {
    "Alavés": "Deportivo Alavés",
    "Athletic": "Athletic Club",
    "Atlético": "Atlético de Madrid",
    "Atlético de Madrid": "Atlético de Madrid",
    "Barcelona": "FC Barcelona",
    "Betis": "Real Betis",
    "Celta": "RC Celta de Vigo",
    "Deportivo": "Deportivo de La Coruña",
    "Elche": "Elche CF",
    "Espanyol": "RCD Espanyol",
    "Getafe": "Getafe CF",
    "Levante": "Levante UD",
    "Malaga": "Málaga CF",
    "Málaga": "Málaga CF",
    "Osasuna": "CA Osasuna",
    "Racing de Santander": "Racing de Santander",
    "Rayo Vallecano": "Rayo Vallecano",
    "Real Madrid": "Real Madrid",
    "Real Sociedad": "Real Sociedad",
    "Sevilla": "Sevilla FC",
    "Valencia": "Valencia CF",
    "Villarreal": "Villarreal CF",
}

POSITIONS = {"entrenador", "portero", "defensa", "medio", "delantero"}
NUMBER_RE = re.compile(r"^(?:\d+(?:BIS|[AB])?|UF\d+|K\d+)$")
SPECIAL_NAME_RE = re.compile(r"^(.*?)\s+\(([^()]*)\)$")
EDITION_MARKER_RE = re.compile(r"^2[ªa]\s*ed\.?$")
SECOND_EDITION = "2ed"

# Los huecos de ÚLTIMOS FICHAJES existían como marcadores generados por
# generar_album.py antes de que Panini publicara los nombres. Reutilizamos sus
# identificadores para no perder el progreso ya guardado.
LEGACY_ID_ALIASES = {
    ("ÚLTIMOS FICHAJES", f"UF{number}"): f"ULTIMOS-FICHAJES-{number:02d}"
    for number in range(1, 67)
}

CSV_FIELDS = [
    "id",
    "seccion",
    "numero",
    "hueco_album",
    "variante",
    "nombre",
    "tipo",
    "club_objetivo",
    "edicion",
    "estado_plantilla",
    "accion",
    "coincidencia_transfermarkt",
    "confianza",
    "comprobado_en",
    "notas",
]


@dataclass
class Sticker:
    id: str
    seccion: str
    numero: str
    hueco_album: str
    variante: str
    nombre: str
    tipo: str
    club_objetivo: str
    edicion: str
    estado_plantilla: str
    accion: str
    coincidencia_transfermarkt: str = ""
    confianza: str = ""
    comprobado_en: str = ""
    notas: str = ""


def normalize(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    ).casefold()


SECTION_BY_NORMALIZED = {
    normalize(section): section for section in CLUB_SECTIONS + SPECIAL_SECTIONS
}


def extract_lines(pdf_path: Path) -> list[str]:
    with pymupdf.open(pdf_path) as document:
        lines = [
            line.strip()
            for page in document
            for line in page.get_text("text").splitlines()
            if line.strip()
        ]

    merged: list[str] = []
    index = 0
    while index < len(lines):
        if (
            lines[index].casefold() == "extra"
            and index + 1 < len(lines)
            and lines[index + 1].casefold() == "sticker"
        ):
            merged.append("Extra Sticker")
            index += 2
        else:
            merged.append(lines[index])
            index += 1
    return merged


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    for line in lines:
        section = SECTION_BY_NORMALIZED.get(normalize(line))
        if section:
            current_section = section
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)

    missing = set(CLUB_SECTIONS + SPECIAL_SECTIONS) - sections.keys()
    if missing:
        raise ValueError(f"No se encontraron estas secciones en el PDF: {sorted(missing)}")
    return sections


def is_number(line: str) -> bool:
    return bool(NUMBER_RE.fullmatch(line)) or line == "Extra Sticker"


def parse_number(number: str) -> tuple[str, str]:
    match = re.fullmatch(r"(\d+)(BIS|[AB])?", number)
    if match:
        return match.group(1), match.group(2) or ""
    match = re.fullmatch(r"UF(\d+)", number)
    if match:
        return match.group(1), ""
    return number, ""


@dataclass
class Entry:
    numero: str
    nombre: str
    tipo: str
    edicion: str = ""


def parse_entries(section: str, lines: list[str]) -> list[Entry]:
    entries: list[Entry] = []
    pending_number: str | None = None
    pending_edition = ""
    name_parts: list[str] = []

    def flush(kind: str = "") -> None:
        nonlocal pending_number, pending_edition, name_parts
        if pending_number is None:
            return
        entries.append(
            Entry(pending_number, " ".join(name_parts).strip(), kind, pending_edition)
        )
        pending_number = None
        pending_edition = ""
        name_parts = []

    for line in lines:
        if EDITION_MARKER_RE.fullmatch(normalize(line).strip()):
            if pending_number is not None:
                pending_edition = SECOND_EDITION
            elif entries:
                entries[-1].edicion = SECOND_EDITION
            else:
                raise ValueError(f"Marca de edición sin cromo en {section}: {line!r}")
            continue

        if is_number(line):
            flush()
            pending_number = line
            continue

        normalized_line = normalize(line)
        if normalized_line in POSITIONS:
            if pending_number is None:
                raise ValueError(f"Posición sin número en {section}: {line!r}")
            flush(normalized_line)
        elif pending_number is not None:
            name_parts.append(line)

    flush()
    return entries


def club_and_name(section: str, raw_name: str) -> tuple[str, str]:
    if section in CLUB_CANONICAL:
        return CLUB_CANONICAL[section], raw_name

    match = SPECIAL_NAME_RE.fullmatch(raw_name)
    if not match:
        return "", raw_name
    name, raw_club = match.groups()
    if name.isupper():
        name = name.title()
    return SPECIAL_CLUB_ALIASES.get(raw_club, raw_club), name


def initial_status(name: str, kind: str) -> tuple[str, str, str]:
    if not name:
        return "pendiente_publicacion", "ESPERAR", "Hueco sin jugador en el checklist."
    if kind in {"entrenador"} or name == "Escudo":
        return "no_aplica", "PEGAR", "La comprobación de plantilla solo cubre jugadores."
    return "sin_comprobar", "PEGAR", ""


def load_known_ids(csv_path: Path | None) -> dict[tuple[str, str, int], str]:
    """IDs ya publicados, indexados por (sección, número, repetición).

    El progreso del álbum se guarda por identificador, así que un cromo nuevo
    del checklist nunca debe desplazar el ID de uno anterior. Algunas secciones
    repiten número (los «Extra Sticker»), de ahí el contador de repetición."""
    known: dict[tuple[str, str, int], str] = {
        (section, number, 1): identifier
        for (section, number), identifier in LEGACY_ID_ALIASES.items()
    }
    if not csv_path or not csv_path.exists():
        return known
    repeats: Counter[tuple[str, str]] = Counter()
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if not row.get("id"):
                continue
            key = (row["seccion"], row["numero"])
            repeats[key] += 1
            known[(*key, repeats[key])] = row["id"]
    return known


def section_identifier(section: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", normalize(section).upper()).strip("-")


def build_stickers(
    sections: dict[str, list[str]],
    known_ids: dict[tuple[str, str, int], str] | None = None,
) -> list[Sticker]:
    known_ids = known_ids or {}
    parsed: list[tuple[str, Entry]] = [
        (section, entry)
        for section in CLUB_SECTIONS + SPECIAL_SECTIONS
        for entry in parse_entries(section, sections[section])
    ]

    repeats: Counter[tuple[str, str]] = Counter()
    assigned: list[str | None] = []
    for section, entry in parsed:
        repeats[(section, entry.numero)] += 1
        key = (section, entry.numero, repeats[(section, entry.numero)])
        assigned.append(known_ids.get(key))

    used = {identifier for identifier in assigned if identifier}
    counters: Counter[str] = Counter()
    for index, (section, _) in enumerate(parsed):
        if assigned[index]:
            continue
        section_id = section_identifier(section)
        while True:
            counters[section_id] += 1
            candidate = f"{section_id}-{counters[section_id]:02d}"
            if candidate not in used:
                break
        used.add(candidate)
        assigned[index] = candidate

    stickers: list[Sticker] = []
    for identifier, (section, entry) in zip(assigned, parsed):
        slot, variant = parse_number(entry.numero)
        club, name = club_and_name(section, entry.nombre)
        status, action, notes = initial_status(name, entry.tipo)
        stickers.append(
            Sticker(
                id=str(identifier),
                seccion=section,
                numero=entry.numero,
                hueco_album=slot,
                variante=variant,
                nombre=name,
                tipo=entry.tipo,
                club_objetivo=club,
                edicion=entry.edicion,
                estado_plantilla=status,
                accion=action,
                notas=notes,
            )
        )
    return stickers


def write_csv(stickers: list[Sticker], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(asdict(sticker) for sticker in stickers)


def markdown_escape(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")


def write_markdown(stickers: list[Sticker], output_path: Path) -> None:
    entry_total = len(stickers)
    named_total = sum(bool(item.nombre) for item in stickers)
    album_slots = len({(item.seccion, item.hueco_album) for item in stickers})
    alternatives = sum(bool(item.variante) for item in stickers)
    second_edition = sum(item.edicion == SECOND_EDITION for item in stickers)
    blanks = sum(not item.nombre for item in stickers)

    lines = [
        "# Checklist Panini LALIGA 2026-27",
        "",
        f"- **Entradas y variantes del checklist:** {entry_total}",
        f"- **Cromos con nombre o contenido asignado:** {named_total}",
        f"- **Huecos de álbum:** {album_slots}",
        f"- **Cromos con variante A/B/BIS:** {alternatives}",
        f"- **Cromos añadidos en la 2ª edición:** {second_edition}",
        f"- **Cromos todavía sin nombre:** {blanks}",
        "",
        "## Leyenda de estrategia",
        "",
        "- **PEGAR:** recomendación por defecto para cualquier cromo con contenido.",
        "- **ESPERAR:** Panini todavía no ha asignado un jugador al hueco.",
        "",
        "> Nunca se recomienda automáticamente *no pegar* ni *revisar*: la "
        "recomendación es siempre pegar y la decisión de descartar un cromo es "
        "personal y se marca a mano en el álbum. El detalle de la comprobación "
        "queda en `estado_plantilla` y en las notas.",
        "",
        "> El estado inicial procede únicamente del checklist. Ejecuta "
        "`python comprobar_plantillas.py` para generar la versión revisada.",
        "",
    ]

    for section in CLUB_SECTIONS + SPECIAL_SECTIONS:
        lines.extend(
            [
                f"## {section}",
                "",
                "| Nº | Variante | Nombre | Tipo | Club a comprobar | Edición | Estado | Acción |",
                "|---:|:---:|---|---|---|:---:|---|:---:|",
            ]
        )
        for item in (sticker for sticker in stickers if sticker.seccion == section):
            values = [
                item.numero,
                item.variante or "—",
                item.nombre or "—",
                item.tipo or "—",
                item.club_objetivo or "—",
                item.edicion or "1ª",
                item.estado_plantilla,
                item.accion,
            ]
            lines.append("| " + " | ".join(markdown_escape(value) for value in values) + " |")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def validate(stickers: list[Sticker]) -> None:
    for club_section in CLUB_SECTIONS:
        slots = {
            item.hueco_album
            for item in stickers
            if item.seccion == club_section
        }
        expected = {str(number) for number in range(1, 21)}
        if slots != expected:
            raise ValueError(
                f"{club_section} no tiene exactamente los huecos 1-20: "
                f"faltan {sorted(expected - slots)}, sobran {sorted(slots - expected)}"
            )

    ids = [item.id for item in stickers]
    if len(ids) != len(set(ids)):
        raise ValueError("Se generaron identificadores de cromo duplicados.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae el checklist oficial Panini a CSV y Markdown."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("Checklist_LALIGA_2026-27-2aED.pdf"),
    )
    parser.add_argument("--csv", type=Path, default=Path("coleccion_panini.csv"))
    parser.add_argument(
        "--markdown", type=Path, default=Path("coleccion_panini.md")
    )
    parser.add_argument(
        "--ids-previos",
        type=Path,
        default=Path("coleccion_panini.csv"),
        help="CSV del que reutilizar los identificadores ya publicados.",
    )
    args = parser.parse_args()

    stickers = build_stickers(
        split_sections(extract_lines(args.pdf)),
        load_known_ids(args.ids_previos),
    )
    validate(stickers)
    write_csv(stickers, args.csv)
    write_markdown(stickers, args.markdown)
    second_edition = sum(item.edicion == SECOND_EDITION for item in stickers)
    print(
        f"Generados {args.csv} y {args.markdown}: "
        f"{len(stickers)} entradas y variantes ({second_edition} de la 2ª edición)."
    )


if __name__ == "__main__":
    main()
