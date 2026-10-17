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
    ALBUM_DATA: ["normal", "manual", "automatic", "override", "owned", "single", "offer"]
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
    "\n  render = () => {};\n  window.testState = state;\n})();",
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
