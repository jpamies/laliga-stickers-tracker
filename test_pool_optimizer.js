const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { performance } = require("node:perf_hooks");
const test = require("node:test");
const vm = require("node:vm");
const api = require("./album/pool-optimizer.js");
const { optimize } = api;

const compareIds = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const person = (id, offered = {}, missing = [], ownedCount = 0) => ({
  id, offered, missing, ownedCount,
});

function verifyPlan(input, result) {
  const byId = new Map(input.map((participant) => [participant.id, participant]));
  const given = new Map(input.map(({ id }) => [id, new Map()]));
  const received = new Map(input.map(({ id }) => [id, new Set()]));
  assert.ok(Number.isSafeInteger(result.totalTransfers));
  assert.equal(result.totalTransfers, result.transfers.length);
  assert.deepEqual(
    result.participants.map(({ id }) => id),
    input.map(({ id }) => id).sort(compareIds),
  );
  assert.deepEqual(result.transfers, [...result.transfers].sort((a, b) => (
    compareIds(a.from, b.from) || compareIds(a.to, b.to) || compareIds(a.stickerId, b.stickerId)
  )));
  for (const transfer of result.transfers) {
    assert.deepEqual(Object.keys(transfer).sort(), ["from", "quantity", "stickerId", "to"]);
    const { from, to, stickerId, quantity } = transfer;
    assert.ok(byId.has(from));
    assert.ok(byId.has(to));
    assert.notEqual(from, to);
    assert.equal(quantity, 1);
    assert.ok(byId.get(to).missing.includes(stickerId));
    assert.ok(!received.get(to).has(stickerId), "at most one receipt of each missing id");
    received.get(to).add(stickerId);
    const donated = given.get(from);
    donated.set(stickerId, (donated.get(stickerId) || 0) + 1);
    assert.ok(donated.get(stickerId) <= byId.get(from).offered[stickerId]);
  }
  let totalGiven = 0;
  let totalReceived = 0;
  for (const participant of result.participants) {
    const expectedGiven = [...given.get(participant.id).values()].reduce((a, b) => a + b, 0);
    const expectedReceived = received.get(participant.id).size;
    assert.deepEqual(participant, {
      id: participant.id,
      available: Object.values(byId.get(participant.id).offered).reduce((a, b) => a + b, 0),
      given: expectedGiven,
      received: expectedReceived,
      balance: expectedGiven - expectedReceived,
    });
    assert.equal(participant.balance, 0, "actual gifts and receipts must balance for each user");
    totalGiven += participant.given;
    totalReceived += participant.received;
  }
  assert.equal(totalGiven, result.totalTransfers);
  assert.equal(totalReceived, result.totalTransfers);
  return result;
}

function solve(input) {
  return verifyPlan(input, optimize(input));
}

// Independent exhaustive oracle: enumerate no receipt / each possible donor
// for every (recipient, missing sticker) slot. No flow algorithm or optimizer
// priorities are reused here.
function bruteMaximum(input) {
  const remaining = input.map(({ offered }) => new Map(Object.entries(offered)));
  const slots = [];
  for (let recipient = 0; recipient < input.length; recipient++) {
    for (const stickerId of input[recipient].missing) {
      const donors = [];
      for (let donor = 0; donor < input.length; donor++) {
        if (donor !== recipient && (remaining[donor].get(stickerId) || 0) > 0) donors.push(donor);
      }
      if (donors.length > 0) slots.push({ recipient, stickerId, donors });
    }
  }
  const given = Array(input.length).fill(0);
  const received = Array(input.length).fill(0);
  let best = 0;
  function visit(index, count) {
    if (count + slots.length - index <= best) return;
    if (index === slots.length) {
      if (given.every((value, user) => value === received[user])) best = count;
      return;
    }
    const { recipient, stickerId, donors } = slots[index];
    for (const donor of donors) {
      const quantity = remaining[donor].get(stickerId);
      if (quantity === 0) continue;
      remaining[donor].set(stickerId, quantity - 1);
      given[donor]++;
      received[recipient]++;
      visit(index + 1, count + 1);
      received[recipient]--;
      given[donor]--;
      remaining[donor].set(stickerId, quantity);
    }
    visit(index + 1, count);
  }
  visit(0, 0);
  return best;
}

function random(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function deepFreeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

test("exports the same synchronous API in CommonJS, a browser and a windowless Worker", () => {
  assert.deepEqual(Object.keys(api), ["optimize"]);
  const source = readFileSync(path.join(__dirname, "album", "pool-optimizer.js"), "utf8");
  const input = [person("a", { x: 1 }, ["y"]), person("b", { y: 1 }, ["x"])];
  for (const globals of [{}, { window: {} }]) {
    const context = vm.createContext(globals);
    vm.runInContext(source, context);
    assert.equal(typeof context.PaniniPool.optimize, "function");
    const actual = JSON.parse(JSON.stringify(context.PaniniPool.optimize(input)));
    assert.deepEqual(actual, solve(input));
    assert.equal(typeof actual.then, "undefined");
  }
});

test("plans a two-way exchange and reports available surplus separately from gifts", () => {
  const result = solve([
    person("b", { blue: 1 }, ["red"]),
    person("a", { red: 4, unwanted: 7 }, ["blue", "unavailable"]),
  ]);
  assert.deepEqual(result, {
    totalTransfers: 2,
    transfers: [
      { from: "a", to: "b", stickerId: "red", quantity: 1 },
      { from: "b", to: "a", stickerId: "blue", quantity: 1 },
    ],
    participants: [
      { id: "a", available: 11, given: 1, received: 1, balance: 0 },
      { id: "b", available: 1, given: 1, received: 1, balance: 0 },
    ],
  });
});

test("finds three-way cycles with no reciprocal pair", () => {
  const result = solve([
    person("a", { x: 1 }, ["z"]),
    person("b", { y: 1 }, ["x"]),
    person("c", { z: 1 }, ["y"]),
  ]);
  assert.equal(result.totalTransfers, 3);
  assert.deepEqual(result.transfers, [
    { from: "a", to: "b", stickerId: "x", quantity: 1 },
    { from: "b", to: "c", stickerId: "y", quantity: 1 },
    { from: "c", to: "a", stickerId: "z", quantity: 1 },
  ]);
});

test("does not impose a small group or cycle-length cap", () => {
  const input = Array.from({ length: 37 }, (_, index) => person(
    `p-${String(index).padStart(2, "0")}`,
    { [`s-${index}`]: 1 },
    [`s-${(index + 36) % 37}`],
  ));
  assert.equal(solve(input).totalTransfers, 37);
});

test("returns no gifts for a directed chain, isolated users or unavailable requests", () => {
  for (const input of [
    [person("a", { x: 1 }), person("b", { y: 1 }, ["x"]), person("c", {}, ["y"])],
    [person("a", { x: 1 }, ["absent"]), person("b", { y: 2 }, ["other"])],
    [person("a"), person("b")],
  ]) {
    assert.equal(solve(input).totalTransfers, 0);
  }
});

test("unwanted and unassigned surplus cannot buy extra receipts", () => {
  const result = solve([
    person("a", { x: 1, unwanted: 100 }, ["y", "z"]),
    person("b", { y: 1 }, ["x"]),
    person("c", { z: 1 }, ["x"]),
  ]);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.participants[0].available, 101);
  assert.equal(result.participants[0].given, 1);
  assert.equal(result.participants[0].received, 1);
  assert.ok(result.transfers.every(({ stickerId }) => stickerId !== "unwanted"));
  assert.equal(solve([
    person("a", { unwanted: 100 }, ["x"]),
    person("b", { x: 1 }),
  ]).totalTransfers, 0);
});

test("sends multiple physical copies of one sticker to distinct recipients", () => {
  const result = solve([
    person("a", { x: 2 }, ["y", "z"]),
    person("b", { y: 1 }, ["x"]),
    person("c", { z: 1 }, ["x"]),
  ]);
  assert.equal(result.totalTransfers, 4);
  assert.deepEqual(
    result.transfers.filter(({ from }) => from === "a").map(({ to }) => to),
    ["b", "c"],
  );
});

test("a missing id is received at most once, even with several donors and many copies", () => {
  const result = solve([
    person("a", { x: 5 }, ["y"]),
    person("b", { x: 5 }, ["y"]),
    person("c", { y: 10 }, ["x"]),
  ]);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.participants.find(({ id }) => id === "c").received, 1);
});

test("reassigns a tempting reciprocal pair to unlock a maximum four-user cycle", () => {
  const result = solve([
    person("a", { x: 1 }, ["y", "w"]),
    person("b", { y: 1 }, ["x", "z"]),
    person("c", { z: 1 }, ["x"]),
    person("d", { w: 1 }, ["y"]),
  ]);
  assert.equal(result.totalTransfers, 4);
  assert.deepEqual(result.transfers.map(({ from, to }) => [from, to]), [
    ["a", "c"], ["b", "d"], ["c", "b"], ["d", "a"],
  ]);
});

test("degree-one priority never sacrifices cardinality for a tempting short cycle", () => {
  const input = [
    person("a", { x: 1 }, ["y", "w"]),
    person("b", { y: 1 }, ["x"]),
    person("c", { z: 1 }, ["x"]),
    person("d", { w: 1 }, ["z"]),
    person("f", { x: 1, z: 1, w: 1 }),
    person("g", {}, ["z", "w"]),
  ];
  // Only y has one eligible missing recipient, but using it allows only two transfers.
  const result = solve(input);
  assert.equal(result.totalTransfers, 3);
  assert.equal(result.totalTransfers, bruteMaximum(input));
  assert.ok(result.transfers.every(({ stickerId }) => stickerId !== "y"));
});

test("one eligible missing recipient gets degree-one priority even with multiple donors", () => {
  const result = solve([
    person("a", { x: 1 }, ["y", "z"]),
    person("b", { y: 1 }, ["x"], 1),
    person("c", { z: 1, unused: 100 }, ["x"], 618),
    person("f", { x: 1, y: 1, z: 1 }),
    person("g", {}, ["z"]),
  ]);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.transfers.find(({ stickerId }) => stickerId === "x").to, "b");
});

test("a unique donor does not earn degree-one priority when several recipients are missing it", () => {
  const input = [
    person("a", { x: 1 }, ["y", "z"]),
    person("b", { y: 1 }, ["x"], 1),
    person("c", { z: 1, unused: 100 }, ["x"], 618),
    person("f", { x: 1, z: 1 }),
    person("g", {}, ["y", "z"]),
  ];
  // y has one donor but two recipients, so surplus breaks the equal-cardinality tie.
  const result = solve(input);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.totalTransfers, bruteMaximum(input));
  assert.equal(result.transfers.find(({ stickerId }) => stickerId === "x").to, "c");
});

test("conflicts prefer useful outgoing capacity before surplus and album completion", () => {
  const result = solve([
    person("a", { x: 1 }, ["y", "z"]),
    person("b", { y: 1, unused: 100 }, ["x"], 618),
    person("c", { z: 2 }, ["x", "y"], 1),
    person("f", { y: 1 }, ["z"]),
    person("n", { z: 1 }),
  ]);
  assert.equal(result.totalTransfers, 4);
  assert.equal(result.transfers.find(({ stickerId }) => stickerId === "x").to, "c");
});

test("equal useful capacity prefers more total surplus, even if it is not transferable", () => {
  const result = solve([
    person("a", { x: 1 }, ["y", "z"]),
    person("b", { y: 1, unused: 10 }, ["x"], 1),
    person("c", { z: 1, other: 9 }, ["x"], 618),
  ]);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.transfers.find(({ stickerId }) => stickerId === "x").to, "b");
});

test("equal useful capacity and surplus prefer the more complete album", () => {
  const result = solve([
    person("a", { x: 1 }, ["y", "z"]),
    person("b", { y: 1 }, ["x"], 400),
    person("c", { z: 1 }, ["x"], 618),
  ]);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.transfers.find(({ stickerId }) => stickerId === "x").to, "c");
});

test("stable code-unit participant ids break otherwise equal recipient priorities", () => {
  const result = solve([
    person("root", { x: 1 }, ["y", "z"]),
    person("gamma", { z: 1 }, ["x"], 500),
    person("beta", { y: 1 }, ["x"], 500),
  ]);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.transfers.find(({ stickerId }) => stickerId === "x").to, "beta");
});

test("handles maximum safe quantities exactly without treating offered copies as credits", () => {
  const max = Number.MAX_SAFE_INTEGER;
  assert.equal(solve([
    person("a", { x: max }, ["y"], max),
    person("b", { y: max }, ["x"], max),
  ]).totalTransfers, 2);
  const result = solve([
    person("a", { x: 1, padding: max - 1 }, ["y", "z"], max),
    person("b", { y: 1, unused: max - 1 }, ["x"], max - 1),
    person("c", { z: 1, other: max - 2 }, ["x"], max),
  ]);
  assert.equal(result.totalTransfers, 2);
  assert.equal(result.transfers.find(({ stickerId }) => stickerId === "x").to, "b");
  assert.equal(result.participants[0].available, max);
});

test("canonicalizes participant, offered-key and missing-id ordering without mutation", () => {
  const input = deepFreeze([
    person("c", { z: 2, q: 1, unused: 5 }, ["y", "x", "absent"], 30),
    person("a", { x: 2, w: 1 }, ["q", "z", "y"], 20),
    person("b", { y: 2 }, ["w", "z", "x"], 10),
  ]);
  const before = JSON.stringify(input);
  const first = solve(input);
  const reordered = [...input].reverse().map((participant) => ({
    ...participant,
    offered: Object.fromEntries(Object.entries(participant.offered).reverse()),
    missing: [...participant.missing].reverse(),
  }));
  assert.deepEqual(solve(reordered), first);
  assert.deepEqual(solve(input), first);
  assert.equal(JSON.stringify(input), before);
  first.transfers[0].to = "changed";
  first.participants[0].available = -1;
  assert.equal(JSON.stringify(input), before);
  assert.deepEqual(solve(input), solve(reordered));
});

test("treats prototype-like ids as ordinary ids and permits zero offers for missing ids", () => {
  const input = [
    person("__proto__", Object.fromEntries([["constructor", 1], ["toString", 0]]), ["toString"]),
    person("constructor", Object.assign(Object.create(null), { toString: 1 }), ["constructor"]),
  ];
  assert.equal(solve(input).totalTransfers, 2);
});

test("rejects malformed participants and inconsistent inventory with useful errors", () => {
  const valid = () => person("a", { x: 1 }, ["y"], 10);
  const other = () => person("b", { y: 1 }, ["x"], 20);
  for (const input of [undefined, null, {}, "people", [], [valid()]]) {
    assert.throws(() => optimize(input), /participants.*array.*at least two/i);
  }
  for (const participant of [null, [], 1, "a"]) {
    assert.throws(() => optimize([participant, other()]), /participant.*object/i);
  }
  for (const id of ["", 1, null, undefined]) {
    assert.throws(() => optimize([{ ...valid(), id }, other()]), /id.*nonempty string/i);
  }
  assert.throws(() => optimize([valid(), valid()]), /duplicate participant id "a"/i);
  for (const offered of [null, undefined, [], new Map(), new Date(), () => {}]) {
    assert.throws(() => optimize([{ ...valid(), offered }, other()]), /"a".*offered.*object/i);
  }
  for (const missing of [null, undefined, {}, new Set()]) {
    assert.throws(() => optimize([{ ...valid(), missing }, other()]), /"a".*missing.*array/i);
  }
  for (const stickerId of ["", null, 1, undefined]) {
    assert.throws(
      () => optimize([{ ...valid(), missing: [stickerId] }, other()]),
      /"a".*missing sticker ids.*nonempty strings/i,
    );
  }
  assert.throws(
    () => optimize([{ ...valid(), missing: ["y", "y"] }, other()]),
    /"a".*duplicate missing sticker "y"/i,
  );
  assert.throws(
    () => optimize([{ ...valid(), offered: { "": 1 } }, other()]),
    /"a".*offered sticker ids.*nonempty strings/i,
  );
  assert.throws(
    () => optimize([{ ...valid(), offered: { [Symbol("x")]: 1 } }, other()]),
    /"a".*offered sticker ids.*nonempty strings/i,
  );
  for (const value of [-1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1, "1", null, undefined, 1n]) {
    assert.throws(
      () => optimize([{ ...valid(), ownedCount: value }, other()]),
      /"a".*ownedCount.*safe nonnegative integer/i,
    );
    assert.throws(
      () => optimize([{ ...valid(), offered: { x: value } }, other()]),
      /"a".*offered quantity.*"x".*safe nonnegative integer/i,
    );
  }
  assert.throws(
    () => optimize([{ ...valid(), missing: ["x"] }, other()]),
    /"a".*both offers and is missing sticker "x"/i,
  );
  assert.throws(
    () => optimize([{ ...valid(), offered: { x: Number.MAX_SAFE_INTEGER, z: 1 } }, other()]),
    /"a".*total offered quantity.*safe integer range/i,
  );
  assert.throws(() => optimize([, other()]), /participant.*object/i);
  assert.throws(
    () => optimize([{ ...valid(), missing: [,] }, other()]),
    /missing sticker ids.*nonempty strings/i,
  );
});

test("matches an independent oracle on every three-user, two-sticker small inventory", () => {
  // Each of six user/sticker cells is missing, owned without surplus, or offered.
  const count = 3 ** 6;
  for (let code = 0; code < count; code++) {
    let digits = code;
    const input = Array.from({ length: 3 }, (_, user) => {
      const participant = person(`p${user}`);
      for (const stickerId of ["x", "y"]) {
        const state = digits % 3;
        digits = Math.floor(digits / 3);
        if (state === 0) participant.missing.push(stickerId);
        else {
          participant.ownedCount++;
          if (state === 2) participant.offered[stickerId] = 1;
        }
      }
      return participant;
    });
    assert.equal(solve(input).totalTransfers, bruteMaximum(input), `inventory ${code}`);
  }
});

test("matches an independent oracle on 600 seeded pools with quantities and three-way cycles", () => {
  const next = random(0x5eed1234);
  let cycles = 0;
  for (let index = 0; index < 600; index++) {
    const userCount = 2 + Math.floor(next() * 3);
    const stickerCount = 1 + Math.floor(next() * 4);
    const input = Array.from({ length: userCount }, (_, user) => {
      const participant = person(`p${user}`, {}, [], Math.floor(next() * 619));
      for (let sticker = 0; sticker < stickerCount; sticker++) {
        const id = `s${sticker}`;
        const state = Math.floor(next() * 4);
        if (state === 0) participant.missing.push(id);
        else if (state >= 2) participant.offered[id] = 1 + Math.floor(next() * 3);
        else participant.offered[id] = 0;
      }
      return participant;
    });
    const result = solve(input);
    assert.equal(result.totalTransfers, bruteMaximum(input), `seeded pool ${index}`);
    if (result.totalTransfers % 2 === 1) cycles++;
    if (index % 10 === 0) {
      const reversed = [...input].reverse().map((participant) => ({
        ...participant,
        offered: Object.fromEntries(Object.entries(participant.offered).reverse()),
        missing: [...participant.missing].reverse(),
      }));
      assert.deepEqual(solve(reversed), result, `canonical seeded pool ${index}`);
    }
  }
  assert.ok(cycles > 0, "the seeded corpus includes non-reciprocal cycles");
});

test("optimizes a representative 618-sticker, 12-user pool and records duration", (t) => {
  const next = random(0x618c0ffe);
  const input = Array.from({ length: 12 }, (_, user) => person(`user-${user}`));
  for (let sticker = 0; sticker < 618; sticker++) {
    const id = `sticker-${String(sticker).padStart(3, "0")}`;
    for (const participant of input) {
      if (next() < 0.48) participant.missing.push(id);
      else {
        participant.ownedCount++;
        if (next() < 0.62) participant.offered[id] = 1 + Math.floor(next() * 3);
      }
    }
  }
  const start = performance.now();
  const result = optimize(input);
  const duration = performance.now() - start;
  verifyPlan(input, result);
  assert.ok(result.totalTransfers > 1000, "the performance fixture must exercise substantial flow");
  t.diagnostic(`618 stickers x 12 users: ${duration.toFixed(1)} ms; ${result.totalTransfers} transfers.`);
});
