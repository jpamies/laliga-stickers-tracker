from __future__ import annotations

import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from generar_album import STAT_FIELDS, generate, load_stats


class AlbumGenerationTests(unittest.TestCase):
    def test_generates_self_contained_collection_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.html"
            total = generate(Path("coleccion_panini_revisada.csv"), output)
            html = output.read_text(encoding="utf-8")

        match = re.search(
            r"window\.ALBUM_DATA = (.*?);</script>",
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        stickers = json.loads(match.group(1))
        themes_match = re.search(
            r"window\.ALBUM_PLACEHOLDERS = (.*?);</script>",
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(themes_match)
        themes = json.loads(themes_match.group(1))
        self.assertEqual(total, 618)
        self.assertEqual(len(stickers), 618)
        self.assertEqual(len({sticker["id"] for sticker in stickers}), 618)
        self.assertEqual(len({sticker["seccion"] for sticker in stickers}), 29)
        self.assertEqual(
            sum(sticker["imagen_provisional"] != "true" for sticker in stickers),
            424,
        )
        self.assertEqual(
            sum(sticker["imagen_provisional"] == "true" for sticker in stickers),
            194,
        )
        self.assertEqual(
            sum(bool(sticker["foto_url"]) for sticker in stickers),
            137,
        )
        # Los retratos oficiales de LALIGA mandan sobre los de Transfermarkt,
        # que sólo quedan donde LALIGA no ha emparejado al jugador.
        fuentes = Counter(
            sticker["foto_fuente"] for sticker in stickers if sticker["foto_url"]
        )
        self.assertEqual(fuentes, Counter({"laliga": 134, "transfermarkt": 3}))
        self.assertTrue(
            all(
                "/default/" not in sticker["foto_url"]
                and "default-player" not in sticker["foto_url"]
                for sticker in stickers
                if sticker["foto_fuente"] == "laliga"
            ),
            "una silueta genérica de LALIGA no es mejor que el dibujo propio",
        )
        self.assertEqual(
            sum(sticker["accion"] == "NO PEGAR" for sticker in stickers),
            0,
        )
        self.assertEqual({sticker["accion"] for sticker in stickers}, {"PEGAR", "ESPERAR"})
        # La ausencia en la plantilla oficial viaja como dato, nunca como una
        # recomendación pública de no pegar.
        self.assertEqual(
            sum(sticker["estado_laliga"] == "fuera_plantilla" for sticker in stickers),
            64,
        )
        self.assertTrue(
            all(
                sticker["accion"] == "PEGAR"
                for sticker in stickers
                if sticker["estado_laliga"] == "fuera_plantilla"
            )
        )
        self.assertEqual(
            sum(sticker["edicion"] == "2ed" for sticker in stickers),
            44,
        )
        self.assertEqual(
            sum(sticker["edicion"] == "3ed" for sticker in stickers),
            51,
        )
        # Aarón Ochoa sigue en el Málaga pero está lesionado y sin ficha, así
        # que LALIGA no tiene su retrato y se recurre al de Transfermarkt.
        transfermarkt_fallback = next(
            sticker for sticker in stickers if sticker["id"] == "MALAGA-CF-16"
        )
        self.assertIn(
            "img.a.transfermarkt.technology", transfermarkt_fallback["foto_url"]
        )
        self.assertIn("tmssl.akamaized.net", transfermarkt_fallback["escudo_url"])
        weak_match = next(
            sticker for sticker in stickers if sticker["id"] == "DEPORTIVO-ALAVES-08"
        )
        self.assertEqual(weak_match["foto_url"], "")
        self.assertIn("tmssl.akamaized.net", weak_match["escudo_url"])
        self.assertIn("*", themes)
        self.assertIn("DEPORTIVO ALAVÉS", themes)
        self.assertEqual(themes["DEPORTIVO ALAVÉS"]["code"], "ALA")
        updates = [
            sticker
            for sticker in stickers
            if sticker["seccion"] in {"ÚLTIMOS FICHAJES", "TOP FICHAJES"}
        ]
        self.assertEqual(len(updates), 69)
        self.assertEqual(
            [sticker["numero"] for sticker in updates[:2]],
            ["UF1", "UF2"],
        )
        self.assertEqual(
            [sticker["numero"] for sticker in updates[-3:]],
            ["67", "68", "69"],
        )
        published = [sticker for sticker in updates if sticker["nombre"]]
        pending = [sticker for sticker in updates if not sticker["nombre"]]
        self.assertEqual(len(published), 40)
        self.assertEqual(len(pending), 29)
        self.assertTrue(
            all(sticker["edicion"] in {"2ed", "3ed"} for sticker in published)
        )
        self.assertTrue(all(sticker["accion"] == "PEGAR" for sticker in published))
        self.assertTrue(
            all(sticker["estado_plantilla"] == "pendiente_publicacion" for sticker in pending)
        )
        self.assertTrue(all(sticker["accion"] == "ESPERAR" for sticker in pending))
        self.assertTrue(all(not sticker["foto_url"] for sticker in pending))
        self.assertIn("Álbum completo", html)
        self.assertIn("Repetidos", html)
        self.assertNotIn('id="summary-stuck"', html)
        self.assertNotIn('data-filter="stuck"', html)
        self.assertIn('id="auth-button"', html)
        self.assertIn('id="section-menu"', html)
        self.assertIn('id="section-prev"', html)
        self.assertIn('id="section-next"', html)
        self.assertIn('id="section-current"', html)
        self.assertNotIn("Tu colección, bajo control.", html)
        self.assertIn('id="figuritas-text"', html)
        self.assertIn('id="figuritas-preview"', html)
        self.assertIn('id="section-clear"', html)
        self.assertIn('id="import-json"', html)
        self.assertIn('data-filter="second-edition"', html)
        self.assertIn('data-filter="third-edition"', html)
        self.assertIn('id="hide-dont-stick"', html)
        self.assertIn('id="summary-skipped"', html)
        self.assertIn('id="density-switch"', html)
        self.assertIn('data-density="cards"', html)
        self.assertIn('data-density="list"', html)
        self.assertIn('data-density="trade"', html)
        self.assertIn('src="app.js?v=51"', html)
        self.assertIn('href="styles.css?v=33"', html)
        self.assertIn('src="cloud-config.js?v=15"', html)
        self.assertIn('src="cloud-sync.js?v=15"', html)
        self.assertIn('src="social.js?v=16"', html)
        self.assertIn('data-view="friends"', html)


class CompactListViewTests(unittest.TestCase):
    """La vista de lista comprime cada cromo en una fila para preparar
    cambios; se apoya en el álbum ya existente, así que es fácil romperla sin
    enterarse."""

    def app(self) -> str:
        return Path("album/app.js").read_text(encoding="utf-8")

    def styles(self) -> str:
        return Path("album/styles.css").read_text(encoding="utf-8")

    def test_the_row_keeps_the_class_the_click_handler_looks_for(self) -> None:
        # La delegación de clics busca `.sticker-card`; si la fila deja de
        # llevar esa clase, marcarla o sumar copias deja de responder.
        source = self.app()
        self.assertIn('class="sticker-card sticker-row"', source)
        self.assertIn('const card = event.target.closest(".sticker-card");', source)

    def test_the_row_rules_outrank_the_card_rules(self) -> None:
        # `.sticker-card` se declara después en la hoja, así que una regla
        # `.sticker-row` suelta pierde el desempate y la fila hereda los 272px
        # de alto de la ficha.
        loose = re.findall(r"(?<!\.sticker-card)\.sticker-row", self.styles())
        self.assertEqual(loose, [])

    def test_the_row_resets_the_card_layout(self) -> None:
        block = re.search(
            r"\.sticker-card\.sticker-row \{(.*?)\}", self.styles(), flags=re.DOTALL
        )
        self.assertIsNotNone(block, "Falta la regla base de la fila compacta")
        self.assertIn("min-height: 0", block.group(1))
        self.assertIn("flex-direction: row", block.group(1))

    def test_the_density_choice_is_remembered(self) -> None:
        source = self.app()
        self.assertIn("const DENSITY_KEY =", source)
        self.assertIn("localStorage.setItem(DENSITY_KEY", source)

    def test_every_state_colours_the_number(self) -> None:
        styles = self.styles()
        for status in ("missing", "owned", "duplicate", "skipped"):
            self.assertIn(
                f'.sticker-card.sticker-row[data-row-status="{status}"]',
                styles,
                f"La fila no distingue el estado {status}",
            )


class StatsTests(unittest.TestCase):
    """Los minutos deciden qué variante pegar, así que un dato mal cargado
    lleva a pegar el cromo equivocado."""

    def load(self, body: str) -> dict[str, list[int]]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stats.csv"
            header = (
                "cromo_id,minutos,partidos,goles,asistencias,partidos_equipo\n"
            )
            path.write_text(header + body, encoding="utf-8")
            return load_stats(path)

    def test_reads_the_fields_in_the_order_the_album_expects(self) -> None:
        stats = self.load("REAL-BETIS-05B,379,5,1,2,6\n")

        self.assertEqual(stats, {"REAL-BETIS-05B": [379, 5, 1, 2, 6]})
        self.assertEqual(
            STAT_FIELDS,
            ("minutos", "partidos", "goles", "asistencias", "partidos_equipo"),
        )

    def test_keeps_a_player_who_has_not_played(self) -> None:
        # Cero minutos es un hecho comprobado y la señal más útil del álbum:
        # descartarlo por caer en un `if` haría desaparecer justo ese aviso.
        stats = self.load("REAL-BETIS-05A,0,0,0,0,6\n")

        self.assertEqual(stats["REAL-BETIS-05A"], [0, 0, 0, 0, 6])

    def test_skips_rows_without_a_sticker(self) -> None:
        stats = self.load(",450,5,0,0,5\n")

        self.assertEqual(stats, {})

    def test_skips_rows_without_games_to_compare_against(self) -> None:
        # Sin partidos del equipo no se puede calcular el reparto de minutos,
        # y una división por cero pintaría un porcentaje inventado.
        stats = self.load("SEVILLA-07,120,2,0,0,0\n")

        self.assertEqual(stats, {})

    def test_missing_file_is_not_an_error(self) -> None:
        self.assertEqual(load_stats(Path("no-existe.csv")), {})
        self.assertEqual(load_stats(None), {})


class StatsInAlbumTests(unittest.TestCase):
    def album(self) -> tuple[str, list[dict], dict[str, list[int]]]:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.html"
            generate(Path("coleccion_panini_revisada.csv"), output)
            html = output.read_text(encoding="utf-8")
        stickers = json.loads(
            re.search(r"window\.ALBUM_DATA = (\[.*?\]);", html, flags=re.DOTALL).group(1)
        )
        stats = json.loads(
            re.search(r"window\.ALBUM_STATS = (\{.*?\});", html, flags=re.DOTALL).group(1)
        )
        return html, stickers, stats

    def test_the_table_only_holds_stickers_that_exist(self) -> None:
        # Va indexada por cromo, así que una clave suelta sería una ficha que
        # nunca se llega a pintar.
        _, stickers, stats = self.album()
        known = {sticker["id"] for sticker in stickers}

        self.assertTrue(stats, "El álbum salió sin estadísticas")
        self.assertEqual(set(stats) - known, set())

    def test_every_entry_carries_the_five_values(self) -> None:
        _, _, stats = self.album()

        lengths = {len(values) for values in stats.values()}
        self.assertEqual(lengths, {len(STAT_FIELDS)})

    def test_the_table_stays_out_of_the_stickers(self) -> None:
        # Repetir los campos dentro de cada cromo costaba 60 KB de más porque
        # obligaba a escribirlos vacíos en escudos y entrenadores.
        _, stickers, _ = self.album()

        self.assertNotIn("minutos", stickers[0])

    def test_the_album_reads_the_table(self) -> None:
        source = Path("album/app.js").read_text(encoding="utf-8")

        self.assertIn("window.ALBUM_STATS", source)
        self.assertIn("function statsSummary(sticker)", source)


class TradeViewTests(unittest.TestCase):
    """El modo intercambio reduce cada cromo a escudo y número, sin cabeceras
    de sección, para recorrer el álbum entero de un tirón."""

    def app(self) -> str:
        return Path("album/app.js").read_text(encoding="utf-8")

    def stickers(self) -> list[dict]:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.html"
            generate(Path("coleccion_panini_revisada.csv"), output)
            html = output.read_text(encoding="utf-8")
        return json.loads(
            re.search(r"window\.ALBUM_DATA = (\[.*?\]);", html, flags=re.DOTALL).group(1)
        )

    def test_every_sticker_has_something_to_show_on_its_chip(self) -> None:
        # La chapa enseña el número, y cuando no lo hay tira del nombre. Si un
        # cromo se quedara sin los dos saldría una chapa en blanco,
        # imposible de pedir en un cambio.
        blank = [
            sticker["id"]
            for sticker in self.stickers()
            if not re.search(r"\d", sticker["numero"])
            and not sticker["nombre"].strip()
        ]

        self.assertEqual(blank, [])

    def test_the_stickers_without_a_number_are_told_apart_by_name(self) -> None:
        # Los Extra Sticker comparten el texto «Extra Sticker» como número, así
        # que sin el nombre serían quince chapas idénticas. Hay que mirarlos por
        # su sección: los BIS que Panini aún no ha numerado también salen sin
        # número, y son jugadores distintos entre sí.
        extra = [
            sticker
            for sticker in self.stickers()
            if sticker["seccion"].startswith("EXTRA STICKER")
        ]

        self.assertTrue(extra, "Ya no hay Extra Sticker que distinguir")
        self.assertTrue(all(sticker["nombre"].strip() for sticker in extra))
        self.assertEqual(
            len({sticker["nombre"] for sticker in extra}),
            len(extra) // 3,
            "Los Extra Sticker deberían repetir los mismos jugadores en bronce, plata y oro",
        )

    def test_the_bis_stickers_carry_their_slot(self) -> None:
        # Desde la tercera edición Panini numera los BIS, así que cada uno sabe
        # en qué casilla se pega. Sin número el álbum no podría colocarlos.
        bis = [
            sticker
            for sticker in self.stickers()
            if sticker["variante"] == "BIS"
        ]

        self.assertTrue(bis, "Ya no hay cromos BIS")
        for sticker in bis:
            self.assertTrue(sticker["nombre"].strip())
            self.assertTrue(
                sticker["hueco_album"],
                f"{sticker['id']} se quedó sin casilla",
            )
            self.assertTrue(sticker["numero"].endswith("BIS"))

    def test_the_chip_falls_back_to_the_name(self) -> None:
        source = self.app()

        self.assertIn("function chipLabel(sticker)", source)
        self.assertIn("function stickerChip(sticker)", source)

    def test_the_trade_view_drops_the_section_headings(self) -> None:
        source = self.app()

        self.assertIn('state.density === "trade"', source)
        self.assertIn('<div class="sticker-trade">', source)

    def test_removing_a_copy_has_a_single_implementation(self) -> None:
        # El globo y los botones −/+ de las fichas comparten la misma función
        # para que el aviso al borrar la última copia no se quede sólo en un
        # sitio.
        source = self.app()

        self.assertIn("function changeCopies(id, delta)", source)
        self.assertEqual(source.count("removeOwnedSticker(id);"), 2)

    def test_the_chip_only_opens_the_popover(self) -> None:
        # Tocar la chapa no puede cambiar el álbum: es lo único que evita que
        # un clic que se escapa sume una copia sin querer, y en el móvil es
        # además la única forma de leer el nombre.
        source = self.app()

        self.assertIn("state.openChip = state.openChip === chip.dataset.id", source)
        self.assertNotIn("changeCopies(chip.dataset.id", source)

    def test_the_popover_shows_the_name(self) -> None:
        source = self.app()

        self.assertIn("function chipPopover(sticker)", source)
        self.assertIn('class="popover-copy"', source)

    def test_the_popover_closes_from_outside_the_collection(self) -> None:
        # El buscador y la cabecera quedan fuera de #collection, así que el
        # cierre tiene que escuchar en el documento.
        source = self.app()

        self.assertIn(
            'document.addEventListener("click"', source
        )
        self.assertIn('event.target.closest("[data-trade-chip], #chip-popover")', source)

    def test_the_popover_closes_with_escape(self) -> None:
        source = self.app()

        self.assertIn('event.key !== "Escape" || !state.openChip', source)

    def test_an_invisible_sticker_cannot_keep_the_popover_open(self) -> None:
        # Sumar una copia con el filtro «Sin conseguir» saca el cromo de la
        # lista, y el globo no puede quedarse anclado a una chapa que ya no
        # se pinta.
        source = self.app()

        self.assertIn("if (!openSticker) state.openChip = null;", source)

    def test_the_density_switch_offers_the_three_views(self) -> None:
        source = self.app()

        self.assertIn('new Set(["cards", "list", "trade"])', source)


class EditionBadgeTests(unittest.TestCase):
    """Cada edición del checklist se marca en el cromo y se puede filtrar, que
    es como se distingue lo que acaba de salir de lo que ya estaba."""

    def app(self) -> str:
        return Path("album/app.js").read_text(encoding="utf-8")

    def test_every_edition_in_the_data_has_a_label(self) -> None:
        # Un cromo de una edición sin etiqueta saldría indistinguible de los
        # originales, que es justo lo que la etiqueta evita.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.html"
            generate(Path("coleccion_panini_revisada.csv"), output)
            html = output.read_text(encoding="utf-8")
        stickers = json.loads(
            re.search(r"window\.ALBUM_DATA = (\[.*?\]);", html, flags=re.DOTALL).group(1)
        )
        editions = {sticker["edicion"] for sticker in stickers if sticker["edicion"]}
        labels = re.search(
            r"const editionLabels = \{(.*?)\};", self.app(), flags=re.DOTALL
        )
        self.assertIsNotNone(labels, "Falta la tabla de etiquetas de edición")
        labelled = set(re.findall(r'"(\w+)":', labels.group(1)))

        self.assertTrue(editions)
        self.assertEqual(editions - labelled, set())

    def test_each_edition_can_be_filtered(self) -> None:
        source = self.app()

        self.assertIn('state.filter === "second-edition"', source)
        self.assertIn('state.filter === "third-edition"', source)

    def test_each_edition_is_searchable_by_words(self) -> None:
        source = self.app()

        self.assertIn("2a edicion segunda edicion", source)
        self.assertIn("3a edicion tercera edicion", source)


class FiguritasSectionTests(unittest.TestCase):
    """El importador de Figuritas traduce el encabezado de cada línea a una
    sección del álbum; si un nombre no existe, esa línea se descarta en
    silencio y el usuario pierde cromos sin enterarse."""

    def album_sections(self) -> set[str]:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.html"
            generate(Path("coleccion_panini_revisada.csv"), output)
            html = output.read_text(encoding="utf-8")
        match = re.search(r"window\.ALBUM_DATA = (.*?);</script>", html, flags=re.DOTALL)
        return {sticker["seccion"] for sticker in json.loads(match.group(1))}

    def mapped_sections(self) -> dict[str, list[str]]:
        source = Path("album/app.js").read_text(encoding="utf-8")
        mappings = {}
        for name in ("figuritasSections", "figuritasLabels"):
            block = re.search(
                rf"const {name} = \{{(.*?)\n  \}};", source, flags=re.DOTALL
            )
            self.assertIsNotNone(block, f"No se encontró {name} en app.js")
            mappings[name] = re.findall(r':\s*"([^"]+)"', block.group(1))
        return mappings

    def test_every_mapped_section_exists_in_the_album(self) -> None:
        sections = self.album_sections()

        for name, targets in self.mapped_sections().items():
            for target in targets:
                self.assertIn(target, sections, f"{name} apunta a una sección inexistente")

    def test_every_album_section_can_be_imported(self) -> None:
        mapped = set(sum(self.mapped_sections().values(), []))

        self.assertEqual(self.album_sections() - mapped, set())


if __name__ == "__main__":
    unittest.main()