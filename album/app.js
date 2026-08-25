(() => {
  "use strict";

  const STORAGE_KEY = "panini-laliga-2026-27-progress-v1";
  const data = window.ALBUM_DATA;
  const sections = [...new Set(data.map((sticker) => sticker.seccion))];
  const validStates = new Set(["missing", "owned", "stuck"]);

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
    filterChips: document.querySelector("#filter-chips"),
    navTabs: document.querySelectorAll(".nav-tab"),
    summaryTotal: document.querySelector("#summary-total"),
    summaryMissing: document.querySelector("#summary-missing"),
    summaryOwned: document.querySelector("#summary-owned"),
    summaryStuck: document.querySelector("#summary-stuck"),
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
    return { state: "missing", copies: 0 };
  }

  function loadProgress() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        return {};
      }
      const cleaned = {};
      for (const [id, entry] of Object.entries(parsed)) {
        if (!entry || typeof entry !== "object") {
          continue;
        }
        const personalState = validStates.has(entry.state) ? entry.state : "missing";
        const copies = Math.max(0, Math.floor(Number(entry.copies) || 0));
        cleaned[id] = {
          state: copies === 0 ? "missing" : personalState,
          copies,
        };
      }
      return cleaned;
    } catch {
      return {};
    }
  }

  function saveProgress() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.progress));
  }

  function progressFor(id) {
    return state.progress[id] || defaultEntry();
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
    if (state.filter === "stuck") {
      return progress.state === "stuck";
    }
    if (state.filter === "duplicates") {
      return progress.copies >= 2;
    }
    if (state.filter === "dont-stick") {
      return sticker.accion === "NO PEGAR";
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
    const visualClass = sticker.digital_group === "ESCUDO"
      ? "sticker-visual sticker-visual-crest"
      : "sticker-visual";
    const visual = sticker.imagen_url
      ? `
        <div class="${visualClass}">
          <img
            class="sticker-image"
            src="${escapeHtml(sticker.imagen_url)}"
            alt="${escapeHtml(name)}"
            loading="lazy"
            referrerpolicy="no-referrer"
          >
        </div>
      `
      : `
        <div class="sticker-visual sticker-visual-empty" aria-label="Imagen no disponible">
          <span>Imagen no disponible</span>
        </div>
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
          <button class="state-button ${progress.state === "stuck" ? "active" : ""}" type="button" data-state="stuck">Pegado</button>
        </div>
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
    let stuck = 0;
    let duplicates = 0;
    for (const sticker of data) {
      const progress = progressFor(sticker.id);
      if (progress.state === "owned") owned += 1;
      else if (progress.state === "stuck") stuck += 1;
      else missing += 1;
      duplicates += Math.max(0, progress.copies - 1);
    }

    const collected = owned + stuck;
    const percentage = data.length ? Math.round((collected / data.length) * 100) : 0;
    elements.summaryTotal.textContent = data.length;
    elements.summaryMissing.textContent = missing;
    elements.summaryOwned.textContent = owned;
    elements.summaryStuck.textContent = stuck;
    elements.summaryDuplicates.textContent = duplicates;
    elements.progressText.textContent = `${percentage}%`;
    elements.progressBar.style.width = `${percentage}%`;
  }

  function sectionId(section) {
    return `section-${normalize(section).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
  }

  function updateSticker(id, updater) {
    const current = { ...progressFor(id) };
    const next = updater(current);
    if (next.state === "missing") {
      next.copies = 0;
    } else if (next.copies === 0) {
      next.copies = 1;
    }
    if (next.state === "missing" && next.copies === 0) {
      delete state.progress[id];
    } else {
      state.progress[id] = next;
    }
    saveProgress();
    render();
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
  }

  elements.search.addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    render();
  });

  elements.sectionSelect.addEventListener("change", (event) => {
    state.section = event.target.value;
    render();
  });

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
      updateSticker(id, (entry) => ({ ...entry, state: stateButton.dataset.state }));
      return;
    }
    const copyButton = event.target.closest("[data-copy]");
    if (copyButton) {
      const delta = Number(copyButton.dataset.copy);
      updateSticker(id, (entry) => ({
        ...entry,
        copies: Math.max(0, entry.copies + delta),
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
      localStorage.setItem(STORAGE_KEY, JSON.stringify(imported));
      state.progress = loadProgress();
      render();
      showToast("Progreso importado correctamente.");
    } catch {
      showToast("No se pudo importar ese archivo.");
    } finally {
      elements.importInput.value = "";
    }
  });

  initializeSections();
  render();
})();
