from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from comprobar_plantillas import TRANSFERMARKT_CLUB_IDS


CLUB_GROUPS = {
    "deportivo alaves": 662,
    "athletic club": 663,
    "atletico de madrid": 664,
    "fc barcelona": 665,
    "real betis": 666,
    "rc celta de vigo": 667,
    "deportivo de la coruna": 668,
    "elche cf": 669,
    "rcd espanyol": 670,
    "getafe cf": 671,
    "levante ud": 672,
    "real madrid": 673,
    "malaga cf": 674,
    "ca osasuna": 675,
    "racing de santander": 676,
    "rayo vallecano": 677,
    "real sociedad": 678,
    "sevilla fc": 679,
    "valencia cf": 680,
    "villarreal cf": 681,
}

COACHES_GROUP = 682
TEAM_GROUPS = set(CLUB_GROUPS.values())
CANONICAL_GROUPS = TEAM_GROUPS | {COACHES_GROUP}

NAME_ALIASES = {
    "cholo simeone": "diego pablo simeone",
    "fede redondo": "federico redondo",
    "fede valverde": "federico valverde",
    "gonzalo": "gonzalo garcia",
    "isi": "isi palazon",
    "joao cancelo": "cancelo",
    "marcao": "marcao",
    "pepe": "nicolas pepe",
    "sorloth": "alexander sorloth",
    "trent": "trent alexander arnold",
    "valles": "alvaro valles",
    "vinicius": "vinicius junior",
    "williams": "inaki williams",
}

OUTPUT_FIELDS = [
    "id",
    "imagen_url",
    "digital_sticker_id",
    "digital_recurso",
    "digital_label",
    "digital_group",
    "metodo_coincidencia",
    "confianza_imagen",
    "notas_imagen",
]


@dataclass(frozen=True)
class Candidate:
    sticker: dict[str, object]
    normalized_name: str
    group_label: str
    resource_number: str


@dataclass(frozen=True)
class Match:
    candidate: Candidate | None
    method: str
    confidence: float
    notes: str


def normalize(value: str) -> str:
    value = re.sub(r"_(?:[A-Z]+[0-9]*)$", "", value)
    value = value.replace("\ufffd", "")
    value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def resource_number(image_url: str) -> str:
    filename = image_url.rsplit("/", 1)[-1]
    return filename.split("-", 1)[0]


def build_candidates(collection: dict[str, object]) -> list[Candidate]:
    groups = {
        int(group["id"]): str(group["label"])
        for group in collection["groups"]  # type: ignore[index]
    }
    return [
        Candidate(
            sticker=sticker,
            normalized_name=normalize(str(sticker["label"])),
            group_label=groups[int(sticker["group_id"])],
            resource_number=resource_number(str(sticker["image_url"])),
        )
        for sticker in collection["stickers"]  # type: ignore[index]
    ]


def similarity(target: str, candidate: str) -> tuple[float, str]:
    if not target or not candidate:
        return 0.0, "none"
    if target == candidate:
        return 1.0, "exacta"

    target_tokens = set(target.split())
    candidate_tokens = set(candidate.split())
    if target_tokens <= candidate_tokens or candidate_tokens <= target_tokens:
        shortest = min(len(target_tokens), len(candidate_tokens))
        if shortest >= 1 and min(len(target), len(candidate)) >= 4:
            return 0.97, "nombre_parcial"

    ratio = difflib.SequenceMatcher(None, target, candidate).ratio()
    return ratio, "aproximada"


def preferred_pool(
    row: dict[str, str],
    candidates: list[Candidate],
) -> list[Candidate]:
    if row["tipo"] == "entrenador":
        return [
            candidate
            for candidate in candidates
            if int(candidate.sticker["group_id"]) == COACHES_GROUP
        ]

    group_id = CLUB_GROUPS.get(normalize(row["club_objetivo"]))
    if group_id is None:
        return []
    return [
        candidate
        for candidate in candidates
        if int(candidate.sticker["group_id"]) == group_id
    ]


def rank(
    target: str,
    candidates: list[Candidate],
) -> list[tuple[float, str, Candidate]]:
    ranked = [
        (*similarity(target, candidate.normalized_name), candidate)
        for candidate in candidates
    ]
    return sorted(ranked, key=lambda item: item[0], reverse=True)


def choose_match(
    row: dict[str, str],
    candidates: list[Candidate],
) -> Match:
    if not row["nombre"]:
        return Match(None, "sin_imagen", 0.0, "Hueco pendiente de publicación.")

    raw_target = normalize(row["nombre"])
    target = NAME_ALIASES.get(raw_target, raw_target)
    primary = preferred_pool(row, candidates)
    special_candidates = [
        candidate
        for candidate in candidates
        if int(candidate.sticker["group_id"]) not in CANONICAL_GROUPS
    ]

    for pool_name, pool in (
        ("grupo", primary),
        ("catalogo", special_candidates),
    ):
        if not pool:
            continue
        ranked = rank(target, pool)
        best_score, best_method, best = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0

        if best_score == 1.0:
            return Match(
                best,
                f"exacta_{pool_name}",
                best_score,
                "Nombre exacto normalizado.",
            )

        if best_method == "nombre_parcial" and best_score - second_score >= 0.02:
            return Match(
                best,
                f"parcial_{pool_name}",
                best_score,
                "Coincidencia única por nombre parcial.",
            )

        if best_score >= 0.88 and best_score - second_score >= 0.08:
            return Match(
                best,
                f"aproximada_{pool_name}",
                best_score,
                "Coincidencia aproximada de alta confianza.",
            )

    return Match(
        None,
        "sin_coincidencia_segura",
        0.0,
        "No hay una coincidencia suficientemente segura en el catálogo digital.",
    )


def load_collection(manifest_path: Path, collection_id: int) -> dict[str, object]:
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


def generate_mapping(
    checklist_path: Path,
    manifest_path: Path,
    output_path: Path,
    collection_id: int = 22,
) -> Counter[str]:
    with checklist_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))

    collection = load_collection(manifest_path, collection_id)
    candidates = build_candidates(collection)
    mapping_rows: list[dict[str, str]] = []
    methods: Counter[str] = Counter()

    for row in rows:
        if row["nombre"] == "Escudo":
            transfermarkt_club = TRANSFERMARKT_CLUB_IDS.get(row["club_objetivo"])
            if transfermarkt_club is None:
                match = Match(
                    None,
                    "sin_coincidencia_segura",
                    0.0,
                    "No hay identificador de Transfermarkt para este club.",
                )
                crest_url = ""
                crest_id = ""
            else:
                _, club_id = transfermarkt_club
                match = Match(
                    None,
                    "escudo_transfermarkt",
                    1.0,
                    "Escudo oficial del club obtenido desde Transfermarkt.",
                )
                crest_url = (
                    "https://tmssl.akamaized.net/images/wappen/"
                    f"head/{club_id}.png"
                )
                crest_id = str(club_id)
        else:
            match = choose_match(row, candidates)
            crest_url = ""
            crest_id = ""
        candidate = match.candidate
        methods[match.method] += 1
        mapping_rows.append(
            {
                "id": row["id"],
                "imagen_url": (
                    str(candidate.sticker["image_url"])
                    if candidate
                    else crest_url
                ),
                "digital_sticker_id": (
                    str(candidate.sticker["id"])
                    if candidate
                    else crest_id
                ),
                "digital_recurso": candidate.resource_number if candidate else "",
                "digital_label": (
                    str(candidate.sticker["label"])
                    if candidate
                    else row["club_objetivo"] if crest_url else ""
                ),
                "digital_group": (
                    candidate.group_label
                    if candidate
                    else "ESCUDO" if crest_url else ""
                ),
                "metodo_coincidencia": match.method,
                "confianza_imagen": (
                    f"{match.confidence:.4f}"
                    if candidate or crest_url
                    else ""
                ),
                "notas_imagen": match.notes,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(mapping_rows)
    return methods


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Relaciona el checklist físico con imágenes Panini digitales."
    )
    parser.add_argument(
        "--checklist",
        type=Path,
        default=Path("coleccion_panini_revisada.csv"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("panini_digital_collection_22.json"),
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=Path("imagenes_panini.csv"),
    )
    parser.add_argument("--coleccion", type=int, default=22)
    args = parser.parse_args()

    methods = generate_mapping(
        args.checklist,
        args.manifest,
        args.salida,
        args.coleccion,
    )
    matched = sum(
        amount
        for method, amount in methods.items()
        if method not in {"sin_imagen", "sin_coincidencia_segura"}
    )
    print(f"Generado {args.salida}: {matched} cromos con imagen.")
    for method, amount in sorted(methods.items()):
        print(f"- {method}: {amount}")


if __name__ == "__main__":
    main()
