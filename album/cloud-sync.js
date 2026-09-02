(() => {
  "use strict";

  const config = window.PANINI_CLOUD_CONFIG || {};
  const album = window.PaniniAlbum;
  const elements = {
    button: document.querySelector("#auth-button"),
    avatar: document.querySelector("#account-avatar"),
    name: document.querySelector("#account-name"),
    status: document.querySelector("#sync-status"),
  };
  const updatedKeyBase = "panini-laliga-2026-27-local-updated-at";
  const syncedKeyBase = "panini-laliga-2026-27-last-synced-at";
  const guestScope = "guest";
  let client = null;
  let currentUser = null;
  let saveTimer = null;
  let applyingRemote = false;

  function scopeFor(user) {
    return user ? `user:${user.id}` : guestScope;
  }

  function scopedKey(base) {
    const scope = album.getStorageScope();
    return scope === guestScope ? base : `${base}::${scope}`;
  }

  function updatedKey() {
    return scopedKey(updatedKeyBase);
  }

  function syncedKey() {
    return scopedKey(syncedKeyBase);
  }

  function setStatus(message, isError = false) {
    elements.status.textContent = message;
    elements.status.classList.toggle("sync-error", isError);
  }

  function cloudIsConfigured() {
    return Boolean(
      config.clerkPublishableKey
      && config.clerkScriptUrl
      && config.supabaseUrl
      && config.supabasePublishableKey,
    );
  }

  function loadClerk() {
    return new Promise((resolve, reject) => {
      if (window.Clerk) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = config.clerkScriptUrl;
      script.dataset.clerkPublishableKey = config.clerkPublishableKey;
      script.crossOrigin = "anonymous";
      script.onload = resolve;
      script.onerror = () => reject(new Error("No se pudo cargar Clerk."));
      document.head.append(script);
    });
  }

  function displayUser(user) {
    currentUser = user || null;
    if (!user) {
      elements.name.textContent = "Modo local";
      elements.button.textContent = "Iniciar sesión";
      elements.avatar.classList.add("hidden");
      elements.avatar.removeAttribute("src");
      elements.avatar.alt = "";
      setStatus("Guardado en este dispositivo");
      return;
    }
    const name = user.fullName || user.firstName || "Mi cuenta";
    elements.name.textContent = name;
    elements.button.textContent = "Cerrar sesión";
    if (user.imageUrl) {
      elements.avatar.src = user.imageUrl;
      elements.avatar.alt = `Avatar de ${name}`;
      elements.avatar.classList.remove("hidden");
    }
  }

  function asTimestamp(value) {
    const parsed = Date.parse(value || "");
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function mergeProgress(localProgress, remoteProgress, localUpdated, remoteUpdated) {
    const merged = {};
    const ids = new Set([
      ...Object.keys(remoteProgress || {}),
      ...Object.keys(localProgress || {}),
    ]);
    for (const id of ids) {
      const localEntry = localProgress[id];
      const remoteEntry = remoteProgress[id];
      if (!localEntry) {
        merged[id] = remoteEntry;
        continue;
      }
      if (!remoteEntry) {
        merged[id] = localEntry;
        continue;
      }
      const localEntryUpdated = asTimestamp(localEntry.updatedAt) || localUpdated;
      const remoteEntryUpdated = asTimestamp(remoteEntry.updatedAt) || remoteUpdated;
      merged[id] = localEntryUpdated >= remoteEntryUpdated ? localEntry : remoteEntry;
    }
    return merged;
  }

  async function saveToCloud() {
    if (!currentUser || !client || applyingRemote || album.isReadOnly()) return;
    const updatedAt = localStorage.getItem(updatedKey()) || new Date().toISOString();
    localStorage.setItem(updatedKey(), updatedAt);
    setStatus("Guardando…");
    // La copia que ven los amigos la deriva un disparador en Supabase, así que
    // aquí sólo se guarda el progreso real.
    const { error } = await client.from("album_progress").upsert({
      user_id: currentUser.id,
      progress: album.getProgress(),
      updated_at: updatedAt,
    }, { onConflict: "user_id" });
    if (error) {
      console.error("No se pudo guardar el progreso en Supabase.", error);
      setStatus("Error al sincronizar", true);
      return;
    }
    localStorage.setItem(syncedKey(), updatedAt);
    setStatus("Sincronizado");
  }

  function scheduleSave() {
    if (applyingRemote || album.isReadOnly()) return;
    localStorage.setItem(updatedKey(), new Date().toISOString());
    if (!currentUser) return;
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(() => {
      saveTimer = null;
      saveToCloud();
    }, 600);
  }

  async function synchronize() {
    if (!currentUser || !client || album.isReadOnly()) return;
    setStatus("Sincronizando…");
    const { data, error } = await client
      .from("album_progress")
      .select("progress, updated_at")
      .eq("user_id", currentUser.id)
      .maybeSingle();
    if (error) {
      console.error("No se pudo cargar el progreso desde Supabase.", error);
      setStatus("Error al sincronizar", true);
      return;
    }

    const localProgress = album.getProgress();
    const localUpdatedAt = localStorage.getItem(updatedKey());
    const lastSyncedAt = localStorage.getItem(syncedKey());
    if (!data) {
      if (!localUpdatedAt && Object.keys(localProgress).length) {
        localStorage.setItem(updatedKey(), new Date().toISOString());
      }
      await saveToCloud();
      return;
    }

    const remoteUpdated = asTimestamp(data.updated_at);
    const localUpdated = asTimestamp(localUpdatedAt);
    const lastSynced = asTimestamp(lastSyncedAt);
    const merged = mergeProgress(
      localProgress,
      data.progress || {},
      localUpdated,
      remoteUpdated,
    );
    const mergedChangedRemote = JSON.stringify(merged) !== JSON.stringify(data.progress || {});
    const localChanged = localUpdated > lastSynced;
    if (mergedChangedRemote || localChanged) {
      applyingRemote = true;
      album.replaceProgress(merged);
      applyingRemote = false;
      localStorage.setItem(updatedKey(), new Date().toISOString());
      await saveToCloud();
      return;
    }

    applyingRemote = true;
    album.replaceProgress(data.progress || {});
    applyingRemote = false;
    localStorage.setItem(updatedKey(), data.updated_at);
    localStorage.setItem(syncedKey(), data.updated_at);
    setStatus("Sincronizado");
  }

  async function handleUser(user) {
    displayUser(user);
    if (album.isReadOnly()) {
      document.dispatchEvent(new CustomEvent("panini:cloud-ready", {
        detail: { client, user: currentUser },
      }));
      return;
    }
    const previousScope = album.getStorageScope();
    const nextScope = scopeFor(user);
    const scopeChanged = album.setStorageScope(nextScope);
    if (scopeChanged && user && previousScope === guestScope
      && album.hasStoredProgress(guestScope)) {
      album.showToast(
        "El progreso de invitado se ha guardado aparte. Expórtalo e impórtalo si quieres unirlo a tu cuenta.",
      );
    }
    if (user) {
      await synchronize();
    }
    document.dispatchEvent(new CustomEvent("panini:cloud-ready", {
      detail: { client, user: currentUser },
    }));
  }

  async function initialize() {
    if (!cloudIsConfigured()) {
      elements.button.disabled = true;
      elements.button.textContent = "Nube pendiente";
      setStatus("Supabase aún no está configurado");
      return;
    }
    if (!window.supabase?.createClient) {
      elements.button.disabled = true;
      setStatus("No se pudo cargar Supabase", true);
      return;
    }

    try {
      await loadClerk();
      await window.Clerk.load();
      client = window.supabase.createClient(
        config.supabaseUrl,
        config.supabasePublishableKey,
        {
          accessToken: async () => window.Clerk.session?.getToken() || null,
        },
      );
      window.PaniniCloud = {
        getClient: () => client,
        getUser: () => currentUser,
        signIn: () => elements.button.click(),
        syncNow: saveToCloud,
      };
      await handleUser(window.Clerk.user);
      window.Clerk.addListener(({ user }) => {
        handleUser(user).catch((error) => {
          console.error("No se pudo actualizar la sesión.", error);
          setStatus("Error de sesión", true);
        });
      });
    } catch (error) {
      console.error("No se pudo inicializar la sincronización.", error);
      elements.button.disabled = true;
      setStatus("Nube no disponible", true);
    }
  }

  elements.button.addEventListener("click", async () => {
    if (!window.Clerk) return;
    if (currentUser) {
      await saveToCloud();
      await window.Clerk.signOut();
      return;
    }
    window.Clerk.openSignIn({
      fallbackRedirectUrl: window.location.href,
      signUpFallbackRedirectUrl: window.location.href,
    });
  });

  document.addEventListener("panini:progress-changed", scheduleSave);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "hidden" || !saveTimer) return;
    window.clearTimeout(saveTimer);
    saveTimer = null;
    saveToCloud();
  });
  initialize();
})();
