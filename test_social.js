const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const appSource = readFileSync(path.join(__dirname, "album", "app.js"), "utf8");
const socialSource = readFileSync(path.join(__dirname, "album", "social.js"), "utf8");
const cloudSyncSource = readFileSync(path.join(__dirname, "album", "cloud-sync.js"), "utf8");

function eventNode(properties = {}) {
  const listeners = new Map();
  const classes = new Set();
  return {
    innerHTML: "",
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(callback);
    },
    async emit(type, event = {}) {
      for (const callback of listeners.get(type) || []) await callback(event);
    },
    dispatchEvent(event) {
      for (const callback of listeners.get(event.type) || []) callback(event);
      return true;
    },
    querySelectorAll: () => [],
    focus() { this.focused = true; },
    select() { this.selected = true; },
    replaceChildren() { this.innerHTML = ""; },
    classList: {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
      toggle(name, active) {
        if (active) classes.add(name);
        else classes.delete(name);
      },
    },
    open: false,
    showModal() { this.open = true; },
    close() {
      this.open = false;
      this.dispatchEvent({ type: "close" });
    },
    ...properties,
  };
}

function fixture(options = {}) {
  const nodes = new Map();
  const storage = new Map();
  const document = eventNode({
    createElement() {
      return {
        textContent: "",
        get innerHTML() {
          return this.textContent.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;").replace(/>/g, "&gt;");
        },
      };
    },
    querySelector(selector) {
      if (!nodes.has(selector)) {
        nodes.set(selector, eventNode({
          querySelector: (child) => document.querySelector(child),
        }));
      }
      return nodes.get(selector);
    },
  });
  const window = {
    ALBUM_DATA: options.data || ["normal", "manual", "automatic", "override", "owned", "single", "offer"]
      .map((id) => ({
        id,
        seccion: "Team",
        numero: id,
        nombre: id,
        estado_laliga: ["automatic", "override"].includes(id)
          ? "fuera_plantilla"
          : "en_plantilla",
      })),
    location: { search: "", origin: "https://example.test", pathname: "/" },
    addEventListener() {},
    scrollTo() {},
  };
  const context = vm.createContext({
    window,
    document,
    console: options.console || console,
    URLSearchParams,
    structuredClone,
    Worker: options.Worker,
    navigator: options.navigator || {},
    CustomEvent: class {
      constructor(type, { detail } = {}) {
        this.type = type;
        this.detail = detail;
      }
    },
    localStorage: {
      getItem: (key) => storage.get(key) || null,
      setItem: (key, value) => storage.set(key, value),
    },
  });
  // Run the real modules, stubbing only DOM rendering and exposing closure state.
  vm.runInContext(appSource.replace(
    /\n  initializeSections\(\);[\s\S]*$/,
    "\n  render = () => {};\n  window.testState = state;\n  window.testAlbumFunctions = {matchesFilter, matchesSearch, editionBadge, photoTag, placeholderSticker, stickerCard};\n})();",
  ), context);
  vm.runInContext(socialSource.replace(
    /\n  document\.addEventListener\("panini:cloud-ready", initialize\);/,
    `\n  window.testComparisons = comparisons;
  window.testRenderComparison = renderComparison;
  window.testRenderFriends = (items) => {
    user = { id: "me" };
    friends = items;
    renderFriendsPanel(document.querySelector("#friends-panel"));
  };
  window.testRenderFriendsModal = async (items) => {
    profile = { inviteToken: "invite" };
    client = { rpc: async () => ({ data: items, error: null }) };
    await renderFriends();
  };
  window.testPool = {
    inventory: poolInventory,
    configure(items, rpc) {
      user = { id: "me", fullName: "Me" };
      friends = items;
      client = { rpc: rpc || (async () => ({ data: items, error: null })) };
      activeTab = "pool";
    },
    render: renderPool,
    calculate: calculatePool,
    initialize,
    plan: () => poolPlan,
    job: () => poolJob,
    text: poolPlanText,
  };
  window.testShare = {
    configure(rpc) {
      user = { id: "me", fullName: "Private account name" };
      client = { rpc: rpc || (async () => ({ data: [], error: null })) };
      activeTab = "share";
    },
    text: collectionListText,
    render: renderShare,
    update: updateShareList,
  };`,
  ), context);
  const album = window.PaniniAlbum;
  album.replaceProgress({
    manual: { state: "missing", copies: 0, stickDecision: "dont-stick" },
    override: { state: "missing", copies: 0, stickDecision: "stick" },
    owned: { state: "owned", copies: 1 },
    offer: { state: "owned", copies: 2, stickDecision: "dont-stick" },
  });
  const friend = {
    user_id: "friend",
    display_name: "Friend",
    progress: Object.fromEntries(
      ["normal", "manual", "automatic", "override", "owned", "single"]
        .map((id) => [id, { state: "owned", copies: id === "single" ? 1 : 2 }]),
    ),
  };
  return { window, album, friend, nodes, document, storage };
}

test("excludes manual No pegar, owned stickers and non-duplicates without changing offers", () => {
  const { window, friend } = fixture();
  const result = window.testComparisons(friend);
  assert.deepEqual(Array.from(result.friendCanGive), ["normal", "automatic", "override"]);
  assert.deepEqual(Array.from(result.iCanGive), ["offer"]);
});

test("fourth edition filters, searches and badges use the same edition without changing progress", () => {
  const { window, album } = fixture();
  const sticker = {
    id: "fourth", numero: "14BIS", nombre: "Casadó", edicion: "4ed",
    seccion: "DEPORTIVO", accion: "PEGAR",
  };
  const before = album.getProgress();
  window.testState.filter = "fourth-edition";
  assert.equal(window.testAlbumFunctions.matchesFilter(sticker), true);
  assert.equal(window.testAlbumFunctions.matchesFilter({ ...sticker, edicion: "3ed" }), false);
  for (const query of ["4ed", "4ª edición", "cuarta edición"]) {
    window.testState.query = query;
    assert.equal(window.testAlbumFunctions.matchesSearch(sticker), true, query);
  }
  assert.match(window.testAlbumFunctions.editionBadge(sticker), /data-edition="4ed"/);
  assert.match(window.testAlbumFunctions.editionBadge(sticker), /4ª ed/);
  assert.deepEqual(album.getProgress(), before);
});

test("LALIGA portraits retain the zoom while moving upward and keeping the same lower edge", () => {
  const { window } = fixture();
  const sticker = {
    id: "portrait", seccion: "REAL BETIS", numero: "9BIS", nombre: "Junior",
    tipo: "defensa", foto_fuente: "laliga", foto_url: "https://example.test/portrait.png",
  };
  const image = window.testAlbumFunctions.photoTag(sticker, "portrait");
  const attributes = Object.fromEntries(
    [...image.matchAll(/\b(x|y|width|height)="([^"]+)"/g)]
      .map((match) => [match[1], Number(match[2])]),
  );
  assert.ok(Math.abs(attributes.width / (172 * 1.22) - 2) < 1e-10);
  assert.ok(Math.abs(attributes.height / (204 * 1.22) - 2) < 1e-10);
  assert.equal(attributes.y, 8);
  assert.ok(Math.abs(attributes.x + attributes.width / 2 - 138) < 1e-10);
  assert.match(image, /^<g clip-path="url\(#photo-portrait\)"><image /);
  assert.match(image, /preserveAspectRatio="xMidYMin slice"/);
  const card = window.testAlbumFunctions.placeholderSticker(sticker);
  assert.match(card, /viewBox="0 0 232 308"/);
  assert.match(card, /<clipPath id="photo-portrait">\s*<rect x="52" y="8" width="172" height="262"/);
});

test("Transfermarkt portraits retain their original size and bottom anchoring", () => {
  const { window } = fixture();
  const image = window.testAlbumFunctions.photoTag({
    foto_fuente: "transfermarkt", foto_url: "https://example.test/portrait.jpg",
  }, "portrait");
  assert.match(image, /x="52" y="66" width="172" height="204"/);
  assert.match(image, /preserveAspectRatio="xMidYMax meet"/);
});

test("silhouettes retain their previous clipping and do not move into the upper portrait area", () => {
  const { window } = fixture();
  const card = window.testAlbumFunctions.placeholderSticker({
    id: "silhouette", seccion: "REAL BETIS", numero: "9BIS",
    nombre: "Junior", tipo: "defensa", foto_url: "", foto_fuente: "",
  });
  assert.match(card, /<clipPath id="photo-silhouette">\s*<rect x="52" y="66" width="172" height="204"/);
  assert.match(card, /<circle cx="138" cy="146" r="34"/);
});

test("generated special cards show their actual club crest without replacing their section or number", () => {
  const { window } = fixture();
  const sticker = {
    id: "rodri-top", seccion: "TOP FICHAJES", numero: "67",
    nombre: "Rodri", tipo: "medio", club_objetivo: "FC Barcelona",
    escudo_url: "https://example.test/barcelona.png", foto_url: "",
    imagen_provisional: "true", accion: "PEGAR", edicion: "4ed",
  };
  const card = window.testAlbumFunctions.placeholderSticker(sticker);
  assert.match(card, /href="https:\/\/example\.test\/barcelona\.png" x="8" y="7" width="56" height="56"/);
  assert.match(card, /<title>Escudo de FC Barcelona<\/title>/);
  assert.match(card, /aria-label="Cromo provisional de TOP FICHAJES\. Equipo: FC Barcelona"/);
  assert.match(card, />67<\/text>/);
  assert.doesNotMatch(card, />TOP<\/text>/);
  const fullCard = window.testAlbumFunctions.stickerCard(sticker);
  assert.match(fullCard, /role="img" aria-label="Imagen provisional de TOP FICHAJES\. Equipo: FC Barcelona"/);
});

test("club crest descriptions are escaped and unknown clubs retain the section fallback", () => {
  const { window } = fixture();
  const sticker = {
    id: "unknown", seccion: "ÚLTIMOS FICHAJES", numero: "UF1",
    nombre: "Jugador", club_objetivo: 'Club <script>"test"</script>',
    escudo_url: "https://example.test/crest.png", foto_url: "",
  };
  const card = window.testAlbumFunctions.placeholderSticker(sticker);
  assert.doesNotMatch(card, /<script>/);
  assert.match(card, /Club &lt;script&gt;&quot;test&quot;&lt;\/script&gt;/);
  window.ALBUM_PLACEHOLDERS = {
    "ÚLTIMOS FICHAJES": { code: "UF", primary: "#147a52", secondary: "#dff3e9", accent: "#0d5639" },
  };
  const fallback = window.testAlbumFunctions.placeholderSticker({
    ...sticker, club_objetivo: "", escudo_url: "",
  });
  assert.match(fallback, />UF<\/text>/);
  assert.doesNotMatch(fallback, /<title>Escudo/);
});

test("Figuritas cannot overwrite two different stickers that share a BIS number", () => {
  const { album } = fixture({ data: [
    { id: "old", seccion: "DEPORTIVO", numero: "14BIS", nombre: "Gijselhart" },
    { id: "new", seccion: "DEPORTIVO", numero: "14BIS", nombre: "Casadó" },
    { id: "normal", seccion: "DEPORTIVO", numero: "15", nombre: "Jugador" },
  ] });
  album.replaceProgress({
    old: { copies: 3, state: "owned", stickDecision: "dont-stick" },
    new: { copies: 1, state: "owned", stickDecision: "stick" },
  });
  const before = album.getProgress();
  const parsed = album.parseFiguritasList(
    "Figuritas App - Lista\nLaLiga 26/27\nMe faltan\nDeportivo: 14BIS\nRepetidas\nDeportivo: 15",
  );
  assert.equal(parsed.progress.old, undefined);
  assert.equal(parsed.progress.new, undefined);
  assert.equal(parsed.progress.normal.copies, 2);
  assert.ok(parsed.unmatched.includes("DEPORTIVO:14BIS (número compartido; sin modificar)"));
  assert.deepEqual(album.getProgress(), before);
});
test("excludes private suggestions but respects an explicit Pegar decision", () => {
  const { window, friend } = fixture();
  window.testState.privateStrategy = true;
  const result = window.testComparisons(friend);
  assert.deepEqual(Array.from(result.friendCanGive), ["normal", "override"]);
  assert.deepEqual(Array.from(result.iCanGive), ["offer"]);
});

test("uses own decisions and suggestions while previewing a friend's album", () => {
  const { window, album, friend } = fixture();
  window.testState.privateStrategy = true;
  album.previewFriend("Friend", {
    normal: { state: "missing", copies: 0, stickDecision: "dont-stick" },
    manual: { state: "owned", copies: 2, stickDecision: "stick" },
  });
  assert.deepEqual(
    Array.from(window.testComparisons(friend).friendCanGive),
    ["normal", "override"],
  );
});

test("does not enable private suggestions in a read-only album", () => {
  const { window, album } = fixture();
  window.testState.privateStrategy = true;
  window.testState.readOnly = true;
  assert.deepEqual(Array.from(album.getUnwantedStickerIds()), ["manual", "offer"]);
});

test("changing a decision restores the sticker to trade candidates", () => {
  const { window, album, friend } = fixture();
  const progress = album.getProgress();
  progress.manual.stickDecision = "stick";
  album.replaceProgress(progress);
  assert.ok(window.testComparisons(friend).friendCanGive.includes("manual"));
});

test("keeps No pegar decisions out of shared progress", () => {
  const { album } = fixture();
  const shared = album.getSocialProgress();
  assert.deepEqual(Object.keys(shared), ["owned", "offer"]);
  assert.deepEqual(Object.keys(shared.offer), ["state", "copies"]);
  assert.equal(shared.offer.copies, 2);
});

test("auth-required mode shows only the catalog without deleting saved progress", () => {
  const { album } = fixture();
  const before = album.getProgress();
  album.setAuthRequired(true);
  assert.equal(album.isAuthRequired(), true);
  assert.equal(Object.keys(album.getSocialProgress()).length, 0);
  album.setAuthRequired(false);
  assert.equal(album.isAuthRequired(), false);
  assert.deepEqual(album.getProgress(), before);
});

test("comparison options and all friend counters use the filtered result", async () => {
  const { window, friend, nodes } = fixture();
  window.testState.privateStrategy = true;
  window.testRenderComparison(friend);
  const comparison = nodes.get("#social-content").innerHTML;
  assert.match(comparison, /Te puede dar <span>2<\/span>/);
  assert.match(comparison, /Puedes ofrecer <span>1<\/span>/);
  assert.match(comparison, /data-trade-item="normal" data-side="requested"/);
  assert.match(comparison, /data-trade-item="override" data-side="requested"/);
  assert.doesNotMatch(comparison, /data-trade-item="(?:manual|automatic)"/);
  assert.match(comparison, /data-trade-item="offer" data-side="offered"/);
  window.testRenderFriends([friend]);
  assert.match(
    nodes.get("#friends-panel").innerHTML,
    /friend-tally tally-owned">2<\/span> te puede dar/,
  );
  await window.testRenderFriendsModal([friend]);
  assert.match(nodes.get("#social-content").innerHTML, /2 para ti · 1 para ofrecer/);
});

test("published scripts keep the versions from the generation template", () => {
  const html = readFileSync(path.join(__dirname, "album", "index.html"), "utf8");
  const template = readFileSync(path.join(__dirname, "generar_album.py"), "utf8");
  for (const script of ["app", "social", "cloud-sync"]) {
    const pattern = new RegExp(`src="${script}\\.js\\?v=\\d+"`);
    assert.equal(html.match(pattern)?.[0], template.match(pattern)?.[0]);
    assert.ok(html.match(pattern));
  }
});

test("invite dialog exposes login and signup actions and closes before auth", () => {
  assert.match(socialSource, /data-social-login/);
  assert.match(socialSource, /data-social-signup/);
  assert.match(socialSource, /dialog\.close\(\);\s*window\.PaniniCloud\.signIn\(\);/);
  assert.match(socialSource, /dialog\.close\(\);\s*window\.PaniniCloud\.signUp\?\.\(\);/);
});

test("cloud sync exposes signUp with Clerk fallback", () => {
  assert.match(cloudSyncSource, /signUp:\s*\(\)\s*=>/);
  assert.match(cloudSyncSource, /window\.Clerk\.openSignUp/);
  assert.match(cloudSyncSource, /window\.Clerk\.openSignIn/);
});

test("WhatsApp missing list uses own preferences and never includes private account data", () => {
  const { window } = fixture();
  window.testShare.configure();
  window.testState.privateStrategy = true;
  const missing = window.testShare.text("missing");
  assert.equal(
    missing,
    "*Mi álbum LALIGA 2026-27*\n\n*ME FALTAN: 3 cromos*\n\n*Team*\nnormal, override, single",
  );
  assert.doesNotMatch(missing, /manual|automatic|owned|offer|Private account|stickDecision|user_id|https?:/);
  assert.throws(() => window.testShare.text("invalid"), /Elige faltantes/);
});

test("WhatsApp duplicates report spare copies, including those marked No pegar", () => {
  const { window, album } = fixture();
  window.testShare.configure();
  const progress = album.getProgress();
  progress.offer.copies = 4;
  album.replaceProgress(progress);
  const text = window.testShare.text("duplicates");
  assert.match(text, /\*REPETIDOS: 1 cromo, 3 copias disponibles\*/);
  assert.match(text, /offer \(×3\)/);
  assert.doesNotMatch(text, /ME FALTAN|owned/);
  const both = window.testShare.text("both");
  assert.match(both, /ME FALTAN/);
  assert.match(both, /REPETIDOS/);
});

test("WhatsApp text distinguishes duplicate BIS identities and names Extra Stickers", () => {
  const { window, album } = fixture({ data: [
    { id: "old", seccion: "DEPORTIVO", numero: "14BIS", nombre: "Gijselhart", edicion: "3ed" },
    { id: "new", seccion: "DEPORTIVO", numero: "14BIS", nombre: "Casadó", edicion: "4ed" },
    { id: "extra", seccion: "EXTRA STICKER ORO", numero: "Extra Sticker", nombre: "Rodri" },
    { id: "pending", seccion: "TOP FICHAJES", numero: "70", nombre: "", accion: "ESPERAR" },
  ] });
  window.testShare.configure();
  album.replaceProgress({});
  const text = window.testShare.text("missing");
  assert.match(text, /ME FALTAN: 3 cromos/);
  assert.match(text, /14BIS Gijselhart \(3ª ed\), 14BIS Casadó \(4ª ed\)/);
  assert.match(text, /\*EXTRA STICKER ORO\*\nRodri/);
  assert.doesNotMatch(text, /TOP FICHAJES|pending|Extra Sticker/);
});

test("WhatsApp text comes from the owner's album even while previewing a friend", () => {
  const { window, album } = fixture();
  window.testShare.configure();
  const before = window.testShare.text("both");
  album.previewFriend("Friend", { normal: { state: "owned", copies: 20 } });
  assert.equal(window.testShare.text("both"), before);
});

test("WhatsApp copying does not mutate progress and refreshes the selected preview", async () => {
  const copied = [];
  const state = fixture({ navigator: { clipboard: { writeText: async (text) => copied.push(text) } } });
  state.window.testShare.configure();
  await state.window.testShare.render();
  const before = new Map(state.storage);
  const dialog = state.nodes.get("#social-dialog");
  await dialog.emit("change", {
    target: targetFor("#share-list-kind", { value: "both" }),
  });
  await dialog.emit("click", { target: targetFor("[data-copy-collection-list]") });
  assert.equal(copied.length, 1);
  assert.equal(copied[0], state.window.testShare.text("both"));
  assert.equal(state.nodes.get("#share-list-text").value, copied[0]);
  assert.match(state.nodes.get("#social-notice").textContent, /Lista copiada/);
  assert.deepEqual(state.storage, before);
  dialog.showModal();
  state.album.replaceProgress({ normal: { state: "owned", copies: 5 } }, { notify: true });
  assert.match(state.nodes.get("#share-list-text").value, /normal \(×4\)/);
});

test("WhatsApp native sharing sends only complete text, not an album link", async () => {
  const shared = [];
  const state = fixture({ navigator: { share: async (payload) => shared.push(payload) } });
  state.window.testShare.configure();
  await state.window.testShare.render();
  assert.equal(state.nodes.get("[data-share-list-native]").classList.contains("hidden"), false);
  await state.nodes.get("#social-dialog").emit("click", {
    target: targetFor("[data-share-list-native]"),
  });
  assert.equal(shared.length, 1);
  assert.deepEqual(Object.keys(shared[0]), ["text"]);
  assert.equal(shared[0].text, state.window.testShare.text("missing"));
});

test("copy failures keep the complete text selectable and report the error", async () => {
  const errors = [];
  const state = fixture({
    navigator: { clipboard: { writeText: async () => { throw new Error("Permission denied"); } } },
    console: { ...console, error: (...args) => errors.push(args) },
  });
  state.window.testShare.configure();
  await state.window.testShare.render();
  await state.nodes.get("#social-dialog").emit("click", {
    target: targetFor("[data-copy-collection-list]"),
  });
  assert.equal(errors.length, 1);
  assert.equal(state.nodes.get("#share-list-text").selected, true);
  assert.equal(state.nodes.get("#social-notice").classList.contains("error"), true);
  assert.match(state.nodes.get("#social-notice").textContent, /texto seleccionado/);
});

test("unsupported clipboard and cancelled sharing never claim a successful copy", async () => {
  const state = fixture({ navigator: {
    share: async () => { const error = new Error("Cancelled"); error.name = "AbortError"; throw error; },
  } });
  state.window.testShare.configure();
  await state.window.testShare.render();
  await state.nodes.get("#social-dialog").emit("click", {
    target: targetFor("[data-share-list-native]"),
  });
  assert.equal(state.nodes.get("#social-notice")?.textContent, undefined);
  await state.nodes.get("#social-dialog").emit("click", {
    target: targetFor("[data-copy-collection-list]"),
  });
  assert.match(state.nodes.get("#social-notice").textContent, /no permite copiar/);
  assert.equal(state.nodes.get("#share-list-text").selected, true);
});

test("public link failures do not block WhatsApp text from the local album", async () => {
  const errors = [];
  const state = fixture({ console: { ...console, error: (...args) => errors.push(args) } });
  state.window.testShare.configure(async () => ({ data: null, error: new Error("Offline") }));
  await state.window.testShare.render();
  assert.equal(state.nodes.get("#share-list-text").value, state.window.testShare.text("missing"));
  assert.match(state.nodes.get("#share-links").innerHTML, /siguen disponibles/);
  assert.equal(errors.length, 1);
});

test("signed-out and public albums cannot export another person's private lists", () => {
  const state = fixture();
  state.window.testShare.configure();
  state.album.setAuthRequired(true);
  assert.throws(() => state.window.testShare.text("both"), /Inicia sesión/);
  state.album.setAuthRequired(false);
  state.window.testState.readOnly = true;
  assert.throws(() => state.window.testShare.text("both"), /Inicia sesión/);
});

test("session changes clear private share content and stale link responses cannot restore it", async () => {
  let resolveLinks;
  const state = fixture();
  state.window.testShare.configure(() => new Promise((resolve) => { resolveLinks = resolve; }));
  const pending = state.window.testShare.render();
  const dialog = state.nodes.get("#social-dialog");
  dialog.showModal();
  await state.window.testPool.initialize({ detail: { user: null, client: {} } });
  assert.equal(dialog.open, false);
  assert.equal(state.nodes.get("#social-content").innerHTML, "");
  resolveLinks({ data: [{ id: "private-old-share", created_at: "2026-10-29" }], error: null });
  await pending;
  assert.doesNotMatch(state.nodes.get("#share-links")?.innerHTML || "", /private-old-share/);
});

test("full-size WhatsApp lists are not truncated and completed albums have explicit empty messages", () => {
  const html = readFileSync(path.join(__dirname, "album", "index.html"), "utf8");
  const data = JSON.parse(html.match(/window\.ALBUM_DATA = (.*?);<\/script>/)[1]);
  const { window, album } = fixture({ data });
  window.testShare.configure();
  album.replaceProgress({});
  const missing = window.testShare.text("missing");
  assert.match(missing, /ME FALTAN: 661 cromos/);
  assert.match(missing, /14BIS Burcio \(4ª ed\)/);
  assert.match(missing, /\*EXTRA STICKER ORO\*/);
  assert.match(missing, /Bellingham/);
  album.replaceProgress(Object.fromEntries(data.map((sticker) => [sticker.id, { state: "owned", copies: 1 }])));
  assert.match(window.testShare.text("missing"), /No me falta ningún cromo/);
  assert.match(window.testShare.text("duplicates"), /No tengo cromos repetidos/);
});

function targetFor(selector, properties = {}) {
  const target = { ...properties };
  target.closest = (match) => match === selector ? target : null;
  return target;
}

function workerFixture() {
  const instances = [];
  const errors = [];
  class TestWorker {
    constructor(url) {
      this.url = url;
      this.events = new Map();
      this.terminated = false;
      instances.push(this);
    }
    addEventListener(type, listener) {
      this.events.set(type, listener);
    }
    postMessage(message) {
      this.message = structuredClone(message);
    }
    terminate() {
      this.terminated = true;
    }
    finish(result) {
      this.events.get("message")({ data: { result } });
    }
    fail(message) {
      this.events.get("message")({ data: { error: message } });
    }
  }
  const state = fixture({
    Worker: TestWorker,
    console: { ...console, error: (...args) => errors.push(args) },
  });
  state.window.testPool.configure([state.friend]);
  const dialog = state.nodes.get("#social-dialog");
  dialog.showModal();
  return { ...state, dialog, workers: instances, errors };
}

async function selectPoolMember(state, id, checked = true) {
  await state.nodes.get("#social-dialog").emit("change", {
    target: targetFor("[data-pool-member]", {
      dataset: { poolMember: id }, checked, disabled: false,
    }),
  });
}

function samplePlan() {
  return {
    totalTransfers: 2,
    transfers: [
      { from: "me", to: "friend", stickerId: "offer", quantity: 1 },
      { from: "friend", to: "me", stickerId: "normal", quantity: 1 },
    ],
    participants: [
      { id: "me", available: 1, given: 1, received: 1, balance: 0 },
      { id: "friend", available: 5, given: 1, received: 1, balance: 0 },
    ],
  };
}

const nextTurn = () => new Promise((resolve) => setImmediate(resolve));

test("pool inventories retain one copy and ignore unknown IDs without leaking decisions", () => {
  const { window, album } = fixture();
  window.testState.privateStrategy = true;
  const inventory = window.testPool.inventory(
    "me",
    { ...album.getSocialProgress(), unknown: { state: "owned", copies: 99 } },
    album.getUnwantedStickerIds(),
  );
  assert.deepEqual(Object.entries(inventory.offered), [["offer", 1]]);
  assert.deepEqual(Array.from(inventory.missing), ["normal", "override", "single"]);
  assert.equal(inventory.ownedCount, 2);
  assert.doesNotMatch(JSON.stringify(inventory), /stickDecision|unknown/);
  assert.throws(
    () => window.testPool.inventory("bad", { normal: { copies: -1 } }),
    /copias no válido/,
  );
});

test("pool setup includes the organizer and safely escapes participant names", async () => {
  const state = fixture();
  state.friend.display_name = '<script>alert("name")</script>';
  state.window.testPool.configure([state.friend]);
  await state.window.testPool.render();
  const html = state.nodes.get("#social-content").innerHTML;
  assert.match(html, /data-social-tab="pool">Grupal/);
  assert.match(html, /data-pool-member="me"\s+checked disabled/);
  assert.match(html, /data-calculate-pool disabled/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>alert/);
  assert.match(html, /Solo cuenta lo que se entrega/);
});

test("calculating refreshes friends, filters only own No pegar and never writes inventories", async () => {
  const state = workerFixture();
  let reads = 0;
  state.window.testState.privateStrategy = true;
  state.window.testPool.configure([state.friend], async (method) => {
    assert.equal(method, "get_album_friends");
    reads += 1;
    const updated = structuredClone(state.friend);
    updated.progress.normal.copies = reads === 1 ? 2 : 4;
    updated.progress.normal.stickDecision = "dont-stick";
    return { data: [updated], error: null };
  });
  const before = new Map(state.storage);
  await state.window.testPool.render();
  await selectPoolMember(state, "friend");
  const calculating = state.window.testPool.calculate();
  await nextTurn();
  assert.equal(reads, 2);
  assert.equal(state.workers.length, 1);
  const worker = state.workers[0];
  assert.equal(worker.url, "pool-worker.js?v=1");
  const [mine, friend] = worker.message.participants;
  assert.deepEqual(mine.offered, { offer: 1 });
  assert.deepEqual(mine.missing, ["normal", "override", "single"]);
  assert.equal(friend.offered.normal, 3);
  assert.deepEqual(friend.missing, ["offer"]);
  assert.equal(state.window.testPool.plan(), null);
  const result = samplePlan();
  result.participants[1].available = 7;
  worker.finish(result);
  await calculating;
  assert.equal(worker.terminated, true);
  assert.deepEqual(state.storage, before);
  const html = state.nodes.get("#pool-results").innerHTML;
  assert.match(html, /2 cromos pueden cambiar de dueño/);
  assert.match(html, /Me → Friend/);
  assert.match(html, /Friend → Me/);
  assert.match(html, /Aporta/);
  const text = state.window.testPool.text(state.window.testPool.plan());
  assert.match(text, /Me: aporta 1, recibe 1, saldo 0/);
  assert.match(text, /Friend -> Me: Team · normal · normal/);
  assert.doesNotMatch(text, /stickDecision|user_id|invite_token/);
});

test("selection changes cancel in-flight jobs and invalidate previously completed plans", async () => {
  const state = workerFixture();
  await state.window.testPool.render();
  await selectPoolMember(state, "friend");
  const pending = state.window.testPool.calculate();
  await nextTurn();
  await selectPoolMember(state, "friend", false);
  await pending;
  assert.equal(state.workers[0].terminated, true);
  assert.equal(state.errors.length, 0);
  assert.equal(state.window.testPool.plan(), null);
  assert.equal(state.nodes.get("[data-calculate-pool]").disabled, true);
  await selectPoolMember(state, "friend");
  const completed = state.window.testPool.calculate();
  await nextTurn();
  state.workers[1].finish(samplePlan());
  await completed;
  state.document.dispatchEvent({ type: "panini:progress-changed" });
  assert.equal(state.window.testPool.plan(), null);
  assert.equal(state.nodes.get("#pool-results").innerHTML, "");
  assert.match(state.nodes.get("#pool-status").textContent, /Tu álbum ha cambiado/);
});

test("closing the dialog cancels work and ignores a late result", async () => {
  const state = workerFixture();
  await selectPoolMember(state, "friend");
  const pending = state.window.testPool.calculate();
  await nextTurn();
  state.dialog.close();
  state.workers[0].finish(samplePlan());
  await pending;
  assert.equal(state.workers[0].terminated, true);
  assert.equal(state.window.testPool.plan(), null);
  assert.equal(state.window.testPool.job(), null);
});

test("cancelling from the button re-enables calculation without inventing a result", async () => {
  const state = workerFixture();
  await selectPoolMember(state, "friend");
  const pending = state.window.testPool.calculate();
  await nextTurn();
  await state.dialog.emit("click", { target: targetFor("[data-cancel-pool]") });
  await pending;
  assert.equal(state.window.testPool.plan(), null);
  assert.equal(state.nodes.get("[data-calculate-pool]").disabled, false);
  assert.match(state.nodes.get("#pool-status").textContent, /cancelado/);
});

test("worker errors are reported and cannot produce a success-shaped plan", async () => {
  const state = workerFixture();
  await selectPoolMember(state, "friend");
  const pending = state.window.testPool.calculate();
  await nextTurn();
  state.workers[0].fail("Inventario inconsistente");
  await pending;
  assert.equal(state.errors.length, 1);
  assert.equal(state.window.testPool.plan(), null);
  assert.equal(state.nodes.get("#social-notice").textContent, "Inventario inconsistente");
  assert.match(state.nodes.get("#pool-status").textContent, /no se ha completado/);
  assert.equal(state.workers[0].terminated, true);
  assert.equal(state.nodes.get("#social-notice").classList.contains("visible"), true);
  const retry = state.window.testPool.calculate();
  await nextTurn();
  state.workers[1].finish(samplePlan());
  await retry;
  assert.equal(state.nodes.get("#social-notice").classList.contains("visible"), false);
  assert.equal(state.window.testPool.plan().result.totalTransfers, 2);
});

test("removed friends and signed-out accounts cannot start a pool worker", async () => {
  const state = workerFixture();
  state.window.testPool.configure([state.friend], async () => ({ data: [], error: null }));
  await selectPoolMember(state, "friend");
  await state.window.testPool.calculate();
  assert.equal(state.workers.length, 0);
  assert.match(state.nodes.get("#social-notice").textContent, /lista de amigos ha cambiado/);
  state.album.setAuthRequired(true);
  state.window.testPool.configure([state.friend]);
  await state.window.testPool.calculate();
  assert.equal(state.workers.length, 0);
  assert.match(state.nodes.get("#social-notice").textContent, /Inicia sesión/);
});

test("switching tabs and signing out cancel the group job without retaining the result", async () => {
  const state = workerFixture();
  state.window.testPool.configure([state.friend], async (method) => ({
    data: method === "get_album_friends" ? [state.friend] : [],
    error: null,
  }));
  await selectPoolMember(state, "friend");
  const pending = state.window.testPool.calculate();
  await nextTurn();
  await state.dialog.emit("click", {
    target: targetFor("[data-social-tab]", { dataset: { socialTab: "share" } }),
  });
  await pending;
  assert.equal(state.workers[0].terminated, true);
  assert.equal(state.window.testPool.plan(), null);
  state.window.testPool.configure([state.friend]);
  const next = state.window.testPool.calculate();
  await nextTurn();
  await state.window.testPool.initialize({ detail: { user: null, client: {} } });
  await next;
  assert.equal(state.workers[1].terminated, true);
  assert.equal(state.window.testPool.plan(), null);
});

test("inventory fetch errors and missing Worker support are explicitly reported", async () => {
  const state = workerFixture();
  state.window.testPool.configure([state.friend], async () => ({
    data: null, error: new Error("Network error"),
  }));
  await selectPoolMember(state, "friend");
  await state.window.testPool.calculate();
  assert.equal(state.workers.length, 0);
  assert.equal(state.window.testPool.plan(), null);
  assert.equal(state.nodes.get("[data-calculate-pool]").disabled, false);
  assert.equal(state.errors.length, 1);

  const unsupported = fixture({ console: { ...console, error() {} } });
  unsupported.window.testPool.configure([unsupported.friend]);
  await selectPoolMember(unsupported, "friend");
  await unsupported.window.testPool.calculate();
  assert.equal(unsupported.window.testPool.plan(), null);
  assert.match(unsupported.nodes.get("#social-notice").textContent, /navegador actualizado/);
});

test("the real Worker imports the deployed optimizer and returns results or explicit errors", () => {
  const workerSource = readFileSync(path.join(__dirname, "album", "pool-worker.js"), "utf8");
  const messages = [];
  const errors = [];
  let handler;
  const context = vm.createContext({
    console: { error: (...args) => errors.push(args) },
    addEventListener(type, callback) {
      assert.equal(type, "message");
      handler = callback;
    },
    postMessage: (message) => messages.push(structuredClone(message)),
    importScripts(script) {
      assert.equal(script, "pool-optimizer.js?v=1");
      const source = readFileSync(path.join(__dirname, "album", "pool-optimizer.js"), "utf8");
      vm.runInContext(source, context);
    },
  });
  context.self = context;
  vm.runInContext(workerSource, context);
  handler({ data: { participants: [
    { id: "a", offered: { red: 1 }, missing: ["blue"], ownedCount: 1 },
    { id: "b", offered: { blue: 1 }, missing: ["red"], ownedCount: 1 },
  ] } });
  assert.equal(messages[0].result.totalTransfers, 2);
  assert.equal(errors.length, 0);
  handler({ data: { participants: [] } });
  assert.equal(typeof messages[1].error, "string");
  assert.equal(messages[1].result, undefined);
  assert.equal(errors.length, 1);
});
