from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from comprobar_plantillas import (
    TRANSFERMARKT_CLUB_IDS,
    USER_AGENT,
    fetch_squad,
    match_player,
    normalize_name,
    transfermarkt_url,
)
from extraer_checklist import CLUB_CANONICAL, CLUB_SECTIONS


BESOCCER_URL = "https://es.besoccer.com/fichajes/altas-y-bajas/primera"
BESOCCER_CLUBS = {
    "Athletic Club": "Athletic Club",
    "Atlético de Madrid": "Atlético de Madrid",
    "Celta": "RC Celta de Vigo",
    "Deportivo Alavés": "Deportivo Alavés",
    "Elche": "Elche CF",
    "Espanyol": "RCD Espanyol",
    "FC Barcelona": "FC Barcelona",
    "Getafe": "Getafe CF",
    "Levante": "Levante UD",
    "Málaga": "Málaga CF",
    "Osasuna": "CA Osasuna",
    "Racing": "Racing de Santander",
    "Rayo Vallecano": "Rayo Vallecano",
    "RC Deportivo": "Deportivo de La Coruña",
    "Real Betis": "Real Betis",
    "Real Madrid": "Real Madrid",
    "Real Sociedad": "Real Sociedad",
    "Sevilla": "Sevilla FC",
    "Valencia": "Valencia CF",
    "Villarreal": "Villarreal CF",
}
SECTION_BY_CLUB = {club: section for section, club in CLUB_CANONICAL.items()}

FIELDS = [
    "orden",
    "id",
    "tipo_registro",
    "seccion",
    "numero",
    "hueco_album",
    "variante",
    "nombre",
    "tipo",
    "club_album",
    "tiene_cromo_fisico",
    "estado_coleccion",
    "copias",
    "estado_mercado",
    "accion_estrategia",
    "club_origen",
    "club_destino",
    "tipo_movimiento",
    "importe_movimiento",
    "fecha_movimiento",
    "en_plantilla_transfermarkt",
    "coincidencia_transfermarkt",
    "coincidencia_besoccer",
    "confianza",
    "fuente_plantilla",
    "fuente_movimiento",
    "comprobado_en",
    "notas",
]


@dataclass(frozen=True)
class SquadPlayer:
    name: str
    position: str


@dataclass(frozen=True)
class Movement:
    club: str
    direction: str
    player: str
    other_club: str
    movement_type: str
    amount: str
    movement_date: str
    source_url: str


def parse_squad_details(html: str) -> list[SquadPlayer]:
    soup = BeautifulSoup(html, "html.parser")
    players: list[SquadPlayer] = []
    seen: set[str] = set()
    for row in soup.select("table.items tbody > tr"):
        cell = row.select_one("td.posrela")
        link = cell.select_one('td.hauptlink a[href*="/profil/spieler/"]') if cell else None
        if not cell or not link:
            continue
        name = link.get("title") or link.get_text(" ", strip=True)
        position_cell = cell.select_one("table.inline-table tr:nth-of-type(2) td")
        position = position_cell.get_text(" ", strip=True) if position_cell else ""
        key = normalize_name(name)
        if name and key not in seen:
            seen.add(key)
            players.append(SquadPlayer(name, position))
    if not players:
        raise ValueError("Transfermarkt no devolvió jugadores en la tabla de plantilla.")
    return players


def split_transfer_detail(value: str) -> tuple[str, str]:
    clean = " ".join(value.split())
    match = re.match(r"^(.*?\.)\s*(.*)$", clean)
    if not match:
        return clean.rstrip("."), ""
    movement_type = match.group(1).rstrip(".")
    amount = match.group(2)
    return movement_type, amount


def parse_besoccer_transfers(html: str) -> list[Movement]:
    soup = BeautifulSoup(html, "html.parser")
    movements: list[Movement] = []
    for head in soup.select("#transfers-panel > .panel-head"):
        title = head.select_one(".panel-title")
        body = head.find_next_sibling("div", class_="panel-body")
        if not title or not body:
            continue
        raw_club = title.get_text(" ", strip=True)
        club = BESOCCER_CLUBS.get(raw_club)
        if not club:
            continue
        for column in body.select("td"):
            direction_node = column.select_one(".table-head")
            if not direction_node:
                continue
            direction = direction_node.get_text(" ", strip=True).casefold()
            for item in column.select("li.sign-list"):
                name_node = item.select_one(".pl-name")
                if not name_node:
                    continue
                date_node = item.select_one(".date")
                other_node = item.select_one(".right-content .shield img")
                detail = " ".join(
                    node.get_text(" ", strip=True)
                    for node in item.select(".data-transfer p")
                )
                movement_type, amount = split_transfer_detail(detail)
                movements.append(
                    Movement(
                        club=club,
                        direction="ALTA" if direction == "alta" else "BAJA",
                        player=name_node.get_text(" ", strip=True),
                        other_club=other_node.get("alt", "").strip() if other_node else "",
                        movement_type=movement_type,
                        amount=amount,
                        movement_date=(
                            date_node.get_text(" ", strip=True) if date_node else ""
                        ),
                        source_url=BESOCCER_URL,
                    )
                )
    if not movements:
        raise ValueError("BeSoccer no devolvió movimientos de mercado.")
    return movements


def fetch_besoccer(cache_path: Path, refresh: bool) -> str:
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8")
    response = requests.get(
        BESOCCER_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "es-ES,es;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )
    response.raise_for_status()
    if "transfers-panel" not in response.text:
        raise RuntimeError("Respuesta inesperada al consultar BeSoccer.")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    return response.text


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def load_progress(path: Path | None) -> dict[str, dict[str, object]]:
    if not path:
        return {}
    with path.open(encoding="utf-8-sig") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError("El progreso debe ser un objeto JSON indexado por ID.")
    return data


def movement_for(
    player_name: str,
    movements: list[Movement],
    direction: str,
) -> tuple[Movement | None, float]:
    candidates = [item for item in movements if item.direction == direction]
    if not player_name or not candidates:
        return None, 0.0
    match = match_player(player_name, [item.player for item in candidates])
    if match.status != "en_plantilla" or match.confidence < 0.86:
        return None, match.confidence
    normalized = normalize_name(match.candidate)
    movement = next(
        item for item in candidates if normalize_name(item.player) == normalized
    )
    return movement, match.confidence


def departure_status(movement: Movement) -> str:
    kind = normalize_name(movement.movement_type)
    if kind == "fichaje":
        return "VENDIDO"
    if kind == "fichaje gratis":
        return "SALIDA_LIBRE"
    if kind.startswith("cesion"):
        return "CEDIDO"
    if kind == "retirado":
        return "RETIRADO"
    if kind in {"libre", "agente libre"}:
        return "SIN_EQUIPO"
    return "BAJA_CONFIRMADA"


def is_official_player(row: dict[str, str]) -> bool:
    return bool(
        row.get("nombre")
        and row.get("tipo") != "entrenador"
        and row.get("nombre") != "Escudo"
    )


def strategy_rows(
    physical_rows: list[dict[str, str]],
    squads: dict[str, list[SquadPlayer]],
    movements: list[Movement],
    progress: dict[str, dict[str, object]],
    checked_on: date,
    season: int = 2026,
) -> list[dict[str, str]]:
    movements_by_club: dict[str, list[Movement]] = {}
    for movement in movements:
        movements_by_club.setdefault(movement.club, []).append(movement)

    matched_squad: dict[str, set[str]] = {club: set() for club in squads}
    output: list[dict[str, str]] = []
    order = 0
    for source_index, source in enumerate(physical_rows):
        order += 1
        club = source.get("club_objetivo", "")
        squad = squads.get(club, [])
        squad_names = [player.name for player in squad]
        player_match = (
            match_player(source["nombre"], squad_names)
            if is_official_player(source) and squad_names
            else None
        )
        in_squad = bool(player_match and player_match.status == "en_plantilla")
        if in_squad and player_match:
            matched_squad[club].add(normalize_name(player_match.candidate))

        departure, departure_confidence = movement_for(
            source.get("nombre", ""),
            movements_by_club.get(club, []),
            "BAJA",
        )
        if not is_official_player(source):
            market_status = "NO_APLICA" if source.get("nombre") else "PENDIENTE_PUBLICACION"
            action = source.get("accion", "PEGAR")
        elif departure:
            market_status = departure_status(departure)
            action = "PEGAR"
        elif in_squad:
            market_status = "EN_PLANTILLA"
            action = "PEGAR"
        elif player_match and player_match.status in {
            "coincidencia_ambigua",
            "coincidencia_dudosa",
        }:
            market_status = "COINCIDENCIA_DUDOSA"
            action = "PEGAR"
        else:
            market_status = "NO_EN_PLANTILLA"
            action = "PEGAR"

        owned = progress.get(source["id"], {})
        output.append(
            {
                "orden": str(order),
                "id": source["id"],
                "tipo_registro": "CROMO_FISICO",
                "seccion": source["seccion"],
                "numero": source["numero"],
                "hueco_album": source["hueco_album"],
                "variante": source["variante"],
                "nombre": source["nombre"],
                "tipo": source["tipo"],
                "club_album": club,
                "tiene_cromo_fisico": "SI",
                "estado_coleccion": str(owned.get("state", "missing")).upper(),
                "copias": str(owned.get("copies", 0)),
                "estado_mercado": market_status,
                "accion_estrategia": action,
                "club_origen": club if departure else "",
                "club_destino": departure.other_club if departure else "",
                "tipo_movimiento": departure.movement_type if departure else "",
                "importe_movimiento": departure.amount if departure else "",
                "fecha_movimiento": departure.movement_date if departure else "",
                "en_plantilla_transfermarkt": "SI" if in_squad else "NO",
                "coincidencia_transfermarkt": (
                    player_match.candidate if player_match else ""
                ),
                "coincidencia_besoccer": departure.player if departure else "",
                "confianza": (
                    f"{departure_confidence:.4f}"
                    if departure
                    else (f"{player_match.confidence:.4f}" if player_match else "")
                ),
                "fuente_plantilla": (
                    transfermarkt_url(club, season)
                    if club in TRANSFERMARKT_CLUB_IDS
                    else ""
                ),
                "fuente_movimiento": departure.source_url if departure else "",
                "comprobado_en": checked_on.isoformat(),
                "notas": (
                    f"Baja confirmada por BeSoccer: {departure.movement_type}."
                    if departure
                    else (
                        player_match.notes
                        if player_match
                        else source.get("notas", "")
                    )
                ),
            }
        )

        next_row = (
            physical_rows[source_index + 1]
            if source_index + 1 < len(physical_rows)
            else None
        )
        if source["seccion"] not in CLUB_SECTIONS:
            continue
        if next_row and next_row["seccion"] == source["seccion"]:
            continue

        virtual_index = 0
        arrivals = movements_by_club.get(club, [])
        for player in squad:
            if normalize_name(player.name) in matched_squad[club]:
                continue
            virtual_index += 1
            order += 1
            arrival, confidence = movement_for(player.name, arrivals, "ALTA")
            output.append(
                {
                    "orden": str(order),
                    "id": (
                        f"NUEVO-{re.sub(r'[^A-Z0-9]+', '-', source['seccion']).strip('-')}"
                        f"-{virtual_index:02d}"
                    ),
                    "tipo_registro": "PLANTILLA_SIN_CROMO",
                    "seccion": source["seccion"],
                    "numero": f"NUEVO-{virtual_index:02d}",
                    "hueco_album": "",
                    "variante": "",
                    "nombre": player.name,
                    "tipo": player.position,
                    "club_album": club,
                    "tiene_cromo_fisico": "NO",
                    "estado_coleccion": "NO_APLICA",
                    "copias": "0",
                    "estado_mercado": (
                        "FICHAJE_SIN_CROMO" if arrival else "PLANTILLA_SIN_CROMO"
                    ),
                    "accion_estrategia": "ESPERAR_CROMO",
                    "club_origen": arrival.other_club if arrival else "",
                    "club_destino": club if arrival else "",
                    "tipo_movimiento": arrival.movement_type if arrival else "",
                    "importe_movimiento": arrival.amount if arrival else "",
                    "fecha_movimiento": arrival.movement_date if arrival else "",
                    "en_plantilla_transfermarkt": "SI",
                    "coincidencia_transfermarkt": player.name,
                    "coincidencia_besoccer": arrival.player if arrival else "",
                    "confianza": f"{confidence:.4f}" if arrival else "1.0000",
                    "fuente_plantilla": transfermarkt_url(club, season),
                    "fuente_movimiento": arrival.source_url if arrival else "",
                    "comprobado_en": checked_on.isoformat(),
                    "notas": (
                        "Alta de BeSoccer presente en Transfermarkt pero sin cromo físico."
                        if arrival
                        else "Jugador de la plantilla Transfermarkt sin cromo físico."
                    ),
                }
            )
    return output


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera el CSV maestro de estrategia de mercado del álbum."
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=Path("coleccion_panini_revisada.csv"),
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=Path("estrategia_mercado.csv"),
    )
    parser.add_argument("--progreso", type=Path)
    parser.add_argument("--temporada", type=int, default=2026)
    parser.add_argument(
        "--cache-transfermarkt",
        type=Path,
        default=Path(".cache_transfermarkt"),
    )
    parser.add_argument(
        "--cache-besoccer",
        type=Path,
        default=Path(".cache_besoccer/primera.html"),
    )
    parser.add_argument("--refrescar-transfermarkt", action="store_true")
    parser.add_argument("--refrescar-besoccer", action="store_true")
    parser.add_argument("--pausa", type=float, default=1.0)
    parser.add_argument("--fecha", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    physical_rows = load_csv(args.entrada)
    progress = load_progress(args.progreso)
    session = requests.Session()
    session.headers.update(
        {"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"}
    )
    squads: dict[str, list[SquadPlayer]] = {}
    for index, club in enumerate(TRANSFERMARKT_CLUB_IDS):
        html = fetch_squad(
            session,
            club,
            args.temporada,
            args.cache_transfermarkt,
            args.refrescar_transfermarkt,
        )
        squads[club] = parse_squad_details(html)
        print(f"{club}: {len(squads[club])} jugadores")
        if args.refrescar_transfermarkt and index + 1 < len(TRANSFERMARKT_CLUB_IDS):
            time.sleep(args.pausa)

    transfer_html = fetch_besoccer(
        args.cache_besoccer,
        args.refrescar_besoccer,
    )
    movements = parse_besoccer_transfers(transfer_html)
    rows = strategy_rows(
        physical_rows,
        squads,
        movements,
        progress,
        args.fecha,
        args.temporada,
    )
    write_csv(rows, args.salida)
    physical_count = sum(row["tipo_registro"] == "CROMO_FISICO" for row in rows)
    virtual_count = len(rows) - physical_count
    print(
        f"Generado {args.salida}: {physical_count} cromos físicos y "
        f"{virtual_count} jugadores de plantilla sin cromo."
    )


if __name__ == "__main__":
    main()
