from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d5639">
  <meta name="description" content="Álbum interactivo Panini LALIGA 2026-27">
  <title>Mi álbum Panini LALIGA 2026-27</title>
  <link rel="stylesheet" href="styles.css?v=25">
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
        <button class="nav-tab" type="button" data-view="friends">Amigos</button>
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
    <section class="progress-overview" aria-label="Progreso de la colección">
      <div class="progress-overview-heading">
        <div>
          <span>Progreso del álbum</span>
          <strong><span id="summary-owned">0</span> de <span id="summary-total">0</span> cromos</strong>
        </div>
        <strong id="progress-text">0%</strong>
      </div>
      <div class="progress-track" aria-hidden="true">
        <div class="progress-bar" id="progress-bar"></div>
      </div>
      <div class="progress-overview-meta">
        <span><strong id="summary-missing">0</strong> pendientes</span>
        <span><strong id="summary-duplicates">0</strong> repetidos</span>
      </div>
    </section>

    <section class="section-menu-panel" aria-labelledby="section-menu-title">
      <div class="section-menu-heading">
        <div>
          <p class="eyebrow">Navegación</p>
          <h2 id="section-menu-title">Secciones del álbum</h2>
        </div>
        <button class="button secondary hidden" id="section-clear" type="button">Borrar selección</button>
      </div>
      <nav class="section-menu" id="section-menu" aria-label="Filtrar por equipo o sección"></nav>
      <div class="section-menu-pager" aria-label="Cambiar de sección">
        <button class="section-page-button" id="section-prev" type="button" aria-label="Sección anterior">←</button>
        <div class="section-page-status" aria-live="polite">
          <strong id="section-current">Todo el álbum</strong>
          <small id="section-position">Vista completa</small>
        </div>
        <button class="section-page-button" id="section-next" type="button" aria-label="Sección siguiente">→</button>
      </div>
    </section>

    <section class="toolbar" aria-label="Buscar y filtrar cromos">
      <div class="toolbar-main">
        <label class="search-wrap">
          <span aria-hidden="true">⌕</span>
          <input class="search" id="search" type="search" placeholder="Buscar cromo…">
        </label>
        <div class="toolbar-actions">
          <select class="section-select" id="section-select" aria-label="Filtrar por sección"></select>
          <button class="button secondary" id="import-progress" type="button">Importar</button>
          <button class="button" id="export-progress" type="button">Exportar progreso</button>
          <button class="button social-button" id="social-open" type="button">Compartir</button>
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
  <dialog class="social-dialog" id="social-dialog">
    <div id="social-content"></div>
  </dialog>
  <dialog class="import-dialog" id="import-dialog">
    <div class="import-header">
      <div>
        <span>Actualizar colección</span>
        <h2>Importar progreso</h2>
      </div>
      <button class="social-close" id="import-close" type="button" aria-label="Cerrar">×</button>
    </div>
    <div class="import-body">
      <section class="import-section">
        <strong>Desde Figuritas App</strong>
        <p>Pega el texto completo de «Compartir lista». Podrás revisarlo antes de aplicarlo.</p>
        <textarea id="figuritas-text" maxlength="100000" placeholder="Figuritas App - Lista&#10;LaLiga 26/27..."></textarea>
        <div class="import-actions">
          <button class="button" id="figuritas-preview" type="button">Revisar importación</button>
        </div>
        <div class="import-preview hidden" id="figuritas-preview-result" aria-live="polite"></div>
      </section>
      <section class="import-section import-json">
        <div>
          <strong>Desde una copia de seguridad</strong>
          <p>Importa un archivo JSON exportado anteriormente desde este álbum.</p>
        </div>
        <button class="button secondary" id="import-json" type="button">Elegir archivo JSON</button>
      </section>
    </div>
  </dialog>
  <script>window.ALBUM_DATA = __ALBUM_DATA__;</script>
  <script>window.ALBUM_PLACEHOLDERS = __ALBUM_PLACEHOLDERS__;</script>
  <script src="cloud-config.js?v=15"></script>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js" crossorigin="anonymous"></script>
  <script src="app.js?v=44"></script>
  <script src="cloud-sync.js?v=15"></script>
  <script src="social.js?v=16"></script>
</body>
</html>
"""

PENDING_UPDATE_SECTIONS = (
    ("ÚLTIMOS FICHAJES", "ULTIMOS-FICHAJES", range(1, 67), "Último fichaje", "UF{number}"),
    ("TOP FICHAJES", "TOP-FICHAJES", range(67, 70), "Top fichaje", "{number}"),
)

PLACEHOLDER_THEMES = {
    "DEPORTIVO ALAVÉS": ("alaves", "ALA", "#0b4da2", "#f4f7fb", "#79b8f3"),
    "ATHLETIC CLUB DE BILBAO": ("athletic", "ATH", "#d71920", "#f7f3eb", "#111111"),
    "ATLÉTICO DE MADRID": ("atletico", "ATM", "#c8102e", "#f5f3ed", "#1b2b5b"),
    "FC BARCELONA": ("barcelona", "BAR", "#004d98", "#a50044", "#edbb00"),
    "REAL BETIS": ("betis", "BET", "#159447", "#f5f7f1", "#0b5f35"),
    "RC CELTA DE VIGO": ("celta", "CEL", "#7cc7e8", "#f5f7f4", "#b21f3d"),
    "DEPORTIVO": ("deportivo", "DEP", "#1d62a7", "#f5f7f4", "#77b5e8"),
    "ELCHE CF": ("elche", "ELC", "#15733c", "#f6f7f2", "#b9d631"),
    "RCD ESPANYOL": ("espanyol", "ESP", "#1474b8", "#f7f5ef", "#202c5f"),
    "GETAFE CF": ("getafe", "GET", "#1459a6", "#f4f6f8", "#e31d2b"),
    "LEVANTE UD": ("levante", "LEV", "#b61f3e", "#174b8f", "#e6b534"),
    "REAL MADRID CF": ("real-madrid", "RMA", "#f4f4ef", "#7851a9", "#d7b64c"),
    "MALAGA CF": ("malaga", "MAL", "#62b5e5", "#f7f5ef", "#193b70"),
    "OSASUNA": ("osasuna", "OSA", "#c8102e", "#172a54", "#d7b640"),
    "RACING DE SANTANDER": ("racing", "RAC", "#168047", "#f5f6ef", "#111111"),
    "RAYO VALLECANO": ("rayo", "RAY", "#f5f4ee", "#d71920", "#1d1d1b"),
    "REAL SOCIEDAD": ("real-sociedad", "RSO", "#1672b8", "#f6f5ef", "#89c8e8"),
    "SEVILLA": ("sevilla", "SEV", "#d71920", "#f7f5ef", "#111111"),
    "VALENCIA": ("valencia", "VAL", "#f28c28", "#1d1d1b", "#f5f3ed"),
    "VILLARREAL": ("villarreal", "VIL", "#f3d332", "#1259a5", "#f7f3d4"),
    "DRAFT 23": ("draft-23", "D23", "#702963", "#f2c14e", "#15172b"),
    "DRAFT 23 KROMIX": ("draft-23-kromix", "KX", "#1f2937", "#d946ef", "#22d3ee"),
    "ÚLTIMOS FICHAJES": ("ultimos-fichajes", "UF", "#006f51", "#e8f4ec", "#c8a64b"),
    "TOP FICHAJES": ("top-fichajes", "TOP", "#191919", "#d7b44a", "#f5efe0"),
}
GENERIC_PLACEHOLDER_THEME = ("general", "LALIGA", "#315b4a", "#edf1eb", "#c8a64b")


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9 ]+", " ", text)
    return " ".join(text.lower().split())


def pending_update_stickers(
    existing_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    existing_ids = existing_ids or set()
    stickers = []
    for section, id_prefix, numbers, sticker_type, number_format in PENDING_UPDATE_SECTIONS:
        for number in numbers:
            identifier = f"{id_prefix}-{number:02d}"
            if identifier in existing_ids:
                continue
            stickers.append(
                {
                    "id": identifier,
                    "seccion": section,
                    "numero": number_format.format(number=number),
                    "hueco_album": "",
                    "variante": "",
                    "nombre": "",
                    "tipo": sticker_type,
                    "club_objetivo": "",
                    "edicion": "",
                    "estado_plantilla": "pendiente_publicacion",
                    "accion": "ESPERAR",
                    "coincidencia_transfermarkt": "",
                    "confianza": "",
                    "comprobado_en": "",
                    "notas": "Pendiente del listado oficial de una actualización de Panini.",
                    "imagen_url": "",
                    "digital_label": "",
                    "digital_group": "",
                    "metodo_coincidencia": "",
                    "estado_laliga": "",
                    "coincidencia_laliga": "",
                    "dorsal_laliga": "",
                    "posicion_laliga": "",
                    "imagen_provisional": "",
                    "foto_url": "",
                    "escudo_url": "",
                    "dorsal": "",
                }
            )
    return stickers


def load_stickers(
    csv_path: Path,
    image_mapping_path: Path | None = None,
    laliga_check_path: Path | None = None,
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

    laliga: dict[str, dict[str, str]] = {}
    if laliga_check_path and laliga_check_path.exists():
        with laliga_check_path.open(encoding="utf-8-sig", newline="") as source:
            laliga = {row["id"]: row for row in csv.DictReader(source)}

    for row in rows:
        image = mapping.get(row["id"], {})
        check = laliga.get(row["id"], {})
        row.setdefault("edicion", "")
        row["imagen_url"] = image.get("imagen_url", "")
        row["digital_label"] = image.get("digital_label", "")
        row["digital_group"] = image.get("digital_group", "")
        row["metodo_coincidencia"] = image.get("metodo_coincidencia", "")
        row["estado_laliga"] = check.get("estado_laliga", "")
        row["coincidencia_laliga"] = check.get("coincidencia_laliga", "")
        row["dorsal_laliga"] = check.get("dorsal_laliga", "")
        row["posicion_laliga"] = check.get("posicion_laliga", "")
        row["imagen_provisional"] = ""
        row["foto_url"] = ""
        row["escudo_url"] = ""
        row["dorsal"] = ""
    rows.extend(pending_update_stickers({row["id"] for row in rows}))
    return rows


def load_player_photos(path: Path | None) -> dict[str, dict[str, str]]:
    if not path or not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        return {
            row["jugador_normalizado"]: row
            for row in csv.DictReader(source)
            if row.get("jugador_normalizado") and row.get("foto_url")
        }


def reliable_match(sticker: dict[str, str], minimum: float = 0.9) -> bool:
    """Sólo aceptamos la foto cuando la coincidencia con Transfermarkt es
    suficientemente fiable; con nombres cortos el emparejamiento parcial
    puede señalar a un jugador distinto."""
    if sticker["estado_plantilla"] != "en_plantilla":
        return False
    try:
        return float(sticker["confianza"]) >= minimum
    except (TypeError, ValueError):
        return False


def generate(
    csv_path: Path,
    output_path: Path,
    image_mapping_path: Path | None = Path("imagenes_panini.csv"),
    photo_mapping_path: Path | None = Path("fotos_transfermarkt.csv"),
    laliga_check_path: Path | None = Path("comprobacion_laliga.csv"),
) -> int:
    stickers = load_stickers(csv_path, image_mapping_path, laliga_check_path)
    photos = load_player_photos(photo_mapping_path)
    crests_by_section = {
        sticker["seccion"]: sticker["imagen_url"]
        for sticker in stickers
        if sticker["digital_group"] == "ESCUDO" and sticker["imagen_url"]
    }
    used_sections: set[str] = set()
    for sticker in stickers:
        if sticker["imagen_url"]:
            continue
        sticker["imagen_provisional"] = "true"
        sticker["escudo_url"] = crests_by_section.get(sticker["seccion"], "")
        player = (
            photos.get(normalize_name(sticker["coincidencia_transfermarkt"]))
            if reliable_match(sticker)
            else None
        )
        if player:
            sticker["foto_url"] = player["foto_url"]
            sticker["dorsal"] = player["dorsal"]
        used_sections.add(sticker["seccion"])
    themes = {
        section: {
            "code": code,
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
        }
        for section, (_, code, primary, secondary, accent) in PLACEHOLDER_THEMES.items()
        if section in used_sections
    }
    _, generic_code, generic_primary, generic_secondary, generic_accent = (
        GENERIC_PLACEHOLDER_THEME
    )
    themes["*"] = {
        "code": generic_code,
        "primary": generic_primary,
        "secondary": generic_secondary,
        "accent": generic_accent,
    }
    serialized = json.dumps(
        stickers,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", r"<\/")
    serialized_themes = json.dumps(
        themes,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", r"<\/")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        HTML_TEMPLATE
        .replace("__ALBUM_DATA__", serialized)
        .replace("__ALBUM_PLACEHOLDERS__", serialized_themes),
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
    parser.add_argument(
        "--fotos",
        type=Path,
        default=Path("fotos_transfermarkt.csv"),
    )
    parser.add_argument(
        "--laliga",
        type=Path,
        default=Path("comprobacion_laliga.csv"),
    )
    args = parser.parse_args()
    total = generate(args.csv, args.salida, args.imagenes, args.fotos, args.laliga)
    print(f"Generado {args.salida} con {total} cromos.")


if __name__ == "__main__":
    main()
