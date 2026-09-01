"""Descarga las plantillas reales de LALIGA EA SPORTS y genera CSV y SQL.

La fuente es la API pública de laliga.com documentada en
`ACTUALIZAR_PLANTILLAS.md`. El SQL se regenera entero en cada ejecución
(borra e inserta dentro de una transacción), así que basta con volver a
lanzarlo cuando Panini o LALIGA actualicen dorsales o fotos.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests


API_ROOT = "https://apim.laliga.com/public-service/api/v1"
SUBSCRIPTION_KEY = "c13c3a8e2f6b46da9c5c425cf61fab3e"
SUBSCRIPTION_SLUG = "laliga-easports-2026"
SEASON_YEAR = 2026
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0 Safari/537.36"
)

# Sección equivalente en el álbum Panini, para poder cruzar ambas vistas.
ALBUM_SECTION_BY_SLUG = {
    "d-alaves": "DEPORTIVO ALAVÉS",
    "athletic-club": "ATHLETIC CLUB DE BILBAO",
    "atletico-de-madrid": "ATLÉTICO DE MADRID",
    "fc-barcelona": "FC BARCELONA",
    "real-betis": "REAL BETIS",
    "rc-celta": "RC CELTA DE VIGO",
    "rc-deportivo": "DEPORTIVO",
    "elche-c-f": "ELCHE CF",
    "rcd-espanyol": "RCD ESPANYOL",
    "getafe-cf": "GETAFE CF",
    "levante-ud": "LEVANTE UD",
    "real-madrid": "REAL MADRID CF",
    "malaga-cf": "MALAGA CF",
    "c-a-osasuna": "OSASUNA",
    "r-racing-club": "RACING DE SANTANDER",
    "rayo-vallecano": "RAYO VALLECANO",
    "real-sociedad": "REAL SOCIEDAD",
    "sevilla-fc": "SEVILLA",
    "valencia-cf": "VALENCIA",
    "villarreal-cf": "VILLARREAL",
}

TEAM_FIELDS = [
    "slug",
    "team_id",
    "nombre",
    "nombre_corto",
    "abreviatura",
    "seccion_album",
    "color",
    "color_secundario",
    "escudo_url",
    "estadio",
    "temporada",
]

PLAYER_FIELDS = [
    "clave",
    "squad_id",
    "team_slug",
    "seccion_album",
    "equipo",
    "dorsal",
    "posicion",
    "posicion_slug",
    "rol",
    "rol_slug",
    "nombre",
    "apodo",
    "nombre_pila",
    "apellidos",
    "fecha_nacimiento",
    "lugar_nacimiento",
    "pais",
    "altura_cm",
    "peso_kg",
    "internacional",
    "activo",
    "cedido",
    "cedido_fuera",
    "foto_url",
    "foto_grande_url",
    "foto_cuadrada_url",
    "person_id",
    "opta_id",
    "temporada",
]

TEAM_TABLE = "public.laliga_equipo"
PLAYER_TABLE = "public.laliga_plantilla"


def api_get(
    session: requests.Session,
    path: str,
    params: dict[str, object],
    cache_path: Path,
    refresh: bool,
) -> dict:
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    query = {**params, "subscription-key": SUBSCRIPTION_KEY, "contentLanguage": "es"}
    response = session.get(f"{API_ROOT}/{path}", params=query, timeout=30)
    if response.status_code == 401:
        raise RuntimeError(
            "LALIGA devolvió 401: la clave pública ha rotado. "
            "Vuelve a leerla desde https://www.laliga.com/es-GB/laliga-easports/clubes"
        )
    response.raise_for_status()
    payload = response.json()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def fetch_teams(
    session: requests.Session, cache_dir: Path, refresh: bool, season: int
) -> list[dict]:
    payload = api_get(
        session,
        "teams",
        {"subscriptionSlug": SUBSCRIPTION_SLUG, "limit": 30},
        cache_dir / f"teams_{season}.json",
        refresh,
    )
    teams = payload.get("teams", [])
    if not teams:
        raise RuntimeError("El endpoint de equipos no devolvió ningún club.")
    return sorted(teams, key=lambda team: ALBUM_ORDER.get(team["slug"], 99))


def fetch_squad(
    session: requests.Session,
    slug: str,
    cache_dir: Path,
    refresh: bool,
    season: int,
) -> list[dict]:
    payload = api_get(
        session,
        f"teams/{slug}/squad-manager",
        {
            "limit": 50,
            "offset": 0,
            "orderField": "id",
            "orderType": "DESC",
            "seasonYear": season,
        },
        cache_dir / f"squad_{season}_{slug}.json",
        refresh,
    )
    squads = payload.get("squads", [])
    if not squads:
        raise RuntimeError(f"La plantilla de {slug} vino vacía.")
    return squads


ALBUM_ORDER = {
    slug: index for index, slug in enumerate(ALBUM_SECTION_BY_SLUG)
}


def image_url(images: dict | None, size: str) -> str:
    if not images:
        return ""
    resizes = images.get("resizes") or {}
    return resizes.get(size) or images.get("url") or ""


def photo_url(photos: dict | None, variant: str, size: str) -> str:
    if not photos:
        return ""
    return (photos.get(variant) or {}).get(size, "")


def text(value: object) -> str:
    """La API deja espacios sobrantes en muchos nombres."""
    return "" if value is None else str(value).strip()


def as_date(value: str | None) -> str:
    if not value:
        return ""
    return str(value)[:10]


def slugify(value: str) -> str:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")


def player_key(member: dict, team: dict) -> str:
    """Identificador estable de la ficha.

    LALIGA todavía no asigna `id` a los fichajes más recientes, así que en ese
    caso lo derivamos del equipo y del nombre para no depender de un valor nulo.
    """
    slug = text(team.get("slug"))
    squad_id = member.get("id")
    if squad_id:
        return f"{slug}-{squad_id}"
    person = member.get("person") or {}
    name = text(person.get("name")) or text(person.get("nickname"))
    return f"{slug}-s-{slugify(name)}"


def team_row(team: dict, season: int) -> dict[str, str]:
    venue = team.get("venue") or {}
    return {
        "slug": text(team.get("slug")),
        "team_id": team.get("id", ""),
        "nombre": text(team.get("name")),
        "nombre_corto": text(team.get("nickname")) or text(team.get("boundname")),
        "abreviatura": text(team.get("shortname")),
        "seccion_album": ALBUM_SECTION_BY_SLUG.get(text(team.get("slug")), ""),
        "color": text(team.get("color")),
        "color_secundario": text(team.get("color_secondary")),
        "escudo_url": image_url(team.get("shield"), "medium"),
        "estadio": text(venue.get("name")),
        "temporada": season,
    }


def player_row(member: dict, team: dict, season: int) -> dict[str, str]:
    person = member.get("person") or {}
    position = member.get("position") or {}
    role = member.get("role") or {}
    photos = member.get("photos") or {}
    slug = text(team.get("slug"))
    return {
        "clave": player_key(member, team),
        "squad_id": member.get("id") or "",
        "team_slug": slug,
        "seccion_album": ALBUM_SECTION_BY_SLUG.get(slug, ""),
        "equipo": text(team.get("nickname")) or text(team.get("name")),
        "dorsal": member.get("shirt_number") or "",
        "posicion": text(position.get("name")),
        "posicion_slug": text(position.get("slug")),
        "rol": text(role.get("name")),
        "rol_slug": text(role.get("slug")),
        "nombre": text(person.get("name")),
        "apodo": text(person.get("nickname")),
        "nombre_pila": text(person.get("firstname")),
        "apellidos": text(person.get("lastname")),
        "fecha_nacimiento": as_date(person.get("date_of_birth")),
        "lugar_nacimiento": text(person.get("place_of_birth")),
        "pais": text((person.get("country") or {}).get("id")),
        "altura_cm": person.get("height") or "",
        "peso_kg": person.get("weight") or "",
        "internacional": "true" if person.get("international") else "false",
        "activo": "true" if member.get("current") else "false",
        "cedido": "true" if member.get("loan") else "false",
        "cedido_fuera": "true" if member.get("loan_to") else "false",
        "foto_url": photo_url(photos, "001", "512x556"),
        "foto_grande_url": photo_url(photos, "001", "1024x1113"),
        "foto_cuadrada_url": photo_url(photos, "002", "512x512"),
        "person_id": person.get("id") or "",
        "opta_id": text(member.get("opta_id")),
        "temporada": season,
    }


def collect(
    session: requests.Session,
    cache_dir: Path,
    refresh: bool,
    season: int,
    delay: float,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    teams: list[dict[str, str]] = []
    players: list[dict[str, str]] = []
    for index, team in enumerate(fetch_teams(session, cache_dir, refresh, season)):
        slug = team["slug"]
        if slug not in ALBUM_SECTION_BY_SLUG:
            continue
        if index and refresh:
            time.sleep(delay)
        squad = fetch_squad(session, slug, cache_dir, refresh, season)
        teams.append(team_row(team, season))
        rows = [player_row(member, team, season) for member in squad]
        rows.sort(
            key=lambda row: (
                POSITION_ORDER.get(row["posicion_slug"], 9),
                int(row["dorsal"]) if str(row["dorsal"]).isdigit() else 999,
                row["nombre"],
            )
        )
        players.extend(rows)
        print(f"{team_row(team, season)['nombre_corto']}: {len(rows)} fichas")

    missing = set(ALBUM_SECTION_BY_SLUG) - {team["slug"] for team in teams}
    if missing:
        raise RuntimeError(f"Faltan plantillas de: {sorted(missing)}")
    keys = [row["clave"] for row in players]
    if len(keys) != len(set(keys)):
        duplicated = sorted({key for key in keys if keys.count(key) > 1})
        raise RuntimeError(f"Claves de ficha repetidas: {duplicated}")
    return teams, players


POSITION_ORDER = {
    "entrenador": 0,
    "portero": 1,
    "defensa": 2,
    "centrocampista": 3,
    "medio": 3,
    "delantero": 4,
}


def write_csv(rows: list[dict[str, str]], fields: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sql_literal(value: object, column: str) -> str:
    text = "" if value is None else str(value)
    if text == "":
        return "null"
    if column in NUMERIC_COLUMNS:
        return text if text.lstrip("-").isdigit() else "null"
    if column in BOOLEAN_COLUMNS:
        return "true" if text == "true" else "false"
    return "'" + text.replace("'", "''") + "'"


NUMERIC_COLUMNS = {
    "team_id",
    "squad_id",
    "person_id",
    "dorsal",
    "altura_cm",
    "peso_kg",
    "temporada",
}
BOOLEAN_COLUMNS = {"internacional", "activo", "cedido", "cedido_fuera"}


def insert_statements(
    rows: list[dict[str, str]], fields: list[str], table: str, chunk: int = 50
) -> list[str]:
    statements: list[str] = []
    columns = ", ".join(fields)
    for start in range(0, len(rows), chunk):
        block = rows[start : start + chunk]
        values = ",\n  ".join(
            "(" + ", ".join(sql_literal(row[field], field) for field in fields) + ")"
            for row in block
        )
        statements.append(f"insert into {table} ({columns}) values\n  {values};")
    return statements


def write_sql(
    teams: list[dict[str, str]],
    players: list[dict[str, str]],
    path: Path,
    generated_at: datetime,
) -> None:
    lines = [
        "-- Plantillas reales de LALIGA EA SPORTS.",
        "-- Generado por generar_plantillas_laliga.py, no editar a mano.",
        f"-- Actualizado: {generated_at.isoformat(timespec='seconds')}",
        f"-- Equipos: {len(teams)} | Fichas: {len(players)}",
        "",
        "begin;",
        "",
        f"delete from {PLAYER_TABLE};",
        f"delete from {TEAM_TABLE};",
        "",
    ]
    lines.extend(insert_statements(teams, TEAM_FIELDS, TEAM_TABLE))
    lines.append("")
    lines.extend(insert_statements(players, PLAYER_FIELDS, PLAYER_TABLE))
    lines.extend(["", "commit;", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga las plantillas oficiales de LALIGA y genera CSV y SQL."
    )
    parser.add_argument(
        "--equipos-csv", type=Path, default=Path("laliga_equipos.csv")
    )
    parser.add_argument(
        "--plantillas-csv", type=Path, default=Path("laliga_plantillas.csv")
    )
    parser.add_argument(
        "--sql", type=Path, default=Path("supabase/laliga_plantillas.sql")
    )
    parser.add_argument("--cache", type=Path, default=Path(".cache_laliga"))
    parser.add_argument("--temporada", type=int, default=SEASON_YEAR)
    parser.add_argument("--espera", type=float, default=1.0)
    parser.add_argument(
        "--refrescar",
        action="store_true",
        help="Ignora la caché y vuelve a pedir los datos a la API.",
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    teams, players = collect(
        session, args.cache, args.refrescar, args.temporada, args.espera
    )

    write_csv(teams, TEAM_FIELDS, args.equipos_csv)
    write_csv(players, PLAYER_FIELDS, args.plantillas_csv)
    write_sql(teams, players, args.sql, datetime.now(timezone.utc))
    print(
        f"Generados {args.equipos_csv}, {args.plantillas_csv} y {args.sql}: "
        f"{len(teams)} equipos y {len(players)} fichas."
    )


if __name__ == "__main__":
    main()
