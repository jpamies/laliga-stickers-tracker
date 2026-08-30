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
        <button class="${activeTab === "share" ? "active" : ""}" type="button" data-social-tab="share">Enlaces</button>
        <button class="${activeTab === "friends" ? "active" : ""}" type="button" data-social-tab="friends">Amigos</button>
        <button class="${activeTab === "trades" ? "active" : ""}" type="button" data-social-tab="trades">Propuestas</button>
      </div>
      <div class="social-notice" id="social-notice" role="status"></div>
      <div class="social-body">${body}</div>
    `;
  }

  async function renderShare() {
    const { data, error } = await client.rpc("list_album_shares");
    if (error) throw error;
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
    content.innerHTML = modalShell(`
      <section class="social-card social-intro">
        <strong>Enlace de sólo lectura</strong>
        <p>Muestra qué cromos tienes y cuántas copias, sin revelar «No pegar», tu correo ni tu cuenta.</p>
        <button class="social-primary" type="button" data-create-share>Crear enlace actualizado</button>
      </section>
      <section>
        <h3>Enlaces activos</h3>
        ${links || '<p class="social-empty">No tienes enlaces públicos activos.</p>'}
      </section>
    `);
  }

  function comparisons(friend) {
    const mine = album.getSocialProgress();
    const theirs = friend.progress || {};
    const friendCanGive = [];
    const iCanGive = [];
    for (const [id, entry] of Object.entries(theirs)) {
      if (entry.copies >= 2 && !mine[id]) friendCanGive.push(id);
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

  async function renderActiveTab() {
    if (!requireUser()) return;
    try {
      if (activeTab === "friends") await renderFriends();
      else if (activeTab === "trades") await renderTrades();
      else await renderShare();
    } catch (error) {
      console.error("No se pudo cargar la sección social.", error);
      content.innerHTML = modalShell('<p class="social-empty">No se pudo cargar esta sección.</p>');
      showNotice("Comprueba que la migración social está instalada.", true);
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
            <button class="social-primary" type="button" data-social-login>Iniciar sesión</button>
          </section>
        `);
        dialog.showModal();
      }
      return;
    }
    try {
      await ensureProfile();
      await renderInviteConfirmation();
    } catch (error) {
      console.error("No se pudo preparar la función social.", error);
    }
  }

  openButton.addEventListener("click", async () => {
    if (!requireUser()) return;
    await renderActiveTab();
    dialog.showModal();
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
      window.PaniniCloud.signIn();
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

  document.addEventListener("panini:cloud-ready", initialize);
})();
