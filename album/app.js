(() => {
  "use strict";

  const STORAGE_KEY = "panini-laliga-2026-27-progress-v1";
  const data = window.ALBUM_DATA;
  const sections = [...new Set(data.map((sticker) => sticker.seccion))];
  const specialSectionIcons = {
    "ADN / LALIGA PRIME": "ADN",
    "LALIGA FANTASY": "LF",
    "DRAFT 23": "D23",
    "DRAFT 23 KROMIX": "KX",
    "EXTRA STICKER BRONCE": "BR",
    "EXTRA STICKER PLATA": "PL",
    "EXTRA STICKER ORO": "OR",
  };
  const validStates = new Set(["missing", "owned"]);
  const validStickDecisions = new Set(["default", "dont-stick", "stick"]);
  const figuritasSections = {
    ALA: "DEPORTIVO ALAVÉS",
    ATH: "ATHLETIC CLUB DE BILBAO",
    ATM: "ATLÉTICO DE MADRID",
    BAR: "FC BARCELONA",
    BET: "REAL BETIS",
    CEL: "RC CELTA DE VIGO",
    DEP: "DEPORTIVO",
    ELC: "ELCHE CF",
    ESP: "RCD ESPANYOL",
    GET: "GETAFE CF",
    LEV: "LEVANTE UD",
    RMA: "REAL MADRID CF",
    MAL: "MALAGA CF",
    OSA: "OSASUNA",
    RAC: "RACING DE SANTANDER",
    RAY: "RAYO VALLECANO",
    RSO: "REAL SOCIEDAD",
    SEV: "SEVILLA",
    VAL: "VALENCIA",
    VIL: "VILLARREAL",
    ADN: "ADN / LALIGA PRIME",
    FAN: "LALIGA FANTASY",
    DRA: "DRAFT 23",
    K: "DRAFT 23 KROMIX",
    BRO: "EXTRA STICKER BRONCE",
    PLA: "EXTRA STICKER PLATA",
    ORO: "EXTRA STICKER ORO",
  };
  const figuritasUnsupportedSections = new Set(["UF", "TOP"]);

  const state = {
    view: "album",
    query: "",
    section: "all",
    filter: "all",
    progress: loadProgress(),
    readOnly: false,
  };
  let pendingFiguritasImport = null;

  const elements = {
    collection: document.querySelector("#collection"),
    search: document.querySelector("#search"),
    sectionSelect: document.querySelector("#section-select"),
    sectionMenu: document.querySelector("#section-menu"),
    sectionPrevious: document.querySelector("#section-prev"),
    sectionNext: document.querySelector("#section-next"),
    sectionCurrent: document.querySelector("#section-current"),
    sectionPosition: document.querySelector("#section-position"),
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
    importDialog: document.querySelector("#import-dialog"),
    importClose: document.querySelector("#import-close"),
    importJsonButton: document.querySelector("#import-json"),
    figuritasText: document.querySelector("#figuritas-text"),
    figuritasPreviewButton: document.querySelector("#figuritas-preview"),
    figuritasPreview: document.querySelector("#figuritas-preview-result"),
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

  function figuritasNumber(sticker, indexInSection) {
    if (sticker.seccion.startsWith("EXTRA STICKER ")) {
      return String(indexInSection + 1);
    }
    return String(sticker.numero || "").trim().toUpperCase();
  }

  function parseFiguritasToken(value) {
    const clean = value.trim().toUpperCase();
    const match = clean.match(/^([A-Z]?\d+[A-Z]?)(?:\s*\(([X×]\s*)?(\d+)\))?$/);
    if (!match) return { number: clean, copies: 2 };
    const quantity = Number(match[3] || 0);
    return {
      number: match[1],
      copies: quantity > 0 ? quantity + (match[2] ? 1 : 0) : 2,
    };
  }

  function parseFiguritasList(text) {
    if (typeof text !== "string" || text.length > 100000) {
      throw new Error("El texto es demasiado largo.");
    }
    const lines = text.replace(/\r/g, "").split("\n").map((line) => line.trim());
    if (!lines.some((line) => /^Figuritas App\s*-\s*Lista$/i.test(line))) {
      throw new Error("No se reconoce una lista compartida por Figuritas App.");
    }
    if (!lines.some((line) => /^LaLiga\s+26\/27\b/i.test(line))) {
      throw new Error("La lista no corresponde a LaLiga 26/27.");
    }

    const missing = new Map();
    const duplicates = new Map();
    const unsupported = [];
    const unknownCodes = [];
    let mode = "";
    for (const line of lines) {
      if (/^Me faltan$/i.test(line)) {
        mode = "missing";
        continue;
      }
      if (/^Repetidas$/i.test(line)) {
        mode = "duplicates";
        continue;
      }
      if (!mode || !line || /^Descarga la app$/i.test(line) || /^https?:\/\//i.test(line)) {
        continue;
      }
      const match = line.match(/^([A-Z]{1,4})(?:\s+[^:]*)?:\s*(.+)$/i);
      if (!match) continue;
      const code = match[1].toUpperCase();
      const tokens = match[2].split(",")
        .map(parseFiguritasToken)
        .filter((token) => token.number);
      if (figuritasUnsupportedSections.has(code)) {
        unsupported.push(...tokens.map((token) => `${code}:${token.number}`));
        continue;
      }
      const section = figuritasSections[code];
      if (!section) {
        unknownCodes.push(code);
        continue;
      }
      const target = mode === "missing" ? missing : duplicates;
      if (!target.has(section)) target.set(section, mode === "missing" ? new Set() : new Map());
      tokens.forEach((token) => {
        if (mode === "missing") {
          target.get(section).add(token.number);
        } else {
          target.get(section).set(token.number, token.copies);
        }
      });
    }

    const importedSections = new Set([...missing.keys(), ...duplicates.keys()]);
    if (!importedSections.size && !unsupported.length) {
      throw new Error("No se encontraron cromos importables.");
    }
    const imported = {};
    const unmatched = [];
    let missingCount = 0;
    let ownedCount = 0;
    let duplicateCount = 0;
    for (const section of importedSections) {
      const sectionStickers = data.filter((sticker) => sticker.seccion === section);
      const knownNumbers = new Set();
      sectionStickers.forEach((sticker, index) => {
        const number = figuritasNumber(sticker, index);
        knownNumbers.add(number);
        const previous = progressFor(sticker.id);
        let copies = 1;
        if (missing.get(section)?.has(number)) copies = 0;
        const duplicateCopies = duplicates.get(section)?.get(number);
        if (duplicateCopies) copies = Math.max(previous.copies, duplicateCopies);
        if (copies === 0) missingCount += 1;
        else ownedCount += 1;
        if (copies >= 2) duplicateCount += 1;
        imported[sticker.id] = {
          state: copies > 0 ? "owned" : "missing",
          copies,
          stickDecision: previous.stickDecision,
        };
      });
      for (const number of missing.get(section) || []) {
        if (!knownNumbers.has(number)) unmatched.push(`${section}:${number}`);
      }
      for (const number of duplicates.get(section)?.keys() || []) {
        if (!knownNumbers.has(number)) unmatched.push(`${section}:${number}`);
      }
    }
    return {
      progress: imported,
      sectionCount: importedSections.size,
      missingCount,
      ownedCount,
      duplicateCount,
      unsupported,
      unmatched,
      unknownCodes: [...new Set(unknownCodes)],
    };
  }

  function renderFiguritasPreview(result) {
    const warnings = [];
    if (result.unsupported.length) {
      warnings.push(`${result.unsupported.length} referencias UF/TOP ignoradas porque no existen en este álbum.`);
    }
    if (result.unmatched.length) {
      warnings.push(`${result.unmatched.length} números no coinciden con ningún cromo físico.`);
    }
    if (result.unknownCodes.length) {
      warnings.push(`Códigos desconocidos: ${result.unknownCodes.join(", ")}.`);
    }
    elements.figuritasPreview.classList.remove("hidden");
    elements.figuritasPreview.replaceChildren();
    const summary = document.createElement("p");
    summary.textContent = `${result.sectionCount} secciones: ${result.ownedCount} conseguidos, ${result.missingCount} faltantes y ${result.duplicateCount} repetidos.`;
    elements.figuritasPreview.append(summary);
    warnings.forEach((warning) => {
      const item = document.createElement("p");
      item.className = "import-warning";
      item.textContent = warning;
      elements.figuritasPreview.append(item);
    });
    if (!result.sectionCount) return;
    const apply = document.createElement("button");
    apply.className = "button";
    apply.type = "button";
    apply.dataset.applyFiguritas = "";
    apply.textContent = "Aplicar importación";
    elements.figuritasPreview.append(apply);
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
    return holder.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
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
          <span class="copy-label">Copias${duplicates ? `<span class="duplicate-pill">+${duplicates} repe</span>` : ""}</span>
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
    const specialIcon = specialSectionIcons[section];
    const visual = crest
      ? `<img src="${escapeHtml(crest.imagen_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
      : `<span class="section-menu-placeholder" aria-hidden="true">${escapeHtml(specialIcon || section.charAt(0))}</span>`;
    return `
      <button
        class="section-menu-tile ${specialIcon ? "section-menu-tile-special" : ""}"
        type="button"
        data-section-menu="${escapeHtml(section)}"
        aria-label="Mostrar ${escapeHtml(section)}"
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
    const sectionIndex = sections.indexOf(state.section);
    elements.sectionCurrent.textContent = state.section === "all"
      ? "Todo el álbum"
      : state.section;
    elements.sectionPosition.textContent = sectionIndex === -1
      ? "Vista completa"
      : `${sectionIndex + 1} de ${sections.length}`;
  }

  function isMobileLayout() {
    return window.matchMedia("(max-width: 620px)").matches;
  }

  function updateSectionHistory(section) {
    if (!isMobileLayout()) return false;
    const historyState = { ...(window.history.state || {}) };
    if (section === "all" && state.section !== "all" && historyState.paniniSectionView) {
      window.history.back();
      return true;
    }
    const nextHistoryState = {
      ...historyState,
      paniniSectionView: section !== "all",
      paniniSection: section,
    };
    if (section !== "all" && state.section === "all") {
      window.history.pushState(nextHistoryState, "");
    } else {
      window.history.replaceState(nextHistoryState, "");
    }
    return false;
  }

  function selectSection(section, { updateHistory = true } = {}) {
    if (updateHistory && updateSectionHistory(section)) return;
    state.section = section;
    elements.sectionSelect.value = section;
    updateSectionMenu();
    render();
  }

  function returnToSectionMenu() {
    selectSection("all", { updateHistory: false });
    window.requestAnimationFrame(() => {
      document.querySelector(".section-menu-panel").scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  function moveBetweenSections(offset) {
    const currentIndex = sections.indexOf(state.section);
    const nextIndex = currentIndex === -1
      ? (offset > 0 ? 0 : sections.length - 1)
      : (currentIndex + offset + sections.length) % sections.length;
    selectSection(sections[nextIndex]);
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
      <button class="section-menu-tile section-menu-all active" type="button" data-section-menu="all" aria-label="Mostrar todas las secciones" aria-pressed="true">
        <span class="section-menu-visual section-menu-placeholder" aria-hidden="true">▦</span>
        <span>Todos</span>
      </button>
      ${sections.map(sectionTile).join("")}
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

  elements.sectionPrevious.addEventListener("click", () => moveBetweenSections(-1));
  elements.sectionNext.addEventListener("click", () => moveBetweenSections(1));

  window.addEventListener("popstate", (event) => {
    if (!isMobileLayout()) return;
    if (event.state?.paniniSectionView && sections.includes(event.state.paniniSection)) {
      selectSection(event.state.paniniSection, { updateHistory: false });
      return;
    }
    returnToSectionMenu();
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
    if (state.readOnly) return;
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

  elements.importButton.addEventListener("click", () => {
    pendingFiguritasImport = null;
    elements.figuritasText.value = "";
    elements.figuritasPreview.replaceChildren();
    elements.figuritasPreview.classList.add("hidden");
    elements.importDialog.showModal();
  });

  elements.importClose.addEventListener("click", () => elements.importDialog.close());

  elements.importDialog.addEventListener("click", (event) => {
    if (event.target === elements.importDialog) {
      elements.importDialog.close();
    }
  });

  elements.importJsonButton.addEventListener("click", () => elements.importInput.click());

  elements.figuritasPreviewButton.addEventListener("click", () => {
    try {
      pendingFiguritasImport = parseFiguritasList(elements.figuritasText.value);
      renderFiguritasPreview(pendingFiguritasImport);
    } catch (error) {
      pendingFiguritasImport = null;
      elements.figuritasPreview.classList.remove("hidden");
      elements.figuritasPreview.replaceChildren();
      const message = document.createElement("p");
      message.className = "import-warning";
      message.textContent = error instanceof Error ? error.message : "No se pudo leer la lista.";
      elements.figuritasPreview.append(message);
    }
  });

  elements.figuritasText.addEventListener("input", () => {
    pendingFiguritasImport = null;
    elements.figuritasPreview.replaceChildren();
    elements.figuritasPreview.classList.add("hidden");
  });

  elements.figuritasPreview.addEventListener("click", (event) => {
    if (!event.target.closest("[data-apply-figuritas]") || !pendingFiguritasImport) return;
    window.PaniniAlbum.replaceProgress({
      ...state.progress,
      ...pendingFiguritasImport.progress,
    }, {
      notify: true,
      stampEntries: true,
    });
    elements.importDialog.close();
    showToast("Lista de Figuritas App importada.");
  });

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
      elements.importDialog.close();
      showToast("Progreso importado correctamente.");
    } catch {
      showToast("No se pudo importar ese archivo.");
    } finally {
      elements.importInput.value = "";
    }
  });

  window.PaniniAlbum = {
    getProgress: () => structuredClone(state.progress),
    isReadOnly: () => state.readOnly,
    getSocialProgress() {
      const socialProgress = {};
      for (const [id, entry] of Object.entries(state.progress)) {
        if (entry.state === "owned" || entry.copies > 0) {
          socialProgress[id] = {
            state: entry.state,
            copies: entry.copies,
          };
        }
      }
      return socialProgress;
    },
    showReadOnly(progress, ownerName) {
      state.readOnly = true;
      state.progress = cleanProgress(progress);
      document.body.classList.add("read-only");
      document.querySelector(".brand strong").textContent = `Álbum de ${ownerName}`;
      render();
    },
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
    parseFiguritasList,
  };

  initializeSections();
  window.history.replaceState({
    ...(window.history.state || {}),
    paniniSectionView: false,
    paniniSection: "all",
  }, "");
  render();
})();
