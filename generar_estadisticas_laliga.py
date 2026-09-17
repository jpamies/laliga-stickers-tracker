"""Descarga las estadísticas de juego de cada jugador de LALIGA.

Sirven para decidir qué cromo pegar cuando un hueco admite dos variantes: entre
un jugador que no ha disputado un minuto y otro que es titular, el segundo
envejece mejor en el álbum. También revelan qué futbolistas se han ganado un
cromo que Panini todavía no ha impreso.

LALIGA no ofrece un endpoint con todas las estadísticas de golpe, así que hay
que pedirlas jugador a jugador. Las respuestas se cachean.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from generar_plantillas_laliga import API_ROOT, SUBSCRIPTION_KEY, USER_AGENT


SUBSCRIPTION_SLUG = "laliga-easports-2026"

# De las más de noventa métricas que publica LALIGA nos quedamos con las que
# describen cuánto juega alguien; el resto es detalle de rendimiento.
TRACKED_STATS = {
    "time_played": "minutos",
    "appearances": "partidos",
    "starts": "titularidades",
    "substitute_off": "sustituido",
    "goals": "goles",
    "goal_assists": "asistencias",
    "yellow_cards": "amarillas",
    "red_cards": "rojas",
    "team_games_played": "partidos_equipo",
}

CSV_FIELDS = [
    "clave",
    "slug",
    "seccion_album",
    "equipo",
    "nombre",
    "apodo",
    "dorsal",
    "posicion",
    "minutos",
    "partidos",
    "titularidades",
    "sustituido",
    "goles",
    "asistencias",
    "amarillas",
    "rojas",
    "partidos_equipo",
    "minutos_por_partido_equipo",
    "cromo_id",
    "cromos",
    "consultado_en",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def fetch_team_games(
    session: requests.Session,
    slug: str,
    cache_dir: Path,
    refresh: bool,
) -> int:
    """Partidos que lleva disputados el equipo.

    Es el denominador para saber si alguien juega mucho o poco, y hace falta
    aparte porque a los jugadores sin un solo minuto LALIGA no les devuelve
    ninguna estadística, ni siquiera la de su equipo."""
    cache_path = cache_dir / f"teamstats_{slug}.json"
    if cache_path.exists() and not refresh:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        response = session.get(
            f"{API_ROOT}/teams/{slug}/stats",
            params={
                "subscriptionSlug": SUBSCRIPTION_SLUG,
                "contentLanguage": "es",
                "subscription-key": SUBSCRIPTION_KEY,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    bloque = (payload or {}).get("team_stats") or {}
    for item in bloque.get("stats") or []:
        if item.get("name") == "games_played":
            return as_number(item.get("stat"))
    return 0


def fetch_stats(
    session: requests.Session,
    slug: str,
    cache_dir: Path,
    refresh: bool,
) -> dict[str, float] | None:
    """Estadísticas acumuladas del jugador en la competición.

    Devuelve un diccionario vacío cuando el jugador existe pero no ha jugado
    (LALIGA responde `{}`), y `None` cuando el slug no existe (responde 404).
    Confundir ambos casos sería dar por seguro que alguien no juega cuando en
    realidad no se le ha encontrado."""
    cache_path = cache_dir / f"stats_{slug}.json"
    if cache_path.exists() and not refresh:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        response = session.get(
            f"{API_ROOT}/players/{slug}/stats",
            params={
                "subscriptionSlug": SUBSCRIPTION_SLUG,
                "contentLanguage": "es",
                "subscription-key": SUBSCRIPTION_KEY,
            },
            timeout=30,
        )
        if response.status_code == 404:
            payload = {"no_encontrado": True}
        else:
            response.raise_for_status()
            payload = response.json()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    if isinstance(payload, dict) and payload.get("no_encontrado"):
        return None
    bloque = payload.get("player_stats") if isinstance(payload, dict) else None
    if not isinstance(bloque, dict):
        return {}
    return {
        TRACKED_STATS[item["name"]]: item.get("stat")
        for item in bloque.get("stats") or []
        if item.get("name") in TRACKED_STATS
    }


def as_number(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def player_row(
    member: dict[str, str],
    stats: dict[str, float] | None,
    team_games: int,
    checked_on: str,
) -> dict[str, str]:
    encontrado = stats is not None
    stats = stats or {}
    # Cuando un jugador no ha disputado ni un minuto, LALIGA no devuelve nada,
    # ni siquiera los partidos de su equipo; los tomamos de las estadísticas
    # del club para poder comparar a todos con el mismo rasero.
    partidos_equipo = as_number(stats.get("partidos_equipo")) or team_games
    minutos = as_number(stats.get("minutos"))
    row = {
        "clave": member["clave"],
        "slug": member["slug"],
        "seccion_album": member["seccion_album"],
        "equipo": member["equipo"],
        "nombre": member["nombre"],
        "apodo": member["apodo"],
        "dorsal": member["dorsal"],
        "posicion": member["posicion"],
        "cromo_id": member.get("cromo_id", ""),
        "cromos": member.get("cromos", ""),
        "consultado_en": checked_on,
        "partidos_equipo": partidos_equipo if encontrado else "",
        "minutos_por_partido_equipo": (
            f"{minutos / partidos_equipo:.1f}"
            if encontrado and partidos_equipo
            else ""
        ),
    }
    for columna in TRACKED_STATS.values():
        if columna == "partidos_equipo":
            continue
        row[columna] = as_number(stats.get(columna)) if encontrado else ""
    return row


def generate(
    squads_path: Path,
    output_path: Path,
    cache_dir: Path,
    refresh: bool = False,
    delay: float = 0.2,
) -> dict[str, int]:
    squads = [
        row
        for row in read_csv(squads_path)
        if row.get("rol_slug") == "jugador" and row.get("slug")
    ]
    if not squads:
        raise ValueError(
            f"{squads_path} no tiene jugadores con slug; "
            "ejecuta antes generar_plantillas_laliga.py."
        )

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    checked_on = datetime.now(timezone.utc).date().isoformat()

    team_games = {
        slug: fetch_team_games(session, slug, cache_dir, refresh)
        for slug in sorted({row["team_slug"] for row in squads})
    }

    rows: list[dict[str, str]] = []
    desconocidos = 0
    for index, member in enumerate(squads):
        if index and refresh:
            time.sleep(delay)
        stats = fetch_stats(session, member["slug"], cache_dir, refresh)
        if stats is None:
            desconocidos += 1
        rows.append(
            player_row(
                member, stats, team_games.get(member["team_slug"], 0), checked_on
            )
        )

    rows.sort(
        key=lambda row: (row["seccion_album"], -as_number(row["minutos"]), row["nombre"])
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    jugados = [row for row in rows if as_number(row["minutos"]) > 0]
    return {
        "jugadores": len(rows),
        "con_minutos": len(jugados),
        "sin_minutos": len(rows) - len(jugados) - desconocidos,
        "sin_datos": desconocidos,
        "sin_cromo_con_minutos": sum(1 for row in jugados if not row["cromo_id"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga las estadísticas de juego de cada jugador de LALIGA."
    )
    parser.add_argument(
        "--plantillas", type=Path, default=Path("laliga_plantillas.csv")
    )
    parser.add_argument(
        "--salida", type=Path, default=Path("laliga_estadisticas.csv")
    )
    parser.add_argument("--cache", type=Path, default=Path(".cache_laliga"))
    parser.add_argument("--espera", type=float, default=0.2)
    parser.add_argument(
        "--refrescar",
        action="store_true",
        help="Ignora la caché y vuelve a pedir las estadísticas.",
    )
    args = parser.parse_args()

    counts = generate(
        args.plantillas, args.salida, args.cache, args.refrescar, args.espera
    )
    print(f"Generado {args.salida}:")
    for clave, total in counts.items():
        print(f"- {clave}: {total}")


if __name__ == "__main__":
    main()
