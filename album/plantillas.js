(() => {
  "use strict";

  const data = Array.isArray(window.SQUAD_DATA) ? window.SQUAD_DATA : [];
  const teams = Array.isArray(window.SQUAD_TEAMS) ? window.SQUAD_TEAMS : [];
  const themes = window.SQUAD_THEMES || {};
  const generatedAt = window.SQUAD_GENERATED_AT || "";

  const teamBySection = new Map(teams.map((team) => [team.seccion_album, team]));
  const sections = teams.map((team) => team.seccion_album);

  const state = {
    query: "",
    section: "all",
    position: "all",
  };

  const elements = {
    collection: document.querySelector("#collection"),
    search: document.querySelector("#search"),
    sectionMenu: document.querySelector("#section-menu"),
    sectionSelect: document.querySelector("#section-select"),
    sectionClear: document.querySelector("#section-clear"),
    sectionCurrent: document.querySelector("#section-current"),
    sectionPosition: document.querySelector("#section-position"),
    sectionPrev: document.querySelector("#section-prev"),
    sectionNext: document.querySelector("#section-next"),
    filterChips: document.querySelector("#filter-chips"),
    resultsLabel: document.querySelector("#results-label"),
    summaryPlayers: document.querySelector("#summary-players"),
    summaryTeams: document.querySelector("#summary-teams"),
    summaryUpdated: document.querySelector("#summary-updated"),
  };

  function normalize(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function escapeHtml(value) {
    const holder = document.createElement("div");
    holder.textContent = String(value === 0 ? "0" : value || "");
    return holder.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function theme(section) {
    return themes[section] || themes["*"] || {
      code: "LALIGA",
      primary: "#315b4a",
      secondary: "#edf1eb",
      accent: "#c8a64b",
    };
  }

  function positionCode(player) {
    const slug = normalize(player.posicion_slug);
    if (slug.startsWith("portero")) return "POR";
    if (slug.startsWith("defensa")) return "DEF";
    if (slug.startsWith("centrocampista") || slug.startsWith("medio")) return "MED";
    if (slug.startsWith("delantero")) return "DEL";
    if (slug.includes("entrenador")) return "ENT";
    return (player.posicion || "").toUpperCase().slice(0, 3) || "—";
  }

  function positionGroup(player) {
    const slug = normalize(player.posicion_slug);
    if (slug.startsWith("portero")) return "portero";
    if (slug.startsWith("defensa")) return "defensa";
    if (slug.startsWith("centrocampista") || slug.startsWith("medio")) return "medio";
    if (slug.startsWith("delantero")) return "delantero";
    return "staff";
  }

  function age(birthDate) {
    if (!birthDate) return "";
    const born = new Date(`${birthDate}T00:00:00Z`);
    if (Number.isNaN(born.getTime())) return "";
    const now = new Date();
    let years = now.getUTCFullYear() - born.getUTCFullYear();
    const monthDelta = now.getUTCMonth() - born.getUTCMonth();
    if (monthDelta < 0 || (monthDelta === 0 && now.getUTCDate() < born.getUTCDate())) {
      years -= 1;
    }
    return years > 0 && years < 120 ? String(years) : "";
  }

  function formatDate(value) {
    if (!value) return "";
    const parsed = new Date(`${value}T00:00:00Z`);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  }

  function stickerSvg(player) {
    const palette = theme(player.seccion_album);
    const id = normalize(player.squad_id).replace(/[^a-z0-9]+/g, "-");
    const team = teamBySection.get(player.seccion_album);
    const label = (player.apodo || player.nombre || "").toUpperCase();
    const labelSize = label.length > 15 ? 13 : label.length > 11 ? 15 : 18;
    const role = positionCode(player);
    const photo = player.foto_url
      ? `<image href="${escapeHtml(player.foto_url)}" x="52" y="66" width="172" height="204" clip-path="url(#photo-${id})" preserveAspectRatio="xMidYMax meet"/>`
      : `<text x="138" y="180" text-anchor="middle" fill="${palette.primary}" font-family="Trebuchet MS, Arial, sans-serif" font-size="44" font-weight="900" opacity=".35">?</text>`;
    const crest = team && team.escudo_url
      ? `<image href="${escapeHtml(team.escudo_url)}" x="8" y="7" width="56" height="56" preserveAspectRatio="xMidYMid meet"/>`
      : `<text x="36" y="44" text-anchor="middle" fill="#ffffff" font-family="Trebuchet MS, Arial, sans-serif" font-size="20" font-weight="900">${escapeHtml(palette.code)}</text>`;

    return `
      <svg viewBox="0 0 232 308" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ficha de ${escapeHtml(player.nombre)}">
        <defs>
          <linearGradient id="swoosh-${id}" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="${palette.primary}"/>
            <stop offset="1" stop-color="${palette.accent}"/>
          </linearGradient>
          <pattern id="weave-${id}" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="9" stroke="${palette.primary}" stroke-width="2.5" opacity=".07"/>
          </pattern>
          <clipPath id="photo-${id}">
            <rect x="52" y="66" width="172" height="204" rx="10"/>
          </clipPath>
        </defs>
        <rect width="232" height="308" fill="#f6f5f1"/>
        <rect width="232" height="308" fill="url(#weave-${id})"/>
        <rect x="10" y="4" width="34" height="264" fill="#ffffff" opacity=".9"/>
        <rect x="46" y="4" width="2.5" height="264" fill="${palette.primary}" opacity=".55"/>
        ${photo}
        <path d="M4 4h118Q42 46 4 116Z" fill="url(#swoosh-${id})"/>
        <path d="M4 122Q44 52 124 6l8 0Q50 56 4 128Z" fill="#ffffff" opacity=".75"/>
        <path d="M0 268h232v40H0z" fill="#f6f5f1"/>
        <text transform="translate(35 262) rotate(-90)" fill="#14171a" font-family="Trebuchet MS, Arial, sans-serif" font-size="${labelSize}" font-weight="900" letter-spacing="1">${escapeHtml(label)}</text>
        <g transform="translate(4 272)">
          <rect width="45" height="24" rx="2" fill="${palette.primary}"/>
          <text x="22.5" y="17" text-anchor="middle" fill="#ffffff" font-family="Trebuchet MS, Arial, sans-serif" font-size="13" font-weight="900">${escapeHtml(role)}</text>
        </g>
        <text x="218" y="288" text-anchor="end" fill="${palette.primary}" font-family="Trebuchet MS, Arial, sans-serif" font-size="21" font-weight="900">${escapeHtml(player.dorsal || "—")}</text>
        ${crest}
        <rect x="2" y="2" width="228" height="304" rx="5" fill="none" stroke="${palette.primary}" stroke-width="4"/>
      </svg>
    `;
  }

  function playerCard(player) {
    const years = age(player.fecha_nacimiento);
    const facts = [
      ["Posición", player.posicion],
      ["Dorsal", player.dorsal || "sin asignar"],
      ["Edad", years ? `${years} años` : ""],
      ["Nacimiento", [formatDate(player.fecha_nacimiento), player.lugar_nacimiento].filter(Boolean).join(" · ")],
      ["País", player.pais],
      ["Altura", player.altura_cm ? `${player.altura_cm} cm` : ""],
      ["Peso", player.peso_kg ? `${player.peso_kg} kg` : ""],
    ].filter(([, value]) => value);

    const tags = [
      player.cedido === "true" ? '<span class="squad-tag squad-tag-loan">Cedido</span>' : "",
      player.cedido_fuera === "true" ? '<span class="squad-tag squad-tag-loan">Cedido fuera</span>' : "",
      player.internacional === "true" ? '<span class="squad-tag">Internacional</span>' : "",
      player.activo === "true" ? "" : '<span class="squad-tag squad-tag-off">Ficha inactiva</span>',
    ].filter(Boolean).join("");

    return `
      <article class="sticker-card squad-card" data-id="${escapeHtml(player.squad_id)}">
        <div class="card-top">
          <span class="sticker-number">${escapeHtml(player.dorsal || "—")}</span>
          <span class="strategy-badge strategy-${positionGroup(player)}">${escapeHtml(player.posicion)}</span>
        </div>
        <span class="sticker-visual squad-visual">
          <span class="sticker-image placeholder-inline" role="img" aria-label="${escapeHtml(player.nombre)}">${stickerSvg(player)}</span>
        </span>
        <h3 class="sticker-name">${escapeHtml(player.apodo || player.nombre)}</h3>
        <p class="sticker-type">${escapeHtml(player.nombre)}</p>
        ${tags ? `<div class="squad-tags">${tags}</div>` : ""}
        <dl class="squad-facts">
          ${facts.map(([term, value]) => `
            <div>
              <dt>${escapeHtml(term)}</dt>
              <dd>${escapeHtml(value)}</dd>
            </div>
          `).join("")}
        </dl>
      </article>
    `;
  }

  function matchesSearch(player) {
    if (!state.query) return true;
    const haystack = normalize([
      player.nombre,
      player.apodo,
      player.nombre_pila,
      player.apellidos,
      player.dorsal,
      player.posicion,
      player.equipo,
      player.seccion_album,
      player.pais,
      player.lugar_nacimiento,
    ].join(" "));
    return haystack.includes(normalize(state.query));
  }

  function matchesPosition(player) {
    if (state.position === "all") return true;
    return positionGroup(player) === state.position;
  }

  function visiblePlayers() {
    return data.filter((player) => (
      (state.section === "all" || player.seccion_album === state.section)
      && matchesSearch(player)
      && matchesPosition(player)
    ));
  }

  function sectionId(section) {
    return `section-${normalize(section).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
  }

  function render() {
    const visible = visiblePlayers();
    const grouped = new Map();
    for (const player of visible) {
      if (!grouped.has(player.seccion_album)) {
        grouped.set(player.seccion_album, []);
      }
      grouped.get(player.seccion_album).push(player);
    }

    elements.collection.innerHTML = visible.length
      ? [...grouped.entries()].map(([section, players]) => {
        const team = teamBySection.get(section) || {};
        return `
          <section class="section-block" id="${sectionId(section)}">
            <div class="section-heading">
              <h2>${escapeHtml(team.nombre_corto || section)}</h2>
              <div class="section-totals" aria-label="Resumen de la plantilla">
                <span class="section-count">${players.length} fichas</span>
                ${team.estadio ? `<span class="section-count">${escapeHtml(team.estadio)}</span>` : ""}
              </div>
            </div>
            <div class="sticker-grid">${players.map(playerCard).join("")}</div>
          </section>
        `;
      }).join("")
      : `
        <div class="empty-state">
          <strong>No hay resultados</strong>
          Prueba con otra búsqueda, equipo o demarcación.
        </div>
      `;

    elements.resultsLabel.textContent = `${visible.length} de ${data.length} fichas`;
    updateSectionMenu();
  }

  function sectionTile(section) {
    const team = teamBySection.get(section) || {};
    const visual = team.escudo_url
      ? `<img src="${escapeHtml(team.escudo_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
      : `<span class="section-menu-placeholder" aria-hidden="true">${escapeHtml(team.abreviatura || section.charAt(0))}</span>`;
    return `
      <button
        class="section-menu-tile"
        type="button"
        data-section-menu="${escapeHtml(section)}"
        aria-label="Mostrar ${escapeHtml(section)}"
        aria-pressed="false"
      >
        <span class="section-menu-visual">${visual}</span>
        <span>${escapeHtml(team.nombre_corto || section)}</span>
      </button>
    `;
  }

  function updateSectionMenu() {
    elements.sectionMenu.querySelectorAll("[data-section-menu]").forEach((tile) => {
      const active = tile.dataset.sectionMenu === state.section;
      tile.classList.toggle("active", active);
      tile.setAttribute("aria-pressed", String(active));
    });
    elements.sectionClear.classList.toggle("hidden", state.section === "all");
    const index = sections.indexOf(state.section);
    const team = teamBySection.get(state.section);
    elements.sectionCurrent.textContent = state.section === "all"
      ? "Todas las plantillas"
      : (team ? team.nombre_corto : state.section);
    elements.sectionPosition.textContent = state.section === "all"
      ? "Vista completa"
      : `${index + 1} de ${sections.length}`;
    elements.sectionSelect.value = state.section;
  }

  function selectSection(section) {
    state.section = section;
    render();
    if (section !== "all") {
      const target = document.querySelector(`#${CSS.escape(sectionId(section))}`);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function stepSection(offset) {
    const current = sections.indexOf(state.section);
    if (current === -1) {
      selectSection(sections[offset > 0 ? 0 : sections.length - 1]);
      return;
    }
    selectSection(sections[(current + offset + sections.length) % sections.length]);
  }

  function bind() {
    elements.search.addEventListener("input", (event) => {
      state.query = event.target.value.trim();
      render();
    });

    elements.sectionMenu.innerHTML = sections.map(sectionTile).join("");
    elements.sectionMenu.addEventListener("click", (event) => {
      const tile = event.target.closest("[data-section-menu]");
      if (!tile) return;
      const section = tile.dataset.sectionMenu;
      selectSection(state.section === section ? "all" : section);
    });

    elements.sectionSelect.innerHTML = [
      '<option value="all">Todas las plantillas</option>',
      ...sections.map((section) => {
        const team = teamBySection.get(section) || {};
        return `<option value="${escapeHtml(section)}">${escapeHtml(team.nombre_corto || section)}</option>`;
      }),
    ].join("");
    elements.sectionSelect.addEventListener("change", (event) => {
      selectSection(event.target.value);
    });

    elements.sectionClear.addEventListener("click", () => selectSection("all"));
    elements.sectionPrev.addEventListener("click", () => stepSection(-1));
    elements.sectionNext.addEventListener("click", () => stepSection(1));

    elements.filterChips.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-position]");
      if (!chip) return;
      state.position = chip.dataset.position;
      elements.filterChips.querySelectorAll("[data-position]").forEach((item) => {
        item.classList.toggle("active", item === chip);
      });
      render();
    });
  }

  elements.summaryPlayers.textContent = data.length;
  elements.summaryTeams.textContent = teams.length;
  elements.summaryUpdated.textContent = generatedAt
    ? formatDate(generatedAt.slice(0, 10))
    : "—";
  bind();
  render();
})();
