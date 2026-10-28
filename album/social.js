(() => {
  "use strict";

  const album = window.PaniniAlbum;
  const stickers = new Map(window.ALBUM_DATA.map((sticker) => [sticker.id, sticker]));
  const dialog = document.querySelector("#social-dialog");
  const content = document.querySelector("#social-content");
  const openButton = document.querySelector("#social-open");
  const params = new URLSearchParams(window.location.search);
  const shareId = params.get("share");
  const friendToken = params.get("friend");
  let client = null;
  let user = null;
  let profile = null;
  let friends = [];
  let activeTab = "share";
  let comparisonFriendId = null;
  let poolSelection = new Set();
  let poolPlan = null;
  let poolJob = null;
  let poolViewVersion = 0;
  let shareListKind = "missing";
  let shareViewVersion = 0;

  function escapeHtml(value) {
    const holder = document.createElement("div");
    holder.textContent = String(value || "");
    return holder.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function baseUrl() {
    return `${window.location.origin}${window.location.pathname}`;
  }

  function stickerName(id) {
    const sticker = stickers.get(id);
    if (!sticker) return id;
    return `${sticker.seccion} · ${sticker.numero} · ${sticker.nombre || "Pendiente"}`;
  }

  function formatDate(value) {
    return new Intl.DateTimeFormat("es", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(value));
  }

  async function shareUrl(url, title) {
    if (navigator.share) {
      await navigator.share({ title, url });
      return;
    }
    await navigator.clipboard.writeText(url);
    showNotice("Enlace copiado.");
  }

  function showNotice(message, isError = false) {
    const notice = content.querySelector("#social-notice");
    if (!notice) return;
    notice.textContent = message;
    notice.classList.toggle("error", isError);
    notice.classList.add("visible");
  }

  function requireUser() {
    if (user) return true;
    window.PaniniCloud?.signIn();
    return false;
  }

  function modalShell(body) {
    return `
      <div class="social-header">
        <div>
          <span>Tu colección</span>
          <h2>Compartir e intercambiar</h2>
        </div>
        <button class="social-close" type="button" data-social-close aria-label="Cerrar">×</button>
      </div>
      <div class="social-tabs" role="tablist">
        <button class="${activeTab === "share" ? "active" : ""}" type="button" data-social-tab="share">Compartir</button>
        <button class="${activeTab === "friends" ? "active" : ""}" type="button" data-social-tab="friends">Amigos</button>
        <button class="${activeTab === "trades" ? "active" : ""}" type="button" data-social-tab="trades">Propuestas</button>
        <button class="${activeTab === "pool" ? "active" : ""}" type="button" data-social-tab="pool">Grupal</button>
      </div>
      <div class="social-notice" id="social-notice" role="status"></div>
      <div class="social-body">${body}</div>
    `;
  }

  function collectionListText(kind) {
    if (!["missing", "duplicates", "both"].includes(kind)) {
      throw new Error("Elige faltantes, repetidos o ambas listas.");
    }
    if (!user || album.isAuthRequired() || album.isReadOnly()) {
      throw new Error("Inicia sesión en tu álbum para compartir tus listas.");
    }
    const mine = album.getSocialProgress();
    const unwanted = album.getUnwantedStickerIds();
    const numberCounts = new Map();
    for (const sticker of stickers.values()) {
      const key = JSON.stringify([sticker.seccion, sticker.numero]);
      numberCounts.set(key, (numberCounts.get(key) || 0) + 1);
    }
    const missing = new Map();
    const duplicates = new Map();
    let missingCount = 0;
    let duplicateCount = 0;
    let extraCopies = 0;
    for (const sticker of stickers.values()) {
      if (!sticker.nombre || sticker.accion === "ESPERAR") continue;
      const entry = mine[sticker.id];
      let label = sticker.numero;
      if (!label || sticker.seccion.startsWith("EXTRA STICKER ")) {
        label = sticker.nombre;
      } else if (numberCounts.get(JSON.stringify([sticker.seccion, sticker.numero])) > 1) {
        const edition = /^(\d+)ed$/.exec(sticker.edicion || "1ed");
        label += ` ${sticker.nombre}${edition ? ` (${edition[1]}ª ed)` : ""}`;
      }
      if (!entry && !unwanted.has(sticker.id)) {
        if (!missing.has(sticker.seccion)) missing.set(sticker.seccion, []);
        missing.get(sticker.seccion).push(label);
        missingCount += 1;
      }
      if (entry?.copies > 1) {
        if (!duplicates.has(sticker.seccion)) duplicates.set(sticker.seccion, []);
        const spare = entry.copies - 1;
        duplicates.get(sticker.seccion).push(`${label} (×${spare})`);
        duplicateCount += 1;
        extraCopies += spare;
      }
    }
    const sections = (groups) => [...groups]
      .map(([section, labels]) => `*${section}*\n${labels.join(", ")}`)
      .join("\n\n");
    const parts = ["*Mi álbum LALIGA 2026-27*"];
    if (kind !== "duplicates") {
      parts.push(
        `*ME FALTAN: ${missingCount} ${missingCount === 1 ? "cromo" : "cromos"}*\n\n`
        + (missingCount ? sections(missing) : "No me falta ningún cromo de los que colecciono."),
      );
    }
    if (kind !== "missing") {
      parts.push(
        `*REPETIDOS: ${duplicateCount} ${duplicateCount === 1 ? "cromo" : "cromos"}, `
        + `${extraCopies} ${extraCopies === 1 ? "copia disponible" : "copias disponibles"}*\n`
        + "Las cantidades (×N) son copias sobrantes para cambiar; conservo una.\n\n"
        + (duplicateCount ? sections(duplicates) : "No tengo cromos repetidos para ofrecer."),
      );
    }
    return parts.join("\n\n");
  }

  function updateShareList() {
    const preview = content.querySelector("#share-list-text");
    if (!preview || activeTab !== "share") return;
    preview.value = collectionListText(shareListKind);
    content.querySelector("#share-list-kind").value = shareListKind;
    content.querySelector("[data-share-list-native]")
      .classList.toggle("hidden", typeof navigator.share !== "function");
  }

  function selectShareList() {
    const preview = content.querySelector("#share-list-text");
    if (!preview) return;
    preview.focus();
    preview.select();
  }

  async function shareCollectionList(native) {
    if (!requireUser()) return;
    try {
      updateShareList();
      const text = collectionListText(shareListKind);
      if (native) {
        if (typeof navigator.share !== "function") {
          selectShareList();
          showNotice("Usa «Copiar para WhatsApp» o copia el texto de la vista previa.", true);
          return;
        }
        await navigator.share({ text });
        showNotice("Lista compartida.");
      } else {
        if (!navigator.clipboard?.writeText) {
          selectShareList();
          showNotice("Tu navegador no permite copiar automáticamente. Copia el texto seleccionado y pégalo en WhatsApp.", true);
          return;
        }
        await navigator.clipboard.writeText(text);
        showNotice("Lista copiada. Pégala en el chat de WhatsApp que quieras.");
      }
    } catch (error) {
      if (native && error?.name === "AbortError") return;
      console.error("No se pudo compartir la lista de cromos.", error);
      selectShareList();
      showNotice("No se pudo compartir automáticamente. Puedes copiar el texto seleccionado y pegarlo en WhatsApp.", true);
    }
  }

  async function renderShare() {
    const version = ++shareViewVersion;
    const ownerId = user?.id;
    content.innerHTML = modalShell(`
      <section class="social-card social-intro share-list-card">
        <strong>Listas para WhatsApp</strong>
        <p>Envía tus faltantes o repetidos a cualquiera, aunque no use esta web. Se comparte todo tu álbum, sin aplicar los filtros de pantalla.</p>
        <label class="share-list-label" for="share-list-kind">Qué quieres compartir</label>
        <select id="share-list-kind">
          <option value="missing">Los que me faltan</option>
          <option value="duplicates">Mis repetidos</option>
          <option value="both">Faltantes y repetidos</option>
        </select>
        <p>Tus «No pegar» no aparecen como faltantes. En repetidos, ×N indica las copias que puedes ofrecer, guardándote una.</p>
        <label class="share-list-label" for="share-list-text">Vista previa del mensaje</label>
        <textarea id="share-list-text" readonly spellcheck="false"></textarea>
        <div class="share-list-actions">
          <button class="social-primary" type="button" data-copy-collection-list>Copiar para WhatsApp</button>
          <button class="button secondary hidden" type="button" data-share-list-native>Compartir texto…</button>
        </div>
        <p>Con «Compartir texto…» puedes elegir WhatsApp si tu dispositivo lo permite. Si no aparece, copia y pega el mensaje; no se envía nada automáticamente.</p>
      </section>
      <section class="social-card social-intro">
        <strong>Enlace de sólo lectura</strong>
        <p>Muestra qué cromos tienes y cuántas copias, sin revelar «No pegar», tu correo ni tu cuenta.</p>
        <button class="social-primary" type="button" data-create-share>Crear enlace actualizado</button>
      </section>
      <section>
        <h3>Enlaces activos</h3>
        <div id="share-links"><p class="social-empty">Cargando enlaces…</p></div>
      </section>
    `);
    updateShareList();
    try {
      const { data, error } = await client.rpc("list_album_shares");
      if (error) throw error;
      if (version !== shareViewVersion || user?.id !== ownerId || activeTab !== "share") return;
      const links = (data || []).map((share) => {
        const url = `${baseUrl()}?share=${share.id}`;
        return `
          <div class="social-row">
            <div><strong>Álbum público</strong><small>${formatDate(share.created_at)}</small></div>
            <div class="social-row-actions">
              <button type="button" data-share-url="${escapeHtml(url)}">Compartir</button>
              <button class="danger" type="button" data-revoke-share="${share.id}">Revocar</button>
            </div>
          </div>
        `;
      }).join("");
      content.querySelector("#share-links").innerHTML =
        links || '<p class="social-empty">No tienes enlaces públicos activos.</p>';
    } catch (error) {
      if (version !== shareViewVersion || user?.id !== ownerId || activeTab !== "share") return;
      console.error("No se pudieron cargar los enlaces del álbum.", error);
      content.querySelector("#share-links").innerHTML =
        '<p class="social-empty">No se pudieron cargar los enlaces. Las listas de texto siguen disponibles.</p>';
      showNotice("No se pudieron cargar los enlaces. Puedes seguir copiando o compartiendo tus listas.", true);
    }
  }

  function comparisons(friend) {
    const mine = album.getSocialProgress();
    const unwanted = album.getUnwantedStickerIds();
    const theirs = friend.progress || {};
    const friendCanGive = [];
    const iCanGive = [];
    for (const [id, entry] of Object.entries(theirs)) {
      if (entry.copies >= 2 && !mine[id] && !unwanted.has(id)) friendCanGive.push(id);
    }
    for (const [id, entry] of Object.entries(mine)) {
      if (entry.copies >= 2 && !theirs[id]) iCanGive.push(id);
    }
    return { friendCanGive, iCanGive };
  }

  async function loadFriends() {
    const { data, error } = await client.rpc("get_album_friends");
    if (error) throw error;
    friends = data || [];
  }

  async function renderFriends() {
    await loadFriends();
    const inviteUrl = `${baseUrl()}?friend=${profile.inviteToken}`;
    const rows = friends.map((friend) => {
      const comparison = comparisons(friend);
      return `
        <div class="friend-row">
          ${friend.avatar_url ? `<img src="${escapeHtml(friend.avatar_url)}" alt="">` : '<span class="friend-avatar">●</span>'}
          <div>
            <strong>${escapeHtml(friend.display_name)}</strong>
            <small>${comparison.friendCanGive.length} para ti · ${comparison.iCanGive.length} para ofrecer</small>
          </div>
          <button type="button" data-compare-friend="${escapeHtml(friend.user_id)}">Comparar</button>
        </div>
      `;
    }).join("");
    content.innerHTML = modalShell(`
      <section class="social-card social-intro">
        <strong>Añadir amigos</strong>
        <p>Comparte tu invitación. La otra persona debe iniciar sesión para aceptar.</p>
        <button class="social-primary" type="button" data-share-url="${escapeHtml(inviteUrl)}">Compartir invitación</button>
      </section>
      <section>
        <h3>Mis amigos</h3>
        ${rows || '<p class="social-empty">Todavía no has añadido amigos.</p>'}
      </section>
    `);
  }

  function tradeItems(items) {
    return (items || []).map((item) => `<li>${escapeHtml(stickerName(item.id))}</li>`).join("");
  }

  async function renderTrades() {
    const { data, error } = await client.rpc("list_album_trades");
    if (error) throw error;
    const rows = (data || []).map((trade) => {
      const received = trade.recipient_id === user.id;
      const counterpart = received ? trade.proposer_name : trade.recipient_name;
      const actions = trade.status !== "pending" ? "" : received
        ? `<button type="button" data-trade-response="${trade.id}" data-status="accepted">Aceptar</button>
           <button class="danger" type="button" data-trade-response="${trade.id}" data-status="rejected">Rechazar</button>`
        : `<button class="danger" type="button" data-trade-response="${trade.id}" data-status="cancelled">Cancelar</button>`;
      return `
        <article class="trade-card">
          <div class="trade-heading">
            <strong>${escapeHtml(counterpart)}</strong>
            <span class="trade-status status-${trade.status}">${escapeHtml(trade.status)}</span>
          </div>
          <div class="trade-columns">
            <div><small>${received ? "Te ofrece" : "Ofreces"}</small><ul>${tradeItems(trade.offered)}</ul></div>
            <div><small>${received ? "Te pide" : "Pides"}</small><ul>${tradeItems(trade.requested)}</ul></div>
          </div>
          ${trade.message ? `<p>${escapeHtml(trade.message)}</p>` : ""}
          <div class="social-row-actions">${actions}</div>
        </article>
      `;
    }).join("");
    content.innerHTML = modalShell(`
      <section>
        <h3>Propuestas de intercambio</h3>
        <p class="social-help">Aceptar no cambia automáticamente ningún álbum. Confirmad el intercambio y actualizad después las copias.</p>
        <button class="social-primary" type="button" data-open-pool>Crear Intercambio Grupal</button>
        ${rows || '<p class="social-empty">No hay propuestas todavía.</p>'}
      </section>
    `);
  }

  function checkboxList(ids, side) {
    return ids.map((id) => `
      <label class="trade-option">
        <input type="checkbox" data-trade-item="${escapeHtml(id)}" data-side="${side}">
        <span>${escapeHtml(stickerName(id))}</span>
      </label>
    `).join("");
  }

  function renderComparison(friend) {
    if (!friend) return;
    comparisonFriendId = friend.user_id;
    const { friendCanGive, iCanGive } = comparisons(friend);
    content.innerHTML = `
      <div class="social-header">
        <div><span>Comparación</span><h2>${escapeHtml(friend.display_name)}</h2></div>
        <button class="social-close" type="button" data-social-close aria-label="Cerrar">×</button>
      </div>
      <div class="social-notice" id="social-notice" role="status"></div>
      <div class="social-body">
        <button class="social-back" type="button" data-social-back>← Amigos</button>
        <div class="trade-columns comparison-columns">
          <section>
            <h3>Te puede dar <span>${friendCanGive.length}</span></h3>
            <div class="trade-options">${checkboxList(friendCanGive, "requested") || '<p class="social-empty">Ningún repetido que te falte.</p>'}</div>
          </section>
          <section>
            <h3>Puedes ofrecer <span>${iCanGive.length}</span></h3>
            <div class="trade-options">${checkboxList(iCanGive, "offered") || '<p class="social-empty">Ningún repetido que le falte.</p>'}</div>
          </section>
        </div>
        <label class="social-message">Mensaje opcional<textarea id="trade-message" maxlength="500" placeholder="¿Te parece bien este cambio?"></textarea></label>
        <button class="social-primary" type="button" data-create-trade="${escapeHtml(friend.user_id)}">Enviar propuesta</button>
      </div>
    `;
  }

  function poolInventory(id, progress, excluded = new Set()) {
    const offered = {};
    const missing = [];
    let ownedCount = 0;
    for (const stickerId of stickers.keys()) {
      const entry = progress[stickerId];
      if (!entry) {
        if (!excluded.has(stickerId)) missing.push(stickerId);
        continue;
      }
      if (!Number.isSafeInteger(entry.copies) || entry.copies < 0) {
        throw new Error("Hay un inventario con un número de copias no válido.");
      }
      if (entry.state === "owned" || entry.copies > 0) {
        ownedCount += 1;
        if (entry.copies > 1) offered[stickerId] = entry.copies - 1;
      } else if (!excluded.has(stickerId)) {
        missing.push(stickerId);
      }
    }
    return { id, offered, missing, ownedCount };
  }

  function poolMembers(ids) {
    if (!user || album.isAuthRequired() || album.isReadOnly()) {
      throw new Error("Inicia sesión en tu propio álbum para calcular un intercambio grupal.");
    }
    const members = [{
      name: user.fullName || user.firstName || "Mi cuenta",
      inventory: poolInventory(user.id, album.getSocialProgress(), album.getUnwantedStickerIds()),
    }];
    for (const id of ids) {
      const friend = friends.find((item) => item.user_id === id);
      if (!friend || id === user.id) {
        throw new Error("La lista de amigos ha cambiado. Vuelve a elegir los participantes.");
      }
      members.push({
        name: friend.display_name,
        inventory: poolInventory(id, friend.progress || {}),
      });
    }
    return members;
  }

  function cancelPoolJob() {
    const job = poolJob;
    poolJob = null;
    if (job?.cancel) job.cancel();
    job?.worker?.terminate();
  }

  function updatePoolControls() {
    const calculate = content.querySelector("[data-calculate-pool]");
    if (calculate) calculate.disabled = Boolean(poolJob) || !poolSelection.size;
    const cancel = content.querySelector("[data-cancel-pool]");
    if (cancel) cancel.classList.toggle("hidden", !poolJob);
  }

  function setPoolStatus(message) {
    const status = content.querySelector("#pool-status");
    if (status) status.textContent = message;
  }

  function invalidatePool(message) {
    cancelPoolJob();
    poolPlan = null;
    if (activeTab !== "pool") return;
    content.querySelector("#social-notice")?.classList.remove("visible");
    const results = content.querySelector("#pool-results");
    if (results) results.replaceChildren();
    setPoolStatus(message);
    updatePoolControls();
  }

  async function renderPool() {
    const version = ++poolViewVersion;
    invalidatePool("");
    content.innerHTML = modalShell('<p class="social-empty">Cargando inventarios de tus amigos…</p>');
    await loadFriends();
    if (version !== poolViewVersion || activeTab !== "pool" || !user) return;
    const availableIds = new Set(friends.map((friend) => friend.user_id));
    poolSelection = new Set([...poolSelection].filter((id) => availableIds.has(id)));
    const members = poolMembers(friends.map((friend) => friend.user_id));
    const options = members.map((member, index) => {
      const inventory = member.inventory;
      const copies = Object.values(inventory.offered).reduce((total, quantity) => total + quantity, 0);
      return `
        <label class="pool-member">
          <input type="checkbox" data-pool-member="${escapeHtml(inventory.id)}"
            ${index === 0 ? "checked disabled" : poolSelection.has(inventory.id) ? "checked" : ""}>
          <span><strong>${escapeHtml(member.name)}${index === 0 ? " (tú)" : ""}</strong>
            <small>${copies} ${copies === 1 ? "copia repetida" : "copias repetidas"} · ${inventory.missing.length} ${inventory.missing.length === 1 ? "falta" : "faltas"}</small></span>
        </label>
      `;
    }).join("");
    content.innerHTML = modalShell(`
      <section class="social-card social-intro">
        <strong>Crear Intercambio Grupal</strong>
        <p>Elige los amigos que participan contigo. Buscaremos el máximo total de cromos que pueden cambiar de dueño, también en ciclos de tres o más personas.</p>
        <p>Solo cuenta lo que se entrega a otro participante: todos dan y reciben la misma cantidad. Conservas una copia de cada cromo y solo recibes cromos que te faltan.</p>
      </section>
      <p class="social-help">Tus «No pegar» se excluyen de lo que recibes. Las faltas de los amigos se deducen de su colección; sus decisiones «No pegar» siguen siendo privadas.</p>
      <fieldset class="pool-members">
        <legend>Participantes</legend>
        ${options}
      </fieldset>
      ${friends.length ? "" : '<p class="social-empty">Añade algún amigo para crear un intercambio grupal.</p>'}
      <div class="pool-actions">
        <button class="social-primary" type="button" data-calculate-pool ${poolSelection.size ? "" : "disabled"}>Calcular reparto óptimo</button>
        <button class="button secondary hidden" type="button" data-cancel-pool>Cancelar cálculo</button>
      </div>
      <p class="social-help" id="pool-status" role="status">Selecciona al menos un amigo. No se cambiará ningún álbum.</p>
      <div id="pool-results" aria-live="polite"></div>
    `);
  }

  function solvePool(job, participants) {
    return new Promise((resolve, reject) => {
      if (typeof Worker !== "function") {
        reject(new Error("Este navegador no permite el cálculo en segundo plano. Prueba con un navegador actualizado."));
        return;
      }
      const worker = new Worker("pool-worker.js?v=1");
      job.worker = worker;
      job.cancel = () => {
        const error = new Error("Cálculo cancelado.");
        error.name = "AbortError";
        reject(error);
      };
      worker.addEventListener("message", (event) => {
        if (event.data.error) reject(new Error(event.data.error));
        else resolve(event.data.result);
      });
      worker.addEventListener("error", () => reject(new Error("No se pudo ejecutar el optimizador del intercambio.")));
      worker.addEventListener("messageerror", () => reject(new Error("No se pudo leer el resultado del optimizador.")));
      worker.postMessage({ participants });
    });
  }

  function renderPoolResult(plan) {
    const names = new Map(plan.members.map((member) => [member.inventory.id, member.name]));
    const rows = plan.result.participants.map((member) => `
      <tr>
        <th scope="row">${escapeHtml(names.get(member.id))}</th>
        <td>${member.given}</td><td>${member.received}</td>
        <td>${member.balance}</td><td>${member.available - member.given}</td>
      </tr>
    `).join("");
    const deliveries = new Map();
    for (const transfer of plan.result.transfers) {
      const key = JSON.stringify([transfer.from, transfer.to]);
      if (!deliveries.has(key)) deliveries.set(key, []);
      deliveries.get(key).push(transfer);
    }
    const routes = [...deliveries.values()].map((items) => `
      <details class="pool-delivery">
        <summary>${escapeHtml(names.get(items[0].from))} → ${escapeHtml(names.get(items[0].to))} · ${items.length} ${items.length === 1 ? "cromo" : "cromos"}</summary>
        <ul>${items.map((item) => `<li>${escapeHtml(stickerName(item.stickerId))}</li>`).join("")}</ul>
      </details>
    `).join("");
    content.querySelector("#pool-results").innerHTML = `
      <section class="pool-result">
        <h3>${plan.result.totalTransfers} cromos pueden cambiar de dueño</h3>
        <p class="social-help">${plan.result.totalTransfers
          ? "Depositad primero las aportaciones indicadas y repartid después. El total cuenta cada copia transferida una sola vez."
          : "No existe un reparto 1:1 con estos inventarios. Un repetido que nadie recibe no genera saldo."}</p>
        <div class="pool-table-wrap">
          <table class="pool-table">
            <caption>Saldo por participante</caption>
            <thead><tr><th scope="col">Participante</th><th scope="col">Aporta</th><th scope="col">Recibe</th><th scope="col">Saldo</th><th scope="col">Sin usar</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
        ${routes}
        <p class="social-help">Calculado el ${escapeHtml(new Date(plan.computedAt).toLocaleString("es"))}. Es un plan, no una reserva ni una propuesta enviada. Recalculad si cambian los inventarios y actualizad las copias manualmente tras el intercambio.</p>
        <button class="button" type="button" data-download-pool>Descargar plan para compartir</button>
      </section>
    `;
  }

  async function calculatePool() {
    if (!requireUser()) return;
    if (!poolSelection.size) {
      showNotice("Selecciona al menos un amigo para el intercambio.", true);
      return;
    }
    invalidatePool("Actualizando los inventarios…");
    const job = { userId: user.id, worker: null, cancel: null };
    poolJob = job;
    const selectedIds = [...poolSelection];
    updatePoolControls();
    try {
      await loadFriends();
      if (poolJob !== job || activeTab !== "pool" || user?.id !== job.userId) return;
      const members = poolMembers(selectedIds);
      setPoolStatus("Calculando el máximo global… Puedes cancelar sin modificar ningún álbum.");
      const result = await solvePool(job, members.map((member) => member.inventory));
      if (poolJob !== job) return;
      poolPlan = { members, result, computedAt: new Date().toISOString() };
      renderPoolResult(poolPlan);
      setPoolStatus("Cálculo óptimo completado. No se ha modificado ningún álbum.");
    } catch (error) {
      if (poolJob !== job) return;
      poolPlan = null;
      content.querySelector("#pool-results")?.replaceChildren();
      console.error("No se pudo calcular el intercambio grupal.", error);
      setPoolStatus("El cálculo no se ha completado.");
      showNotice(error instanceof Error ? error.message : "No se pudo calcular el intercambio grupal.", true);
    } finally {
      job.worker?.terminate();
      if (poolJob === job) {
        poolJob = null;
        updatePoolControls();
      }
    }
  }

  function poolPlanText(plan) {
    const names = new Map(plan.members.map((member) => [member.inventory.id, member.name]));
    const lines = [
      "Intercambio grupal - Panini LALIGA 2026-27",
      `Calculado: ${new Date(plan.computedAt).toLocaleString("es")}`,
      `Cromos transferidos: ${plan.result.totalTransfers}`,
      "Depositad primero las aportaciones indicadas y repartid despues.",
      "",
      ...plan.result.participants.map((member) =>
        `${names.get(member.id)}: aporta ${member.given}, recibe ${member.received}, saldo ${member.balance}`),
      "",
      ...plan.result.transfers.map((item) =>
        `${names.get(item.from)} -> ${names.get(item.to)}: ${stickerName(item.stickerId)}`),
      "",
      "Plan sin reservas. Recalcular si cambian los inventarios. Actualizad las copias manualmente.",
    ];
    return lines.join("\n");
  }

  function downloadPoolPlan() {
    if (!poolPlan) {
      showNotice("Calcula un reparto actualizado antes de descargarlo.", true);
      return;
    }
    const blob = new Blob([poolPlanText(poolPlan)], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "intercambio-grupal-panini.txt";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function openPool() {
    if (!requireUser()) return;
    activeTab = "pool";
    dialog.showModal();
    await renderActiveTab();
  }

  async function renderActiveTab() {
    if (!requireUser()) return;
    comparisonFriendId = null;
    if (activeTab !== "pool") {
      poolViewVersion += 1;
      invalidatePool("");
    }
    try {
      if (activeTab === "friends") await renderFriends();
      else if (activeTab === "trades") await renderTrades();
      else if (activeTab === "pool") await renderPool();
      else await renderShare();
    } catch (error) {
      console.error("No se pudo cargar la sección social.", error);
      content.innerHTML = modalShell('<p class="social-empty">No se pudo cargar esta sección.</p>');
      showNotice(activeTab === "pool"
        ? error instanceof Error
          ? error.message
          : "No se pudieron cargar los inventarios. Comprueba tu conexión y vuelve a abrir Grupal."
        : "Comprueba que la migración social está instalada.", true);
    }
  }

  function friendSummary(friend) {
    const theirs = friend.progress || {};
    let owned = 0;
    let duplicates = 0;
    for (const entry of Object.values(theirs)) {
      if (entry.state === "owned" || entry.copies > 0) owned += 1;
      if (entry.copies >= 2) duplicates += 1;
    }
    return { owned, duplicates, missing: stickers.size - owned };
  }

  function renderFriendsPanel(container) {
    if (!container) return;
    if (!user) {
      container.innerHTML = `
        <div class="friends-empty">
          <strong>Inicia sesión para ver a tus amigos</strong>
          <p>Con una cuenta puedes comparar colecciones, proponer intercambios y ver sus álbumes.</p>
          <button class="button" type="button" data-social-login>Iniciar sesión</button>
        </div>
      `;
      return;
    }
    const inviteUrl = profile ? `${baseUrl()}?friend=${profile.inviteToken}` : "";
    const cards = friends.map((friend) => {
      const totals = friendSummary(friend);
      const comparison = comparisons(friend);
      return `
        <article class="friend-card">
          <header>
            ${friend.avatar_url
              ? `<img src="${escapeHtml(friend.avatar_url)}" alt="" referrerpolicy="no-referrer">`
              : '<span class="friend-avatar">●</span>'}
            <div>
              <strong>${escapeHtml(friend.display_name)}</strong>
              <small>${totals.owned} cromos · ${totals.duplicates} repetidos</small>
            </div>
          </header>
          <p class="friend-trade-summary">
            <span class="friend-tally tally-owned">${comparison.friendCanGive.length}</span> te puede dar
            <span class="friend-tally tally-duplicates">${comparison.iCanGive.length}</span> le puedes dar
          </p>
          <div class="friend-actions">
            <button class="button secondary" type="button" data-open-friend-album="${escapeHtml(friend.user_id)}">Ver su álbum</button>
            <button class="button" type="button" data-open-friend-trade="${escapeHtml(friend.user_id)}">Intercambiar</button>
          </div>
        </article>
      `;
    }).join("");
    container.innerHTML = `
      <div class="friends-toolbar">
        <div>
          <strong>Mis amigos</strong>
          <small>${friends.length} ${friends.length === 1 ? "amigo" : "amigos"}</small>
        </div>
        <div class="friends-toolbar-actions">
          ${inviteUrl ? `<button class="button secondary" type="button" data-share-url="${escapeHtml(inviteUrl)}">Invitar</button>` : ""}
          <button class="button" type="button" data-open-trades>Propuestas</button>
          <button class="button" type="button" data-open-pool>Crear Intercambio Grupal</button>
        </div>
      </div>
      ${cards || '<div class="friends-empty"><strong>Todavía no tienes amigos</strong><p>Comparte tu invitación para comparar colecciones y proponer intercambios.</p></div>'}
    `;
  }

  async function refreshFriendsPanel(container) {
    const target = container || document.querySelector("#friends-panel");
    if (!target) return;
    if (!user || !client) {
      renderFriendsPanel(target);
      return;
    }
    target.innerHTML = '<p class="social-empty">Cargando amigos…</p>';
    try {
      if (!profile) await ensureProfile();
      await loadFriends();
      renderFriendsPanel(target);
    } catch (error) {
      console.error("No se pudieron cargar los amigos.", error);
      target.innerHTML = '<div class="friends-empty"><strong>No se pudieron cargar tus amigos</strong><p>Comprueba tu conexión e inténtalo de nuevo.</p></div>';
    }
  }

  async function ensureProfile() {
    if (!user) return;
    const displayName = user.fullName || user.firstName || "Coleccionista";
    const { data, error } = await client.rpc("ensure_album_profile", {
      p_display_name: displayName,
      p_avatar_url: user.imageUrl || null,
    });
    if (error) throw error;
    profile = { inviteToken: data };
    await window.PaniniCloud.syncNow();
  }

  async function loadPublicShare() {
    if (!shareId) return false;
    const { data, error } = await client.rpc("get_shared_album", { p_id: shareId });
    if (error || !data?.length) {
      content.innerHTML = modalShell('<p class="social-empty">Este enlace no existe o ha sido revocado.</p>');
      dialog.showModal();
      return true;
    }
    const shared = data[0];
    album.showReadOnly(shared.snapshot || {}, shared.owner_name);
    document.title = `Álbum de ${shared.owner_name}`;
    return true;
  }

  async function acceptInvite() {
    if (!friendToken || !user) return;
    const { error } = await client.rpc("accept_album_invite", { p_token: friendToken });
    if (error) {
      console.error("No se pudo aceptar la invitación.", error);
      showNotice("La invitación no es válida o ha caducado.", true);
      return;
    }
    clearFriendToken();
    activeTab = "friends";
    await renderActiveTab();
    showNotice("Amigo añadido.");
  }

  function clearFriendToken() {
    const url = new URL(window.location.href);
    url.searchParams.delete("friend");
    window.history.replaceState(window.history.state, "", url);
  }

  async function renderInviteConfirmation() {
    if (!friendToken || !user) return;
    if (window.top !== window.self) {
      content.innerHTML = modalShell(`
        <section class="social-card social-intro">
          <strong>Abre la invitación directamente</strong>
          <p>Por seguridad, las invitaciones de amistad no se pueden aceptar dentro de otra página.</p>
          <button type="button" data-decline-invite>Cerrar</button>
        </section>
      `);
      dialog.showModal();
      return;
    }
    const { data, error } = await client.rpc("get_album_invite", { p_token: friendToken });
    const inviter = data?.[0]?.display_name;
    if (error || !inviter) {
      content.innerHTML = modalShell(`
        <section class="social-card social-intro">
          <strong>Invitación no disponible</strong>
          <p>Este enlace no existe o ha caducado.</p>
          <button type="button" data-decline-invite>Cerrar</button>
        </section>
      `);
    } else {
      content.innerHTML = modalShell(`
        <section class="social-card social-intro">
          <strong>${escapeHtml(inviter)} quiere añadirte como amigo</strong>
          <p>Si aceptas, ambos podréis comparar colecciones y enviar propuestas de intercambio.</p>
          <div class="social-row-actions">
            <button class="social-primary" type="button" data-accept-invite>Aceptar amistad</button>
            <button type="button" data-decline-invite>Ahora no</button>
          </div>
        </section>
      `);
    }
    dialog.showModal();
  }

  async function initialize(event) {
    poolViewVersion += 1;
    invalidatePool("La sesión o el álbum ha cambiado. Vuelve a calcular el reparto.");
    if (user?.id !== event.detail.user?.id) {
      poolSelection.clear();
      shareViewVersion += 1;
      if (dialog.open) dialog.close();
      content.replaceChildren();
    }
    client = event.detail.client;
    user = event.detail.user;
    if (await loadPublicShare()) return;
    if (!user) {
      if (friendToken) {
        const { data } = await client.rpc("get_album_invite", { p_token: friendToken });
        const inviter = data?.[0]?.display_name || "otro coleccionista";
        content.innerHTML = modalShell(`
          <section class="social-card social-intro">
            <strong>${escapeHtml(inviter)} quiere añadirte como amigo</strong>
            <p>Inicia sesión para comparar colecciones y proponer intercambios.</p>
            <div class="social-row-actions">
              <button class="social-primary" type="button" data-social-login>Iniciar sesión</button>
              <button type="button" data-social-signup>Registrarse</button>
            </div>
          </section>
        `);
        dialog.showModal();
      }
      return;
    }
    try {
      await ensureProfile();
      await renderInviteConfirmation();
      await refreshFriendsPanel();
    } catch (error) {
      console.error("No se pudo preparar la función social.", error);
    }
  }

  openButton.addEventListener("click", async () => {
    if (!requireUser()) return;
    activeTab = "share";
    dialog.showModal();
    await renderActiveTab();
  });

  dialog.addEventListener("close", () => {
    poolViewVersion += 1;
    shareViewVersion += 1;
    invalidatePool("");
  });

  dialog.addEventListener("change", (event) => {
    if (event.target.closest("#share-list-kind")) {
      shareListKind = event.target.value;
      updateShareList();
      return;
    }
    const member = event.target.closest("[data-pool-member]");
    if (!member || member.disabled) return;
    if (member.checked) poolSelection.add(member.dataset.poolMember);
    else poolSelection.delete(member.dataset.poolMember);
    invalidatePool("El grupo ha cambiado. Calcula el reparto para esta selección.");
  });

  dialog.addEventListener("click", async (event) => {
    if (event.target === dialog || event.target.closest("[data-social-close]")) {
      dialog.close();
      return;
    }
    const tab = event.target.closest("[data-social-tab]");
    if (tab) {
      activeTab = tab.dataset.socialTab;
      await renderActiveTab();
      return;
    }
    if (event.target.closest("[data-social-login]")) {
      dialog.close();
      window.PaniniCloud.signIn();
      return;
    }
    if (event.target.closest("[data-social-signup]")) {
      dialog.close();
      window.PaniniCloud.signUp?.();
      return;
    }
    if (event.target.closest("[data-copy-collection-list]")) {
      await shareCollectionList(false);
      return;
    }
    if (event.target.closest("[data-share-list-native]")) {
      await shareCollectionList(true);
      return;
    }
    if (event.target.closest("[data-open-pool]")) {
      await openPool();
      return;
    }
    if (event.target.closest("[data-calculate-pool]")) {
      await calculatePool();
      return;
    }
    if (event.target.closest("[data-cancel-pool]")) {
      invalidatePool("Cálculo cancelado. No se ha modificado ningún álbum.");
      return;
    }
    if (event.target.closest("[data-download-pool]")) {
      downloadPoolPlan();
      return;
    }
    if (event.target.closest("[data-accept-invite]")) {
      await acceptInvite();
      return;
    }
    if (event.target.closest("[data-decline-invite]")) {
      clearFriendToken();
      dialog.close();
      return;
    }
    if (event.target.closest("[data-create-share]")) {
      const { data, error } = await client.rpc("create_album_share", {
        p_snapshot: album.getSocialProgress(),
      });
      if (error) {
        showNotice("No se pudo crear el enlace.", true);
        return;
      }
      await renderShare();
      await shareUrl(`${baseUrl()}?share=${data}`, "Mi álbum Panini");
      return;
    }
    const shareButton = event.target.closest("[data-share-url]");
    if (shareButton) {
      await shareUrl(shareButton.dataset.shareUrl, "Mi álbum Panini");
      return;
    }
    const revokeButton = event.target.closest("[data-revoke-share]");
    if (revokeButton) {
      await client.rpc("revoke_album_share", { p_id: revokeButton.dataset.revokeShare });
      await renderShare();
      showNotice("Enlace revocado.");
      return;
    }
    const compareButton = event.target.closest("[data-compare-friend]");
    if (compareButton) {
      renderComparison(friends.find((friend) => friend.user_id === compareButton.dataset.compareFriend));
      return;
    }
    if (event.target.closest("[data-social-back]")) {
      comparisonFriendId = null;
      await renderFriends();
      return;
    }
    const createTrade = event.target.closest("[data-create-trade]");
    if (createTrade) {
      const selected = [...content.querySelectorAll("[data-trade-item]:checked")];
      const offered = selected.filter((item) => item.dataset.side === "offered")
        .map((item) => ({ id: item.dataset.tradeItem, quantity: 1 }));
      const requested = selected.filter((item) => item.dataset.side === "requested")
        .map((item) => ({ id: item.dataset.tradeItem, quantity: 1 }));
      if (!offered.length || !requested.length) {
        showNotice("Selecciona al menos un cromo de cada lado.", true);
        return;
      }
      const { error } = await client.rpc("create_album_trade", {
        p_recipient_id: createTrade.dataset.createTrade,
        p_offered: offered,
        p_requested: requested,
        p_message: content.querySelector("#trade-message").value.trim(),
      });
      if (error) {
        showNotice("No se pudo enviar la propuesta.", true);
        return;
      }
      activeTab = "trades";
      await renderTrades();
      showNotice("Propuesta enviada.");
      return;
    }
    const response = event.target.closest("[data-trade-response]");
    if (response) {
      await client.rpc("respond_album_trade", {
        p_id: response.dataset.tradeResponse,
        p_status: response.dataset.status,
      });
      await renderTrades();
    }
  });

  document.addEventListener("panini:friends-render", (event) => {
    refreshFriendsPanel(event.detail.container);
  });

  document.addEventListener("panini:progress-changed", () => {
    invalidatePool("Tu álbum ha cambiado. Vuelve a calcular el reparto.");
    if (!user) return;
    if (dialog.open && activeTab === "share") updateShareList();
    const panel = document.querySelector("#friends-panel");
    if (panel) {
      renderFriendsPanel(panel);
    }
    if (!dialog.open || activeTab !== "friends" || !comparisonFriendId) return;
    const friend = friends.find((item) => item.user_id === comparisonFriendId);
    if (friend) {
      renderComparison(friend);
    }
  });

  document.addEventListener("click", async (event) => {
    const albumButton = event.target.closest("[data-open-friend-album]");
    if (albumButton) {
      const friend = friends.find((item) => item.user_id === albumButton.dataset.openFriendAlbum);
      if (friend) album.previewFriend(friend.display_name, friend.progress || {});
      return;
    }
    const tradeButton = event.target.closest("[data-open-friend-trade]");
    if (tradeButton) {
      const friend = friends.find((item) => item.user_id === tradeButton.dataset.openFriendTrade);
      if (!friend) return;
      activeTab = "friends";
      renderComparison(friend);
      dialog.showModal();
      return;
    }
    if (event.target.closest("#friends-panel [data-open-trades]")) {
      activeTab = "trades";
      await renderActiveTab();
      dialog.showModal();
      return;
    }
    if (event.target.closest("#friends-panel [data-open-pool]")) {
      await openPool();
      return;
    }
    const panelShare = event.target.closest("#friends-panel [data-share-url]");
    if (panelShare) {
      await shareUrl(panelShare.dataset.shareUrl, "Únete a mi álbum Panini");
      return;
    }
    if (event.target.closest("#friends-panel [data-social-login]")) {
      window.PaniniCloud?.signIn();
    }
  });

  document.addEventListener("panini:cloud-ready", initialize);
})();
