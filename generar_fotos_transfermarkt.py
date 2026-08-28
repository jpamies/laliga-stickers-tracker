"""Extrae las fotos de jugador y sus datos básicos desde las plantillas
cacheadas de Transfermarkt para poder ilustrar los cromos que la colección
digital todavía no cubre."""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

FIELDNAMES = ["club", "jugador", "jugador_normalizado", "dorsal", "posicion", "foto_url"]


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9 ]+", " ", text)
    return " ".join(text.lower().split())


def parse_squad_photos(html: str) -> tuple[str, list[dict[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("h1")
    club = heading.get_text(" ", strip=True) if heading else ""
    players: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in soup.select("table.items tbody > tr"):
        cell = row.select_one("td.posrela")
        if not cell:
            continue
        portrait = cell.select_one("img.bilderrahmen-fixed")
        link = cell.select_one('td.hauptlink a[href*="/profil/spieler/"]')
        if not portrait or not link:
            continue
        name = link.get("title") or link.get_text(" ", strip=True)
        key = normalize_name(name)
        if not key or key in seen:
            continue
        photo = portrait.get("data-src") or portrait.get("src") or ""
        if photo.startswith("data:"):
            photo = ""
        photo = photo.split("?")[0]
        if photo.rsplit("/", 1)[-1].startswith("default."):
            photo = ""
        position_cell = cell.select_one("table.inline-table tr:nth-of-type(2) td")
        number_cell = row.select_one("td.zentriert .rn_nummer")
        seen.add(key)
        players.append(
            {
                "club": club,
                "jugador": name,
                "jugador_normalizado": key,
                "dorsal": number_cell.get_text(strip=True) if number_cell else "",
                "posicion": position_cell.get_text(" ", strip=True) if position_cell else "",
                "foto_url": photo,
            }
        )
    return club, players


def collect(cache_directory: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(cache_directory.glob("*.html")):
        club, players = parse_squad_photos(path.read_text(encoding="utf-8"))
        if not players:
            raise ValueError(f"No se encontraron jugadores en {path}.")
        rows.extend(players)
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un CSV con las fotos de jugador de Transfermarkt."
    )
    parser.add_argument("--cache", type=Path, default=Path(".cache_transfermarkt"))
    parser.add_argument("--salida", type=Path, default=Path("fotos_transfermarkt.csv"))
    args = parser.parse_args()
    rows = collect(args.cache)
    write_csv(rows, args.salida)
    clubs = len({row["club"] for row in rows})
    photos = sum(1 for row in rows if row["foto_url"])
    print(f"Generado {args.salida} con {len(rows)} jugadores de {clubs} clubes ({photos} con foto).")


if __name__ == "__main__":
    main()
