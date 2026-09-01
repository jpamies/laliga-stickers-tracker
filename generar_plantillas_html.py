"""Genera la vista estática de plantillas reales de LALIGA.

Es una página aparte del álbum (`album/plantillas.html`), sin enlace en el
menú: se llega escribiendo la URL. Reutiliza la hoja de estilos del álbum y la
misma plantilla de cromo, pero con los datos y las fotos oficiales de LALIGA.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from generar_album import GENERIC_PLACEHOLDER_THEME, PLACEHOLDER_THEMES


HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d5639">
  <meta name="robots" content="noindex">
  <meta name="description" content="Plantillas oficiales de LALIGA EA SPORTS 2026-27">
  <title>Plantillas reales LALIGA 2026-27</title>
  <link rel="stylesheet" href="styles.css?v=24">
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <span class="brand-mark">L</span>
        <div>
          <strong>Plantillas reales</strong>
          <small>LALIGA EA SPORTS 2026-27</small>
        </div>
      </div>
      <nav class="nav-tabs" aria-label="Vistas">
        <a class="nav-tab" href="index.html">← Volver al álbum</a>
        <button class="nav-tab active" type="button" aria-current="page">Plantillas</button>
      </nav>
      <div class="account-panel">
        <div class="account-copy">
          <strong>Datos oficiales</strong>
          <small id="summary-updated">—</small>
        </div>
      </div>
    </div>
  </header>

  <main class="page">
    <section class="progress-overview" aria-label="Resumen de plantillas">
      <div class="progress-overview-heading">
        <div>
          <span>Fichas publicadas por LALIGA</span>
          <strong><span id="summary-players">0</span> jugadores y técnicos</strong>
        </div>
        <strong><span id="summary-teams">0</span> equipos</strong>
      </div>
      <div class="progress-overview-meta">
        <span>Fuente: <strong>apim.laliga.com</strong></span>
        <span>Vista de sólo lectura, no afecta a tu álbum</span>
      </div>
    </section>

    <section class="section-menu-panel" aria-labelledby="section-menu-title">
      <div class="section-menu-heading">
        <div>
          <p class="eyebrow">Navegación</p>
          <h2 id="section-menu-title">Equipos de Primera División</h2>
        </div>
        <button class="button secondary hidden" id="section-clear" type="button">Borrar selección</button>
      </div>
      <nav class="section-menu" id="section-menu" aria-label="Filtrar por equipo"></nav>
      <div class="section-menu-pager" aria-label="Cambiar de equipo">
        <button class="section-page-button" id="section-prev" type="button" aria-label="Equipo anterior">←</button>
        <div class="section-page-status" aria-live="polite">
          <strong id="section-current">Todas las plantillas</strong>
          <small id="section-position">Vista completa</small>
        </div>
        <button class="section-page-button" id="section-next" type="button" aria-label="Equipo siguiente">→</button>
      </div>
    </section>

    <section class="toolbar" aria-label="Buscar y filtrar jugadores">
      <div class="toolbar-main">
        <label class="search-wrap">
          <span aria-hidden="true">⌕</span>
          <input class="search" id="search" type="search" placeholder="Buscar jugador…">
        </label>
        <div class="toolbar-actions">
          <select class="section-select" id="section-select" aria-label="Filtrar por equipo"></select>
        </div>
      </div>
      <div class="filters" id="filter-chips">
        <button class="filter-chip active" type="button" data-position="all">Todos</button>
        <button class="filter-chip" type="button" data-position="portero">Porteros</button>
        <button class="filter-chip" type="button" data-position="defensa">Defensas</button>
        <button class="filter-chip" type="button" data-position="medio">Centrocampistas</button>
        <button class="filter-chip" type="button" data-position="delantero">Delanteros</button>
        <button class="filter-chip" type="button" data-position="staff">Cuerpo técnico</button>
        <span id="results-label" class="section-count"></span>
      </div>
    </section>

    <div id="collection" aria-live="polite"></div>
  </main>

  <script>window.SQUAD_DATA = __SQUAD_DATA__;</script>
  <script>window.SQUAD_TEAMS = __SQUAD_TEAMS__;</script>
  <script>window.SQUAD_THEMES = __SQUAD_THEMES__;</script>
  <script>window.SQUAD_GENERATED_AT = __SQUAD_GENERATED_AT__;</script>
  <script src="plantillas.js?v=1"></script>
</body>
</html>
"""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def build_themes(sections: set[str]) -> dict[str, dict[str, str]]:
    themes = {
        section: {
            "code": code,
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
        }
        for section, (_, code, primary, secondary, accent) in PLACEHOLDER_THEMES.items()
        if section in sections
    }
    _, code, primary, secondary, accent = GENERIC_PLACEHOLDER_THEME
    themes["*"] = {
        "code": code,
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
    }
    return themes


def dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
        "</", r"<\/"
    )


def generate(
    players_path: Path,
    teams_path: Path,
    output_path: Path,
    generated_at: datetime | None = None,
) -> int:
    players = read_csv(players_path)
    teams = read_csv(teams_path)
    if not players or not teams:
        raise ValueError("Faltan datos: ejecuta antes generar_plantillas_laliga.py.")

    themes = build_themes({player["seccion_album"] for player in players})
    stamp = (generated_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        HTML_TEMPLATE
        .replace("__SQUAD_DATA__", dump(players))
        .replace("__SQUAD_TEAMS__", dump(teams))
        .replace("__SQUAD_THEMES__", dump(themes))
        .replace("__SQUAD_GENERATED_AT__", dump(stamp)),
        encoding="utf-8",
    )
    return len(players)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera album/plantillas.html con las plantillas reales de LALIGA."
    )
    parser.add_argument(
        "--plantillas", type=Path, default=Path("laliga_plantillas.csv")
    )
    parser.add_argument("--equipos", type=Path, default=Path("laliga_equipos.csv"))
    parser.add_argument("--salida", type=Path, default=Path("album/plantillas.html"))
    args = parser.parse_args()

    total = generate(args.plantillas, args.equipos, args.salida)
    print(f"Generado {args.salida} con {total} fichas.")


if __name__ == "__main__":
    main()
