from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from extraer_checklist import CSV_FIELDS, markdown_escape


TRANSFERMARKT_CLUB_IDS = {
    "Deportivo Alavés": ("deportivo-alaves", 1108),
    "Athletic Club": ("athletic-bilbao", 621),
    "Atlético de Madrid": ("atletico-de-madrid", 13),
    "FC Barcelona": ("fc-barcelona", 131),
    "Real Betis": ("real-betis-sevilla", 150),
    "RC Celta de Vigo": ("celta-vigo", 940),
    "Deportivo de La Coruña": ("deportivo-la-coruna", 897),
    "Elche CF": ("fc-elche", 1531),
    "RCD Espanyol": ("rcd-espanyol-barcelona", 714),
    "Getafe CF": ("fc-getafe", 3709),
    "Levante UD": ("ud-levante", 3368),
    "Real Madrid": ("real-madrid", 418),
    "Málaga CF": ("fc-malaga", 1084),
    "CA Osasuna": ("ca-osasuna", 331),
    "Racing de Santander": ("racing-santander", 630),
    "Rayo Vallecano": ("rayo-vallecano", 367),
    "Real Sociedad": ("real-sociedad-san-sebastian", 681),
    "Sevilla FC": ("fc-sevilla", 368),
    "Valencia CF": ("fc-valencia", 1049),
    "Villarreal CF": ("fc-villarreal", 1050),
}

NAME_ALIASES = {
    "alex sancris": "alejandro sanchez lopez",
    "alvaro fernandez": "alvaro ferllo",
    "cholo simeone": "diego simeone",
    "fede redondo": "federico redondo",
    "fede valverde": "federico valverde",
    "fer lopez": "fernando lopez",
    "gonzalo": "gonzalo garcia",
    "isi": "isi palazon",
    "joao cancelo": "joao cancelo",
    "koke": "koke",
    "marcao": "marcao",
    "pepe": "nicolas pepe",
    "sorloth": "alexander sorloth",
    "trent": "trent alexander arnold",
    "valles": "alvaro valles",
    "vinicius": "vinicius junior",
    "williams": "inaki williams",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0 Safari/537.36"
)


@dataclass(frozen=True)
class Match:
    status: str
    action: str
    candidate: str
    confidence: float
    notes: str


def normalize_name(value: str) -> str:
    value = value.replace("ø", "o").replace("Ø", "O")
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    words = re.findall(r"[a-z0-9]+", without_accents.casefold())
    return " ".join(words)


def transfermarkt_url(club: str, season: int) -> str:
    slug, club_id = TRANSFERMARKT_CLUB_IDS[club]
    return (
        f"https://www.transfermarkt.es/{slug}/kader/verein/"
        f"{club_id}/saison_id/{season}/plus/1"
    )


def fetch_squad(
    session: requests.Session,
    club: str,
    season: int,
    cache_dir: Path,
    refresh: bool,
) -> str:
    url = transfermarkt_url(club, season)
    cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    cache_path = cache_dir / f"{season}_{cache_key}.html"
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8")

    response = session.get(url, timeout=30)
    response.raise_for_status()
    if "Transfermarkt" not in response.text:
        raise RuntimeError(f"Respuesta inesperada al consultar {club}: {url}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    return response.text


def parse_squad(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    names: list[str] = []
    for row in soup.select("table.items tbody tr"):
        links = row.select('a[href*="/profil/spieler/"]')
        if not links:
            continue
        preferred = row.select_one('td.hauptlink a[href*="/profil/spieler/"]')
        link = preferred or links[0]
        name = link.get("title") or link.get_text(" ", strip=True)
        if name and name not in names:
            names.append(name)
    if not names:
        raise ValueError("Transfermarkt no devolvió jugadores en la tabla de plantilla.")
    return names


def match_player(sticker_name: str, squad: list[str]) -> Match:
    raw_target = normalize_name(sticker_name)
    normalized_squad = [(name, normalize_name(name)) for name in squad]

    for original, normalized in normalized_squad:
        if raw_target == normalized:
            return Match("en_plantilla", "PEGAR", original, 1.0, "Coincidencia exacta.")

    target = NAME_ALIASES.get(raw_target, raw_target)
    if target != raw_target:
        for original, normalized in normalized_squad:
            if target == normalized:
                return Match(
                    "en_plantilla",
                    "PEGAR",
                    original,
                    0.99,
                    "Coincidencia exacta mediante alias conocido.",
                )

    containment = [
        (original, normalized)
        for original, normalized in normalized_squad
        if target in normalized or normalized in target
    ]
    if len(containment) == 1 and len(target) >= 4:
        original, _ = containment[0]
        return Match(
            "en_plantilla",
            "PEGAR",
            original,
            0.96,
            "Coincidencia única por nombre parcial.",
        )
    if len(containment) > 1:
        candidates = ", ".join(original for original, _ in containment)
        return Match(
            "coincidencia_ambigua",
            "REVISAR",
            candidates,
            0.5,
            "El nombre parcial coincide con varios jugadores.",
        )

    scores = sorted(
        (
            difflib.SequenceMatcher(None, target, normalized).ratio(),
            original,
        )
        for original, normalized in normalized_squad
    )
    best_score, best_name = scores[-1]
    if best_score >= 0.86:
        return Match(
            "en_plantilla",
            "PEGAR",
            best_name,
            best_score,
            "Coincidencia aproximada de alta confianza.",
        )
    if best_score >= 0.68:
        return Match(
            "coincidencia_dudosa",
            "REVISAR",
            best_name,
            best_score,
            "Posible coincidencia; no pegar hasta revisarla.",
        )
    return Match(
        "no_encontrado",
        "NO PEGAR",
        best_name,
        best_score,
        "No aparece en la plantilla de Transfermarkt.",
    )


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = set(CSV_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Faltan columnas en {csv_path}: {sorted(missing)}")
        return list(reader)


def write_rows(rows: list[dict[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_review_markdown(
    rows: list[dict[str, str]],
    output_path: Path,
    checked_on: date,
) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["accion"]] = counts.get(row["accion"], 0) + 1

    lines = [
        "# Estrategia Panini LALIGA 2026-27",
        "",
        f"Comprobación realizada: **{checked_on.isoformat()}**.",
        "",
        f"- **PEGAR:** {counts.get('PEGAR', 0)}",
        f"- **NO PEGAR:** {counts.get('NO PEGAR', 0)}",
        f"- **REVISAR:** {counts.get('REVISAR', 0)}",
        f"- **ESPERAR:** {counts.get('ESPERAR', 0)}",
        "",
        "> Transfermarkt es una fuente externa y puede tardar en reflejar un fichaje. "
        "Antes de descartar definitivamente un cromo marcado NO PEGAR, revisa la fecha.",
        "",
    ]

    section = None
    for row in rows:
        if row["seccion"] != section:
            if section is not None:
                lines.append("")
            section = row["seccion"]
            lines.extend(
                [
                    f"## {section}",
                    "",
                    "| Nº | Nombre | Club | Estado | Acción | Coincidencia | Confianza |",
                    "|---:|---|---|---|:---:|---|---:|",
                ]
            )
        confidence = (
            f"{float(row['confianza']):.0%}" if row["confianza"] else "—"
        )
        values = [
            row["numero"],
            row["nombre"] or "—",
            row["club_objetivo"] or "—",
            row["estado_plantilla"],
            row["accion"],
            row["coincidencia_transfermarkt"] or "—",
            confidence,
        ]
        lines.append("| " + " | ".join(markdown_escape(value) for value in values) + " |")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def check_rows(
    rows: list[dict[str, str]],
    squads: dict[str, list[str]],
    checked_on: date,
) -> list[dict[str, str]]:
    checked_on_text = checked_on.isoformat()
    for row in rows:
        if row["tipo"] == "entrenador" or row["nombre"] == "Escudo":
            continue
        if not row["nombre"]:
            continue
        club = row["club_objetivo"]
        if club not in squads:
            row["estado_plantilla"] = "club_no_disponible"
            row["accion"] = "REVISAR"
            row["notas"] = "No se pudo obtener la plantilla de este club."
            continue

        match = match_player(row["nombre"], squads[club])
        row["estado_plantilla"] = match.status
        row["accion"] = match.action
        row["coincidencia_transfermarkt"] = match.candidate
        row["confianza"] = f"{match.confidence:.4f}"
        row["comprobado_en"] = checked_on_text
        row["notas"] = match.notes
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Contrasta el checklist Panini con las plantillas de Transfermarkt."
    )
    parser.add_argument("--entrada", type=Path, default=Path("coleccion_panini.csv"))
    parser.add_argument(
        "--salida-csv",
        type=Path,
        default=Path("coleccion_panini_revisada.csv"),
    )
    parser.add_argument(
        "--salida-markdown",
        type=Path,
        default=Path("coleccion_panini_revisada.md"),
    )
    parser.add_argument(
        "--temporada",
        type=int,
        default=2026,
        help="Año inicial de la temporada; para 2026-27 usa 2026.",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".cache_transfermarkt"),
    )
    parser.add_argument(
        "--refrescar",
        action="store_true",
        help="Ignora la caché y vuelve a consultar las 20 plantillas.",
    )
    parser.add_argument(
        "--pausa",
        type=float,
        default=1.0,
        help="Segundos entre peticiones para no sobrecargar Transfermarkt.",
    )
    parser.add_argument(
        "--fecha",
        type=date.fromisoformat,
        default=date.today(),
        help="Fecha de comprobación en formato AAAA-MM-DD.",
    )
    args = parser.parse_args()

    rows = load_rows(args.entrada)
    required_clubs = sorted(
        {row["club_objetivo"] for row in rows if row["club_objetivo"]}
    )
    unknown = set(required_clubs) - TRANSFERMARKT_CLUB_IDS.keys()
    if unknown:
        raise ValueError(f"Faltan identificadores de Transfermarkt: {sorted(unknown)}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"})
    squads: dict[str, list[str]] = {}
    errors: list[str] = []
    for index, club in enumerate(required_clubs):
        try:
            html = fetch_squad(
                session, club, args.temporada, args.cache, args.refrescar
            )
            squads[club] = parse_squad(html)
            print(f"{club}: {len(squads[club])} jugadores")
        except (requests.RequestException, RuntimeError, ValueError) as error:
            message = f"{club}: {error}"
            errors.append(message)
            print(f"ERROR - {message}")
        if index + 1 < len(required_clubs):
            time.sleep(args.pausa)

    checked_rows = check_rows(rows, squads, args.fecha)
    write_rows(checked_rows, args.salida_csv)
    write_review_markdown(checked_rows, args.salida_markdown, args.fecha)
    print(f"Generados {args.salida_csv} y {args.salida_markdown}.")
    if errors:
        raise SystemExit(
            f"La revisión terminó con {len(errors)} clubes no disponibles; "
            "sus cromos quedan marcados REVISAR."
        )


if __name__ == "__main__":
    main()
