from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d5639">
  <meta name="description" content="Álbum interactivo Panini LALIGA 2026-27">
  <title>Mi álbum Panini LALIGA 2026-27</title>
  <link rel="stylesheet" href="styles.css?v=5">
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <span class="brand-mark">P</span>
        <div>
          <strong>Mi álbum Panini</strong>
          <small>LALIGA 2026-27</small>
        </div>
      </div>
      <nav class="nav-tabs" aria-label="Vistas del álbum">
        <button class="nav-tab active" type="button" data-view="album">Álbum completo</button>
        <button class="nav-tab" type="button" data-view="duplicates">Repetidos</button>
      </nav>
      <div class="account-panel">
        <img class="account-avatar hidden" id="account-avatar" alt="">
        <div class="account-copy">
          <strong id="account-name">Modo local</strong>
          <small id="sync-status">Guardado en este dispositivo</small>
        </div>
        <button class="button account-button" id="auth-button" type="button">Iniciar sesión</button>
      </div>
    </div>
  </header>

  <main class="page">
    <section class="hero">
      <div>
        <p class="eyebrow">Colección 2026-27</p>
        <h1>Tu colección, bajo control.</h1>
        <p class="hero-copy">
          Consulta todos los equipos y secciones, sigue la recomendación de plantilla
          y guarda qué cromos tienes, cuáles no quieres pegar y cuántas copias repetidas conservas.
        </p>
      </div>
      <div class="hero-progress">
        <div class="hero-progress-row">
          <span>Colección conseguida</span>
          <strong id="progress-text">0%</strong>
        </div>
        <div class="progress-track" aria-hidden="true">
          <div class="progress-bar" id="progress-bar"></div>
        </div>
      </div>
    </section>

    <section class="summary-grid" aria-label="Resumen de la colección">
      <div class="summary-card"><span>Total</span><strong id="summary-total">0</strong></div>
      <div class="summary-card"><span>Sin conseguir</span><strong id="summary-missing">0</strong></div>
      <div class="summary-card"><span>Los tengo</span><strong id="summary-owned">0</strong></div>
      <div class="summary-card"><span>Copias repetidas</span><strong id="summary-duplicates">0</strong></div>
    </section>

    <section class="toolbar" aria-label="Buscar y filtrar cromos">
      <div class="toolbar-main">
        <label class="search-wrap">
          <span aria-hidden="true">⌕</span>
          <input class="search" id="search" type="search" placeholder="Buscar jugador, equipo, número o posición…">
        </label>
        <div class="toolbar-actions">
          <select class="section-select" id="section-select" aria-label="Filtrar por sección"></select>
          <button class="button secondary" id="import-progress" type="button">Importar</button>
          <button class="button" id="export-progress" type="button">Exportar progreso</button>
          <input class="hidden" id="import-file" type="file" accept="application/json,.json">
        </div>
      </div>
      <div class="filters" id="filter-chips">
        <button class="filter-chip active" type="button" data-filter="all">Todos</button>
        <button class="filter-chip" type="button" data-filter="missing">Sin conseguir</button>
        <button class="filter-chip" type="button" data-filter="owned">Los tengo</button>
        <button class="filter-chip" type="button" data-filter="duplicates">Con repetidos</button>
        <button class="filter-chip" type="button" data-filter="dont-stick">No pegar</button>
        <button class="filter-chip" type="button" data-filter="wait">Esperar</button>
        <span id="results-label" class="section-count"></span>
      </div>
    </section>

    <div id="collection" aria-live="polite"></div>
  </main>

  <div class="toast" id="toast" role="status"></div>
  <script>window.ALBUM_DATA = __ALBUM_DATA__;</script>
  <script src="cloud-config.js?v=5"></script>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js" crossorigin="anonymous"></script>
  <script src="app.js?v=5"></script>
  <script src="cloud-sync.js?v=5"></script>
</body>
</html>
"""


def load_stickers(
    csv_path: Path,
    image_mapping_path: Path | None = None,
) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    required_fields = {
        "id",
        "seccion",
        "numero",
        "nombre",
        "tipo",
        "club_objetivo",
        "estado_plantilla",
        "accion",
        "coincidencia_transfermarkt",
        "notas",
    }
    missing = required_fields - set(rows[0] if rows else ())
    if missing:
        raise ValueError(f"Faltan columnas en {csv_path}: {sorted(missing)}")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("El CSV contiene identificadores de cromo duplicados.")

    mapping: dict[str, dict[str, str]] = {}
    if image_mapping_path and image_mapping_path.exists():
        with image_mapping_path.open(encoding="utf-8-sig", newline="") as source:
            image_rows = list(csv.DictReader(source))
        mapping = {row["id"]: row for row in image_rows}

    for row in rows:
        image = mapping.get(row["id"], {})
        row["imagen_url"] = image.get("imagen_url", "")
        row["digital_label"] = image.get("digital_label", "")
        row["digital_group"] = image.get("digital_group", "")
        row["metodo_coincidencia"] = image.get("metodo_coincidencia", "")
    return rows


def generate(
    csv_path: Path,
    output_path: Path,
    image_mapping_path: Path | None = Path("imagenes_panini.csv"),
) -> int:
    stickers = load_stickers(csv_path, image_mapping_path)
    serialized = json.dumps(
        stickers,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", r"<\/")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        HTML_TEMPLATE.replace("__ALBUM_DATA__", serialized),
        encoding="utf-8",
    )
    return len(stickers)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un álbum HTML estático desde el CSV revisado."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("coleccion_panini_revisada.csv"),
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=Path("album/index.html"),
    )
    parser.add_argument(
        "--imagenes",
        type=Path,
        default=Path("imagenes_panini.csv"),
    )
    args = parser.parse_args()
    total = generate(args.csv, args.salida, args.imagenes)
    print(f"Generado {args.salida} con {total} cromos.")


if __name__ == "__main__":
    main()
