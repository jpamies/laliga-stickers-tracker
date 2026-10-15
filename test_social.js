const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const appSource = readFileSync(path.join(__dirname, "album", "app.js"), "utf8");
const socialSource = readFileSync(path.join(__dirname, "album", "social.js"), "utf8");
const cloudSyncSource = readFileSync(path.join(__dirname, "album", "cloud-sync.js"), "utf8");

function fixture() {
  const nodes = new Map();
  const storage = new Map();
  const document = {
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
        nodes.set(selector, {
          innerHTML: "",
          addEventListener() {},
          querySelectorAll: () => [],
          classList: { add() {}, remove() {}, toggle() {} },
        });
      }
      return nodes.get(selector);
    },
    querySelectorAll: () => [],
    addEventListener() {},
  };
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
    console,
    URLSearchParams,
    structuredClone,
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
  return { window, album, friend, nodes };
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
  for (const script of ["app", "social"]) {
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
