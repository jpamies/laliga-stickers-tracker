"""Incorpora al checklist los cromos anunciados en la 3ª edición.

Panini ha publicado el listado de la tercera edición antes de numerarlo del
todo. De los cromos nuevos conocemos tres cosas distintas:

- Los siete huecos de equipo que estaban en blanco ya tienen jugador, y su
  número no cambia porque el hueco ya existía en el álbum.
- Los veinte Últimos Fichajes llegan numerados del UF21 al UF40.
- Los BIS se anuncian sin numeración. Se registran igualmente, porque el cromo
  existe y puede salir en cualquier sobre, pero con el número en blanco hasta
  que Panini lo publique.

Escribe sobre `coleccion_panini.csv`, que es la fuente de la que parten los
demás scripts. Va justo después de `extraer_checklist.py`, que reconstruye ese
fichero desde el PDF de la segunda edición y por tanto no conoce estos cromos;
como el paso es idempotente, se puede repetir tras cada extracción. Cuando
Panini publique el PDF de la tercera edición, este script sobra.
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from pathlib import Path


CSV_FIELDS = (
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
)

EDITION = "3ed"

# Huecos que ya existían en blanco: sólo les faltaba el nombre del jugador.
PENDING_SLOTS = (
    # Los huecos 3 y 4 del Alavés son los dos porteros.
    ("DEPORTIVO ALAVÉS", "4", "Adrián Rodríguez", "portero"),
    # El cromo sólo pone «Rodríguez» y el Alavés tiene tres. El hueco cierra la
    # franja de defensas (5-9), justo antes de los medios, así que es el
    # central Mikel y no el delantero Miguel.
    ("DEPORTIVO ALAVÉS", "10", "Mikel Rodríguez", "defensa"),
    ("DEPORTIVO", "17", "Asp Jensen", "delantero"),
    ("GETAFE CF", "13", "Francho", "medio"),
    ("GETAFE CF", "15", "Mangala", "medio"),
    ("RACING DE SANTANDER", "3", "Agirrezabala", "portero"),
    ("SEVILLA", "4", "Fran González", "portero"),
)

LATEST_SIGNINGS = (
    (21, "Bernardo Silva", "Real Madrid", "medio"),
    (22, "Amatucci", "Deportivo de La Coruña", "medio"),
    (23, "Mojica", "Getafe CF", "defensa"),
    (24, "Gordon", "FC Barcelona", "delantero"),
    (25, "Robbie Ure", "Sevilla FC", "delantero"),
    (26, "Javi Morcillo", "Elche CF", "delantero"),
    (27, "Núñez", "RCD Espanyol", "delantero"),
    (28, "Maffeo", "Valencia CF", "defensa"),
    (29, "Cucurella", "Real Madrid", "defensa"),
    (30, "Valentini", "Deportivo Alavés", "defensa"),
    (31, "Sazonov", "Getafe CF", "defensa"),
    # La lista de Panini lo escribe «Buonanote»; LALIGA lo inscribe como
    # Facundo Buonanotte, con doble te.
    (32, "Buonanotte", "Elche CF", "medio"),
    (33, "Angeliño", "Deportivo de La Coruña", "defensa"),
    (34, "Iván Martín", "Racing de Santander", "medio"),
    (35, "Peio Canales", "Athletic Club", "medio"),
    (36, "Kochorashvili", "Sevilla FC", "medio"),
    (37, "Javi Galán", "RC Celta de Vigo", "defensa"),
    (38, "Parrott", "Real Betis", "delantero"),
    (39, "Diomande", "Real Madrid", "delantero"),
    (40, "Rodri", "FC Barcelona", "medio"),
)

# Los BIS llegan sin número. Se guardan en el orden del anuncio, que es lo
# único estable que tenemos para reconocerlos.
BIS_STICKERS = (
    ("DEPORTIVO ALAVÉS", "Garcés", "defensa"),
    ("DEPORTIVO ALAVÉS", "Mariano Díaz", "delantero"),
    ("ATLÉTICO DE MADRID", "Alejandro Grimaldo", "defensa"),
    ("ATLÉTICO DE MADRID", "Arnau Ortiz", "defensa"),
    ("FC BARCELONA", "Hamza Abdelkarim", "delantero"),
    ("REAL BETIS", "Deossa", "medio"),
    ("RC CELTA DE VIGO", "Hugo González", "portero"),
    ("DEPORTIVO", "Bright Ede", "delantero"),
    ("DEPORTIVO", "Gijselhart", "defensa"),
    ("RCD ESPANYOL", "Drkusic", "defensa"),
    ("RCD ESPANYOL", "Hinojo", "medio"),
    ("RCD ESPANYOL", "Javi Hernández", "defensa"),
    ("GETAFE CF", "Enes Ünal", "delantero"),
    ("LEVANTE UD", "Nacho Pérez", "defensa"),
    ("LEVANTE UD", "Thiago Fernández", "medio"),
    ("REAL MADRID CF", "Konaté", "defensa"),
    ("MALAGA CF", "Ángel Recio", "medio"),
    ("OSASUNA", "Jonathan Dubasin", "delantero"),
    ("RACING DE SANTANDER", "Pedro Felipe", "defensa"),
    ("RACING DE SANTANDER", "Sergio Martínez", "medio"),
    ("RACING DE SANTANDER", "Zabiri", "delantero"),
    ("RAYO VALLECANO", "Vertrouwd", "defensa"),
    ("RAYO VALLECANO", "Pelayo", "defensa"),
    ("SEVILLA", "Julio Díaz", "defensa"),
    ("SEVILLA", "Miguel Sierra", "defensa"),
)

# Hamza es el único BIS cuyo número ha publicado Panini.
BIS_NUMBERS = {("FC BARCELONA", "Hamza Abdelkarim"): "18"}

# Sergio Martínez dejó el Racing por el Real Madrid Castilla y no tiene ficha
# del primer equipo. El cromo se imprimió a tiempo y puede salir en un sobre,
# así que se registra igual; `comprobar_plantillas_laliga.py` verá que ya no
# está inscrito y lo marcará como «no pegar» por su cuenta.
GONE = {
    ("RACING DE SANTANDER", "Sergio Martínez"): (
        "Fichó por el Real Madrid Castilla y no tiene ficha del primer equipo."
    ),
}

SECTION_CLUBS = {
    "DEPORTIVO ALAVÉS": "Deportivo Alavés",
    "ATLÉTICO DE MADRID": "Atlético de Madrid",
    "FC BARCELONA": "FC Barcelona",
    "REAL BETIS": "Real Betis",
    "RC CELTA DE VIGO": "RC Celta de Vigo",
    "DEPORTIVO": "Deportivo de La Coruña",
    "RCD ESPANYOL": "RCD Espanyol",
    "GETAFE CF": "Getafe CF",
    "LEVANTE UD": "Levante UD",
    "REAL MADRID CF": "Real Madrid",
    "MALAGA CF": "Málaga CF",
    "OSASUNA": "CA Osasuna",
    "RACING DE SANTANDER": "Racing de Santander",
    "RAYO VALLECANO": "Rayo Vallecano",
    "SEVILLA": "Sevilla FC",
}


def section_prefix(section: str) -> str:
    plain = unicodedata.normalize("NFKD", section)
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return "".join(c if c.isalnum() else "-" for c in plain.upper()).strip("-")


def bis_id(section: str, position: int) -> str:
    """Identificador estable para un BIS todavía sin numerar.

    El progreso del álbum se guarda por identificador, así que no puede salir
    de un contador sobre las filas existentes: `extraer_checklist.py` rehace el
    fichero desde el PDF y el hueco libre de turno cambiaría de un día para
    otro. Se deriva de la posición dentro del anuncio, que es fija."""
    return f"{section_prefix(section)}-BIS-{position}"


def blank_row() -> dict[str, str]:
    return {field: "" for field in CSV_FIELDS}


def append_to_section(
    rows: list[dict[str, str]], section: str, new_rows: list[dict[str, str]]
) -> None:
    """Coloca los cromos nuevos detrás del último de su sección.

    El fichero va en el orden del álbum, que no es alfabético: los equipos
    primero y luego las secciones temáticas. Reordenarlo entero cambiaría la
    navegación del álbum, así que sólo se inserta donde toca."""
    last = max(
        (index for index, row in enumerate(rows) if row["seccion"] == section),
        default=None,
    )
    if last is None:
        raise SystemExit(f"No existe la sección {section}")
    rows[last + 1 : last + 1] = new_rows


def fill_pending(rows: list[dict[str, str]]) -> int:
    by_slot = {(row["seccion"], row["numero"]): row for row in rows}
    filled = 0
    for section, number, name, kind in PENDING_SLOTS:
        row = by_slot.get((section, number))
        if row is None:
            raise SystemExit(f"No existe el hueco {section} {number}")
        if row["nombre"].strip():
            continue
        row.update(
            nombre=name,
            tipo=kind,
            edicion=EDITION,
            # Vuelve a la cola de comprobación: hasta ahora era un hueco sin
            # jugador al que no había nada que comparar.
            estado_plantilla="sin_comprobar",
            accion="PEGAR",
            notas="Jugador anunciado en la 3ª edición del checklist.",
        )
        filled += 1
    return filled


def add_latest_signings(rows: list[dict[str, str]]) -> int:
    known = {row["id"] for row in rows}
    nuevos = []
    for number, name, club, kind in LATEST_SIGNINGS:
        identifier = f"ULTIMOS-FICHAJES-{number:02d}"
        if identifier in known:
            continue
        row = blank_row()
        row.update(
            id=identifier,
            seccion="ÚLTIMOS FICHAJES",
            numero=f"UF{number}",
            hueco_album=str(number),
            nombre=name,
            tipo=kind,
            club_objetivo=club,
            edicion=EDITION,
            estado_plantilla="sin_comprobar",
            accion="PEGAR",
            notas="Último fichaje anunciado en la 3ª edición del checklist.",
        )
        nuevos.append(row)
    if nuevos:
        append_to_section(rows, "ÚLTIMOS FICHAJES", nuevos)
    return len(nuevos)


def add_bis(rows: list[dict[str, str]]) -> int:
    known = {row["id"] for row in rows}
    seen: dict[str, int] = {}
    por_seccion: dict[str, list[dict[str, str]]] = {}
    for section, name, kind in BIS_STICKERS:
        seen[section] = seen.get(section, 0) + 1
        identifier = bis_id(section, seen[section])
        if identifier in known:
            continue
        number = BIS_NUMBERS.get((section, name), "")
        gone = GONE.get((section, name))
        row = blank_row()
        row.update(
            id=identifier,
            seccion=section,
            # Sin número publicado el cromo se queda con la variante a secas;
            # inventarle un hueco sería peor que dejarlo en blanco, porque el
            # álbum lo colocaría donde no va.
            numero=f"{number}BIS" if number else "BIS",
            hueco_album=number,
            variante="BIS",
            nombre=name,
            tipo=kind,
            club_objetivo=SECTION_CLUBS[section],
            edicion=EDITION,
            estado_plantilla="sin_comprobar",
            accion="PEGAR",
            notas=gone or "Cromo BIS de la 3ª edición, pendiente de numeración.",
        )
        por_seccion.setdefault(section, []).append(row)
    for section, nuevos in por_seccion.items():
        append_to_section(rows, section, nuevos)
    return sum(len(nuevos) for nuevos in por_seccion.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path("coleccion_panini.csv"))
    args = parser.parse_args()

    with args.csv.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))

    before = len(rows)
    filled = fill_pending(rows)
    signings = add_latest_signings(rows)
    bis = add_bis(rows)

    with args.csv.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Huecos rellenados: {filled}")
    print(f"Últimos fichajes añadidos: {signings}")
    print(f"Cromos BIS añadidos: {bis}")
    print(f"Total de cromos: {before} -> {len(rows)}")


if __name__ == "__main__":
    main()
