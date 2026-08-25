from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "coleccion_id",
    "coleccion",
    "sticker_id",
    "recurso_global",
    "numero_grupo",
    "nombre",
    "imagen_url",
    "group_id",
    "grupo",
    "slot_id",
    "pagina_id",
    "pagina",
    "fondo_pagina_url",
    "coord_x",
    "coord_y",
    "girado",
]


def markdown_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", r"\|").replace(
        "\n", " "
    )


def resource_number(image_url: str) -> str:
    return image_url.rsplit("/", 1)[-1].split("-", 1)[0]


def load_collection(
    manifest_path: Path,
    collection_id: int,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    collection = next(
        (
            item
            for item in manifest["collections"]
            if int(item["id"]) == collection_id
        ),
        None,
    )
    if collection is None:
        raise ValueError(
            f"No se encontró la colección {collection_id} en {manifest_path}."
        )
    return collection


def build_slot_index(
    collection: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    slots: dict[int, dict[str, Any]] = {}
    for page in collection["pages"]:
        for slot in page["slots"]:
            slot_id = int(slot["id"])
            if slot_id in slots:
                raise ValueError(f"El slot {slot_id} aparece en más de una página.")
            slots[slot_id] = {
                "page": page,
                "slot": slot,
            }
    return slots


def flatten_stickers(collection: dict[str, Any]) -> list[dict[str, str]]:
    groups = {
        int(group["id"]): str(group["label"])
        for group in collection["groups"]
    }
    slot_index = build_slot_index(collection)
    rows: list[dict[str, str]] = []

    for sticker in collection["stickers"]:
        slot_id = int(sticker["slot_id"])
        placement = slot_index.get(slot_id)
        if placement is None:
            raise ValueError(
                f"El cromo {sticker['id']} referencia el slot inexistente {slot_id}."
            )

        page = placement["page"]
        slot = placement["slot"]
        coords = slot.get("coords", {})
        image_url = str(sticker["image_url"])
        rows.append(
            {
                "coleccion_id": str(collection["id"]),
                "coleccion": str(collection["name"]),
                "sticker_id": str(sticker["id"]),
                "recurso_global": resource_number(image_url),
                "numero_grupo": str(sticker["number"]),
                "nombre": str(sticker["label"]),
                "imagen_url": image_url,
                "group_id": str(sticker["group_id"]),
                "grupo": groups[int(sticker["group_id"])],
                "slot_id": str(slot_id),
                "pagina_id": str(page["id"]),
                "pagina": str(page["number"]),
                "fondo_pagina_url": str(page["bg_url"]),
                "coord_x": str(coords.get("x", "")),
                "coord_y": str(coords.get("y", "")),
                "girado": str(
                    bool(sticker.get("rotated") or slot.get("rotated"))
                ).lower(),
            }
        )

    rows.sort(
        key=lambda row: (
            int(row["pagina"]),
            int(row["numero_grupo"]),
            int(row["sticker_id"]),
        )
    )
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def link(label: str, url: str) -> str:
    return f"[{markdown_escape(label)}]({url})" if url else "—"


def scalar_settings(collection: dict[str, Any]) -> list[tuple[str, object]]:
    settings: list[tuple[str, object]] = []
    for section_name in (
        "content",
        "packs",
        "swaps",
        "ecommerce",
        "buy_missing_stickers",
        "rankings",
    ):
        section = collection.get(section_name, {})
        if not isinstance(section, dict):
            settings.append((section_name, section))
            continue
        for key, value in section.items():
            if not isinstance(value, (dict, list)):
                settings.append((f"{section_name}.{key}", value))
    return settings


def write_markdown(
    collection: dict[str, Any],
    rows: list[dict[str, str]],
    output_path: Path,
) -> None:
    group_counts = Counter(row["group_id"] for row in rows)
    group_pages: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        group_pages[row["group_id"]].add(int(row["pagina"]))

    lines = [
        f"# {collection['name']}",
        "",
        collection["description"],
        "",
        "## Resumen",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| ID | {collection['id']} |",
        f"| Estado | {collection['status']} |",
        f"| Categoría | {collection['category']} |",
        f"| Caduca | {collection['expires_at']} |",
        f"| Cromos | {len(rows)} |",
        f"| Grupos | {len(collection['groups'])} |",
        f"| Páginas | {len(collection['pages'])} |",
        "",
        "## Assets de la colección",
        "",
        "| Asset | Valor |",
        "|---|---|",
    ]

    for key, value in collection["assets"].items():
        rendered = (
            link("Abrir", str(value))
            if isinstance(value, str) and value.startswith("http")
            else markdown_escape(value)
        )
        lines.append(f"| {markdown_escape(key)} | {rendered} |")

    lines.extend(
        [
            "",
            "## Configuración",
            "",
            "| Campo | Valor |",
            "|---|---|",
        ]
    )
    for key, value in scalar_settings(collection):
        lines.append(f"| {markdown_escape(key)} | {markdown_escape(value)} |")

    lines.extend(
        [
            "",
            "## Grupos",
            "",
            "| ID | Grupo | Cromos | Páginas |",
            "|---:|---|---:|---|",
        ]
    )
    for group in collection["groups"]:
        group_id = str(group["id"])
        pages = ", ".join(str(page) for page in sorted(group_pages[group_id]))
        lines.append(
            f"| {group_id} | {markdown_escape(group['label'])} | "
            f"{group_counts[group_id]} | {pages or '—'} |"
        )

    lines.extend(
        [
            "",
            "## Páginas",
            "",
            "| Página | ID | Slots | Fondo |",
            "|---:|---:|---:|---|",
        ]
    )
    for page in collection["pages"]:
        lines.append(
            f"| {page['number']} | {page['id']} | {len(page['slots'])} | "
            f"{link('Abrir fondo', str(page['bg_url']))} |"
        )

    lines.extend(
        [
            "",
            "## Cromos",
            "",
            "El **recurso global** es el número que aparece al principio del "
            "archivo PNG. El **número de grupo** es la numeración local dentro "
            "de su sección digital.",
            "",
            "| Recurso | Nº grupo | Nombre | Grupo | Página | Slot | "
            "Coordenadas | Girado | Imagen |",
            "|---:|---:|---|---|---:|---:|---|:---:|---|",
        ]
    )
    for row in rows:
        coords = (
            f"{row['coord_x']}, {row['coord_y']}"
            if row["coord_x"] and row["coord_y"]
            else "—"
        )
        lines.append(
            f"| {row['recurso_global']} | {row['numero_grupo']} | "
            f"{markdown_escape(row['nombre'])} | "
            f"{markdown_escape(row['grupo'])} | {row['pagina']} | "
            f"{row['slot_id']} | {coords} | "
            f"{'Sí' if row['girado'] == 'true' else 'No'} | "
            f"{link('Abrir PNG', row['imagen_url'])} |"
        )

    lines.extend(
        [
            "",
            "## Notas",
            "",
            "- El JSON original es la fuente de verdad.",
            "- Los escudos no aparecen como cromos ni assets independientes.",
            "- Los fondos de página pueden contener escudos y otros elementos "
            "integrados en el diseño.",
            "- La numeración digital no coincide necesariamente con el álbum "
            "físico.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def convert(
    manifest_path: Path,
    csv_path: Path,
    markdown_path: Path,
    collection_id: int = 22,
) -> tuple[int, int, int]:
    collection = load_collection(manifest_path, collection_id)
    rows = flatten_stickers(collection)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(rows, csv_path)
    write_markdown(collection, rows, markdown_path)
    return len(rows), len(collection["groups"]), len(collection["pages"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convierte el manifiesto de Panini a CSV y Markdown."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("panini_digital_collection_22.json"),
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("coleccion_digital_panini.csv"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("coleccion_digital_panini.md"),
    )
    parser.add_argument("--coleccion", type=int, default=22)
    args = parser.parse_args()

    stickers, groups, pages = convert(
        args.manifest,
        args.csv,
        args.markdown,
        args.coleccion,
    )
    print(
        f"Generados {args.csv} y {args.markdown}: "
        f"{stickers} cromos, {groups} grupos y {pages} páginas."
    )


if __name__ == "__main__":
    main()
