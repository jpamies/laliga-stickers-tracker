(() => {
  "use strict";

  const STORAGE_KEY = "panini-laliga-2026-27-progress-v1";
  const data = window.ALBUM_DATA;
  const sections = [...new Set(data.map((sticker) => sticker.seccion))];
  const teamSections = sections.filter((section) => data.some((sticker) => (
    sticker.seccion === section
    && sticker.digital_group === "ESCUDO"
    && sticker.imagen_url
  )));
  const validStates = new Set(["missing", "owned"]);
  const validStickDecisions = new Set(["default", "dont-stick", "stick"]);

  const state = {
    view: "album",
    query: "",
    section: "all",
    filter: "all",
    progress: loadProgress(),
  };

  const elements = {
    collection: document.querySelector("#collection"),
    search: document.querySelector("#search"),
    sectionSelect: document.querySelector("#section-select"),
    sectionMenu: document.querySelector("#section-menu"),
    sectionPrevious: document.querySelector("#section-prev"),
    sectionNext: document.querySelector("#section-next"),
    filterChips: document.querySelector("#filter-chips"),
    navTabs: document.querySelectorAll(".nav-tab"),
    summaryTotal: document.querySelector("#summary-total"),
    summaryMissing: document.querySelector("#summary-missing"),
    summaryOwned: document.querySelector("#summary-owned"),
    summaryDuplicates: document.querySelector("#summary-duplicates"),
    progressText: document.querySelector("#progress-text"),
    progressBar: document.querySelector("#progress-bar"),
    resultsLabel: document.querySelector("#results-label"),
    exportButton: document.querySelector("#export-progress"),
    importButton: document.querySelector("#import-progress"),
    importInput: document.querySelector("#import-file"),
    toast: document.querySelector("#toast"),
  };

  function defaultEntry() {
    return { state: "missing", copies: 0, stickDecision: "default" };
  }

  function cleanProgress(progress) {
    if (!progress || typeof progress !== "object" || Array.isArray(progress)) {
      return {};
    }
    const cleaned = {};
    for (const [id, entry] of Object.entries(progress)) {
      if (!entry || typeof entry !== "object") {
        continue;
      }
      const migratedState = entry.state === "stuck" ? "owned" : entry.state;
      const personalState = validStates.has(migratedState) ? migratedState : "missing";
      const copies = Math.max(0, Math.floor(Number(entry.copies) || 0));
      const stickDecision = validStickDecisions.has(entry.stickDecision)
        ? entry.stickDecision
        : "default";
      const updatedAt = typeof entry.updatedAt === "string"
        && !Number.isNaN(Date.parse(entry.updatedAt))
        ? entry.updatedAt
        : "";
      const normalized = {
        state: copies === 0 ? "missing" : personalState,
        copies,
        stickDecision,
        ...(updatedAt ? { updatedAt } : {}),
      };
      if (
        normalized.state !== "missing"
        || normalized.copies !== 0
        || normalized.stickDecision !== "default"
        || normalized.updatedAt
      ) {
        cleaned[id] = normalized;
      }
    }
    return cleaned;
  }

  function loadProgress() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      return cleanProgress(parsed);
    } catch (error) {
      console.error("No se pudo leer el progreso local.", error);
      return {};
    }
  }

  function saveProgress() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.progress));
  }

  function progressFor(id) {
    return state.progress[id] || defaultEntry();
  }

  function shouldNotStick(sticker, progress = progressFor(sticker.id)) {
    if (progress.stickDecision === "dont-stick") return true;
    if (progress.stickDecision === "stick") return false;
    return sticker.accion === "NO PEGAR";
  }

  function normalize(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function matchesSearch(sticker) {
    if (!state.query) {
      return true;
    }
    const haystack = normalize([
      sticker.numero,
      sticker.nombre,
      sticker.tipo,
      sticker.seccion,
      sticker.club_objetivo,
      sticker.accion,
      sticker.coincidencia_transfermarkt,
      sticker.notas,
    ].join(" "));
    return haystack.includes(normalize(state.query));
  }

  function matchesFilter(sticker) {
    const progress = progressFor(sticker.id);
    if (state.view === "duplicates" && progress.copies < 2) {
      return false;
    }
    if (state.filter === "missing") {
      return progress.state === "missing";
    }
    if (state.filter === "owned") {
      return progress.state === "owned";
    }
    if (state.filter === "duplicates") {
      return progress.copies >= 2;
    }
    if (state.filter === "dont-stick") {
      return shouldNotStick(sticker, progress);
    }
    if (state.filter === "wait") {
      return sticker.accion === "ESPERAR";
    }
    return true;
  }

  function visibleStickers() {
    return data.filter((sticker) => (
      (state.section === "all" || sticker.seccion === state.section)
      && matchesSearch(sticker)
      && matchesFilter(sticker)
    ));
  }

  function strategyClass(action) {
    if (action === "PEGAR") return "strategy-stick";
    if (action === "NO PEGAR") return "strategy-dont";
    if (action === "ESPERAR") return "strategy-wait";
    return "strategy-review";
  }

  function escapeHtml(value) {
    const holder = document.createElement("div");
    holder.textContent = String(value || "");
    return holder.innerHTML;
  }

  function stickerCard(sticker) {
    const progress = progressFor(sticker.id);
    const duplicates = Math.max(0, progress.copies - 1);
    const transfermarkt = sticker.coincidencia_transfermarkt
      ? `<strong>${escapeHtml(sticker.coincidencia_transfermarkt)}</strong>`
      : escapeHtml(sticker.notas || "Sin coincidencia disponible");
    const name = sticker.nombre || "Pendiente de publicación";
    const dontStick = shouldNotStick(sticker, progress);
    const stickDecisionSource = progress.stickDecision === "default"
      ? "Recomendación automática"
      : "Decisión personal";
    const photoAction = progress.state === "missing"
      ? `Marcar ${name} como conseguido`
      : `Quitar ${name} de la colección`;
    const visualClass = sticker.digital_group === "ESCUDO"
      ? "sticker-visual sticker-visual-crest"
      : "sticker-visual";
    const visual = sticker.imagen_url
      ? `
        <button class="${visualClass}" type="button" data-photo-toggle aria-label="${escapeHtml(photoAction)}">
          <img
            class="sticker-image"
            src="${escapeHtml(sticker.imagen_url)}"
            alt="${escapeHtml(name)}"
            loading="lazy"
            referrerpolicy="no-referrer"
          >
        </button>
      `
      : `
        <button class="sticker-visual sticker-visual-empty" type="button" data-photo-toggle aria-label="${escapeHtml(photoAction)}. Imagen no disponible">
          <span>Imagen no disponible</span>
        </button>
      `;

    return `
      <article class="sticker-card" data-id="${escapeHtml(sticker.id)}" data-personal-state="${progress.state}">
        <div class="card-top">
          <span class="sticker-number">${escapeHtml(sticker.numero)}</span>
          <span class="strategy-badge ${strategyClass(sticker.accion)}">${escapeHtml(sticker.accion)}</span>
        </div>
        ${visual}
        <h3 class="sticker-name">${escapeHtml(name)}</h3>
        <p class="sticker-type">${escapeHtml(sticker.tipo || sticker.estado_plantilla.replaceAll("_", " "))}</p>
        <div class="card-meta">
          <span>Transfermarkt:</span>
          <span>${transfermarkt}</span>
        </div>
        <div class="card-spacer"></div>
        <div class="copy-row">
          <span class="copy-label">Copias en total${duplicates ? `<span class="duplicate-pill">+${duplicates} repe</span>` : ""}</span>
          <div class="copy-control">
            <button class="icon-button" type="button" data-copy="-1" aria-label="Quitar una copia">−</button>
            <span class="copy-count">${progress.copies}</span>
            <button class="icon-button" type="button" data-copy="1" aria-label="Añadir una copia">+</button>
          </div>
        </div>
        <div class="state-controls" aria-label="Estado personal">
          <button class="state-button ${progress.state === "missing" ? "active" : ""}" type="button" data-state="missing">No lo tengo</button>
          <button class="state-button ${progress.state === "owned" ? "active" : ""}" type="button" data-state="owned">Lo tengo</button>
        </div>
        <button
          class="stick-toggle ${dontStick ? "active" : ""}"
          type="button"
          data-stick-toggle
          aria-pressed="${dontStick}"
          title="${stickDecisionSource}"
        >
          <span>No pegar</span>
          <small>${stickDecisionSource}</small>
        </button>
      </article>
    `;
  }

  function render() {
    const visible = visibleStickers();
    const grouped = new Map();
    for (const sticker of visible) {
      if (!grouped.has(sticker.seccion)) {
        grouped.set(sticker.seccion, []);
      }
      grouped.get(sticker.seccion).push(sticker);
    }

    elements.collection.innerHTML = [...grouped.entries()].map(([section, stickers]) => `
      <section class="section-block" id="${sectionId(section)}">
        <div class="section-heading">
          <h2>${escapeHtml(section)}</h2>
          <span class="section-count">${stickers.length} ${stickers.length === 1 ? "cromo" : "cromos"}</span>
        </div>
        <div class="sticker-grid">${stickers.map(stickerCard).join("")}</div>
      </section>
    `).join("");

    if (!visible.length) {
      elements.collection.innerHTML = `
        <div class="empty-state">
          <strong>${state.view === "duplicates" ? "Todavía no tienes repetidos" : "No hay resultados"}</strong>
          ${state.view === "duplicates"
            ? "Añade dos o más copias de un cromo para verlo aquí."
            : "Prueba con otra búsqueda, equipo o filtro."}
        </div>
      `;
    }

    elements.resultsLabel.textContent = `${visible.length} de ${data.length} cromos`;
    updateSummary();
  }

  function updateSummary() {
    let missing = 0;
    let owned = 0;
    let duplicates = 0;
    for (const sticker of data) {
      const progress = progressFor(sticker.id);
      if (progress.state === "owned") owned += 1;
      else missing += 1;
      duplicates += Math.max(0, progress.copies - 1);
    }

    const collected = owned;
    const percentage = data.length ? Math.round((collected / data.length) * 100) : 0;
    elements.summaryTotal.textContent = data.length;
    elements.summaryMissing.textContent = missing;
    elements.summaryOwned.textContent = owned;
    elements.summaryDuplicates.textContent = duplicates;
    elements.progressText.textContent = `${percentage}%`;
    elements.progressBar.style.width = `${percentage}%`;
  }

  function sectionId(section) {
    return `section-${normalize(section).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
  }

  function sectionTile(section) {
    const crest = data.find((sticker) => (
      sticker.seccion === section
      && sticker.digital_group === "ESCUDO"
      && sticker.imagen_url
    ));
    const visual = crest
      ? `<img src="${escapeHtml(crest.imagen_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
      : `<span class="section-menu-placeholder" aria-hidden="true">${escapeHtml(section.charAt(0))}</span>`;
    return `
      <button
        class="section-menu-tile"
        type="button"
        data-section-menu="${escapeHtml(section)}"
        aria-pressed="false"
      >
        <span class="section-menu-visual">${visual}</span>
        <span>${escapeHtml(section)}</span>
      </button>
    `;
  }

  function updateSectionMenu() {
    elements.sectionMenu.querySelectorAll("[data-section-menu]").forEach((tile) => {
      const active = tile.dataset.sectionMenu === state.section;
      tile.classList.toggle("active", active);
      tile.setAttribute("aria-pressed", String(active));
    });
  }

  function selectSection(section) {
    state.section = section;
    elements.sectionSelect.value = section;
    updateSectionMenu();
    render();
  }

  function moveBetweenTeams(offset) {
    const currentIndex = teamSections.indexOf(state.section);
    const nextIndex = currentIndex === -1
      ? (offset > 0 ? 0 : teamSections.length - 1)
      : (currentIndex + offset + teamSections.length) % teamSections.length;
    selectSection(teamSections[nextIndex]);
    document.querySelector(".section-menu-panel").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  function updateSticker(id, updater) {
    const current = { ...progressFor(id) };
    const next = { ...updater(current), updatedAt: new Date().toISOString() };
    if (next.state === "missing") {
      next.copies = 0;
    } else if (next.copies === 0) {
      next.copies = 1;
    }
    state.progress[id] = next;
    saveProgress();
    document.dispatchEvent(new CustomEvent("panini:progress-changed", {
      detail: { progress: state.progress },
    }));
    render();
  }

  function removeOwnedSticker(id) {
    const confirmed = window.confirm(
      "¿Seguro que quieres marcar este cromo como «No lo tengo»? Sus copias se pondrán a 0.",
    );
    if (!confirmed) return;
    updateSticker(id, (entry) => ({ ...entry, state: "missing", copies: 0 }));
  }

  function setOwnership(id, nextState) {
    const current = progressFor(id);
    if (nextState === "missing" && current.state === "owned") {
      removeOwnedSticker(id);
      return;
    }
    updateSticker(id, (entry) => ({ ...entry, state: nextState }));
  }

  function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.add("visible");
    window.clearTimeout(showToast.timeout);
    showToast.timeout = window.setTimeout(() => {
      elements.toast.classList.remove("visible");
    }, 2400);
  }

  function initializeSections() {
    elements.sectionSelect.innerHTML = [
      '<option value="all">Todos los equipos y secciones</option>',
      ...sections.map((section) => `<option value="${escapeHtml(section)}">${escapeHtml(section)}</option>`),
    ].join("");
    elements.sectionMenu.innerHTML = `
      <button class="section-menu-tile section-menu-all active" type="button" data-section-menu="all" aria-pressed="true">
        <span class="section-menu-visual section-menu-placeholder" aria-hidden="true">▦</span>
        <span>Todos</span>
      </button>
      ${teamSections.map(sectionTile).join("")}
    `;
  }

  elements.search.addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    render();
  });

  elements.sectionSelect.addEventListener("change", (event) => {
    selectSection(event.target.value);
  });

  elements.sectionMenu.addEventListener("click", (event) => {
    const tile = event.target.closest("[data-section-menu]");
    if (!tile) return;
    selectSection(tile.dataset.sectionMenu);
  });

  elements.sectionPrevious.addEventListener("click", () => moveBetweenTeams(-1));
  elements.sectionNext.addEventListener("click", () => moveBetweenTeams(1));

  elements.filterChips.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-filter]");
    if (!chip) return;
    state.filter = chip.dataset.filter;
    elements.filterChips.querySelectorAll("[data-filter]").forEach((item) => {
      item.classList.toggle("active", item === chip);
    });
    render();
  });

  elements.navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      state.view = tab.dataset.view;
      state.filter = "all";
      elements.navTabs.forEach((item) => item.classList.toggle("active", item === tab));
      elements.filterChips.querySelectorAll("[data-filter]").forEach((item) => {
        item.classList.toggle("active", item.dataset.filter === "all");
      });
      render();
    });
  });

  elements.collection.addEventListener("click", (event) => {
    const card = event.target.closest(".sticker-card");
    if (!card) return;
    const id = card.dataset.id;
    const stateButton = event.target.closest("[data-state]");
    if (stateButton) {
      setOwnership(id, stateButton.dataset.state);
      return;
    }
    const photoToggle = event.target.closest("[data-photo-toggle]");
    if (photoToggle) {
      const nextState = progressFor(id).state === "missing" ? "owned" : "missing";
      setOwnership(id, nextState);
      return;
    }
    const stickToggle = event.target.closest("[data-stick-toggle]");
    if (stickToggle) {
      const sticker = data.find((item) => item.id === id);
      const nextDecision = shouldNotStick(sticker) ? "stick" : "dont-stick";
      updateSticker(id, (entry) => ({ ...entry, stickDecision: nextDecision }));
      return;
    }
    const copyButton = event.target.closest("[data-copy]");
    if (copyButton) {
      const delta = Number(copyButton.dataset.copy);
      const current = progressFor(id);
      if (delta < 0 && current.state === "owned" && current.copies <= 1) {
        removeOwnedSticker(id);
        return;
      }
      updateSticker(id, (entry) => ({
        ...entry,
        copies: Math.max(0, entry.copies + delta),
        state: delta > 0 ? "owned" : entry.state,
      }));
    }
  });

  elements.exportButton.addEventListener("click", () => {
    const payload = {
      album: "Panini LALIGA 2026-27",
      exportedAt: new Date().toISOString(),
      progress: state.progress,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "progreso-panini-2026-27.json";
    link.click();
    URL.revokeObjectURL(link.href);
    showToast("Progreso exportado.");
  });

  elements.importButton.addEventListener("click", () => elements.importInput.click());

  elements.importInput.addEventListener("change", async () => {
    const file = elements.importInput.files[0];
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      const imported = payload.progress || payload;
      if (!imported || typeof imported !== "object" || Array.isArray(imported)) {
        throw new Error("Formato no válido");
      }
      window.PaniniAlbum.replaceProgress(imported, {
        notify: true,
        stampEntries: true,
      });
      showToast("Progreso importado correctamente.");
    } catch {
      showToast("No se pudo importar ese archivo.");
    } finally {
      elements.importInput.value = "";
    }
  });

  window.PaniniAlbum = {
    getProgress: () => structuredClone(state.progress),
    replaceProgress(progress, { notify = false, stampEntries = false } = {}) {
      state.progress = cleanProgress(progress);
      if (stampEntries) {
        const updatedAt = new Date().toISOString();
        for (const entry of Object.values(state.progress)) {
          entry.updatedAt = updatedAt;
        }
      }
      saveProgress();
      render();
      if (notify) {
        document.dispatchEvent(new CustomEvent("panini:progress-changed", {
          detail: { progress: state.progress },
        }));
      }
    },
  };

  initializeSections();
  render();
})();
