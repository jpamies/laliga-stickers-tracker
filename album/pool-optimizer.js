(() => {
  "use strict";

  const compareIds = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  function nonnegativeInteger(value, label) {
    if (!Number.isSafeInteger(value) || value < 0) {
      throw new TypeError(`${label} must be a safe nonnegative integer.`);
    }
  }

  function safeSum(a, b, label) {
    if (a > Number.MAX_SAFE_INTEGER - b) {
      throw new RangeError(`${label} exceeds the safe integer range.`);
    }
    return a + b;
  }

  function normalize(participants) {
    if (!Array.isArray(participants) || participants.length < 2) {
      throw new TypeError("participants must be an array of at least two participants.");
    }
    const ids = new Set();
    const users = [];
    for (const participant of participants) {
      if (!participant || typeof participant !== "object" || Array.isArray(participant)) {
        throw new TypeError("Each participant must be an object.");
      }
      const { id, offered, missing, ownedCount } = participant;
      if (typeof id !== "string" || id.length === 0) {
        throw new TypeError("Each participant id must be a nonempty string.");
      }
      if (ids.has(id)) throw new TypeError(`Duplicate participant id "${id}".`);
      ids.add(id);
      nonnegativeInteger(ownedCount, `Participant "${id}" ownedCount`);
      if (!offered || Object.prototype.toString.call(offered) !== "[object Object]") {
        throw new TypeError(`Participant "${id}" offered must be a sticker-to-quantity object.`);
      }
      if (!Array.isArray(missing)) {
        throw new TypeError(`Participant "${id}" missing must be an array of sticker ids.`);
      }
      const missingIds = new Set();
      for (const stickerId of missing) {
        if (typeof stickerId !== "string" || stickerId.length === 0) {
          throw new TypeError(`Participant "${id}" missing sticker ids must be nonempty strings.`);
        }
        if (missingIds.has(stickerId)) {
          throw new TypeError(`Participant "${id}" has duplicate missing sticker "${stickerId}".`);
        }
        missingIds.add(stickerId);
      }
      const keys = Reflect.ownKeys(offered);
      for (const stickerId of keys) {
        if (typeof stickerId !== "string" || stickerId.length === 0) {
          throw new TypeError(`Participant "${id}" offered sticker ids must be nonempty strings.`);
        }
      }
      const quantities = new Map();
      let available = 0;
      for (const stickerId of keys.sort(compareIds)) {
        const quantity = offered[stickerId];
        nonnegativeInteger(quantity, `Participant "${id}" offered quantity for "${stickerId}"`);
        if (quantity > 0 && missingIds.has(stickerId)) {
          throw new TypeError(`Participant "${id}" both offers and is missing sticker "${stickerId}".`);
        }
        available = safeSum(available, quantity, `Participant "${id}" total offered quantity`);
        quantities.set(stickerId, quantity);
      }
      users.push({
        id,
        offered: quantities,
        missing: Array.from(missingIds).sort(compareIds),
        ownedCount,
        available,
        useful: 0,
      });
    }
    return users.sort((a, b) => compareIds(a.id, b.id));
  }

  function ranks(values) {
    return new Map(Array.from(new Set(values)).sort((a, b) => a - b)
      .map((value, index) => [value, BigInt(index)]));
  }

  function addEdge(graph, from, to, capacity, cost) {
    const forward = {
      to, reverse: graph[to].length, capacity, original: capacity, cost, zero: false,
    };
    const reverse = {
      to: from, reverse: graph[from].length, capacity: 0, original: 0, cost: -cost, zero: false,
    };
    graph[from].push(forward);
    graph[to].push(reverse);
    return forward;
  }

  class MinHeap {
    constructor() {
      this.items = [];
    }

    before(a, b) {
      return a.distance < b.distance || (a.distance === b.distance && a.node < b.node);
    }

    push(node, distance) {
      const item = { node, distance };
      const items = this.items;
      let index = items.length;
      items.push(item);
      while (index > 0) {
        const parent = Math.floor((index - 1) / 2);
        if (!this.before(item, items[parent])) break;
        items[index] = items[parent];
        index = parent;
      }
      items[index] = item;
    }

    pop() {
      const items = this.items;
      const first = items[0];
      const last = items.pop();
      if (items.length === 0) return first;
      let index = 0;
      while (index * 2 + 1 < items.length) {
        let child = index * 2 + 1;
        if (child + 1 < items.length && this.before(items[child + 1], items[child])) child++;
        if (!this.before(items[child], last)) break;
        items[index] = items[child];
        index = child;
      }
      items[index] = last;
      return first;
    }
  }

  function shortestDistances(graph, source, sink, potentials) {
    const distances = Array(graph.length).fill(null);
    const heap = new MinHeap();
    distances[source] = 0n;
    heap.push(source, 0n);
    while (heap.items.length > 0) {
      const { node, distance } = heap.pop();
      if (distance !== distances[node]) continue;
      if (node === sink) break;
      for (const edge of graph[node]) {
        if (edge.capacity === 0) continue;
        const reduced = edge.cost + potentials[node] - potentials[edge.to];
        if (reduced < 0n) throw new Error("Internal optimizer error: negative reduced cost.");
        const candidate = distance + reduced;
        if (distances[edge.to] === null || candidate < distances[edge.to]) {
          distances[edge.to] = candidate;
          heap.push(edge.to, candidate);
        }
      }
    }
    return distances;
  }

  // Iterative Dinic DFS avoids a call-stack limit on long exchange cycles.
  function augmentLevelPath(graph, source, sink, limit, levels, next) {
    const nodes = [source];
    const edges = [];
    const limits = [limit];
    while (nodes.length > 0) {
      const node = nodes[nodes.length - 1];
      if (node === sink) {
        const amount = limits[limits.length - 1];
        for (let index = 0; index < edges.length; index++) {
          const edge = graph[nodes[index]][edges[index]];
          edge.capacity -= amount;
          graph[edge.to][edge.reverse].capacity += amount;
        }
        return amount;
      }
      const row = graph[node];
      while (next[node] < row.length) {
        const edge = row[next[node]];
        if (edge.capacity > 0 && edge.zero && levels[edge.to] === levels[node] + 1) break;
        next[node]++;
      }
      if (next[node] === row.length) {
        levels[node] = -1;
        nodes.pop();
        limits.pop();
        if (edges.length > 0) {
          edges.pop();
          next[nodes[nodes.length - 1]]++;
        }
      } else {
        const edge = row[next[node]];
        nodes.push(edge.to);
        edges.push(next[node]);
        limits.push(Math.min(limits[limits.length - 1], edge.capacity));
      }
    }
    return 0;
  }

  function zeroCostMaxFlow(graph, source, sink, limit) {
    let total = 0;
    const levels = Array(graph.length);
    while (total < limit) {
      levels.fill(-1);
      levels[source] = 0;
      const queue = [source];
      for (let head = 0; head < queue.length; head++) {
        const node = queue[head];
        for (const edge of graph[node]) {
          if (edge.capacity > 0 && edge.zero && levels[edge.to] === -1) {
            levels[edge.to] = levels[node] + 1;
            queue.push(edge.to);
          }
        }
      }
      if (levels[sink] === -1) break;
      const next = Array(graph.length).fill(0);
      while (total < limit) {
        const amount = augmentLevelPath(graph, source, sink, limit - total, levels, next);
        if (amount === 0) break;
        total += amount;
      }
    }
    return total;
  }

  function repairCirculation(graph, source, sink, required) {
    const potentials = Array(graph.length).fill(0n);
    let repaired = 0;
    while (repaired < required) {
      const distances = shortestDistances(graph, source, sink, potentials);
      const distance = distances[sink];
      if (distance === null) throw new Error("Internal optimizer error: infeasible circulation repair.");
      // Clipping also updates unreachable nodes and preserves global dual feasibility.
      for (let node = 0; node < graph.length; node++) {
        potentials[node] += distances[node] !== null && distances[node] < distance
          ? distances[node] : distance;
      }
      for (let node = 0; node < graph.length; node++) {
        for (const edge of graph[node]) {
          edge.zero = edge.cost + potentials[node] - potentials[edge.to] === 0n;
        }
      }
      const amount = zeroCostMaxFlow(graph, source, sink, required - repaired);
      if (amount === 0) throw new Error("Internal optimizer error: circulation repair made no progress.");
      repaired += amount;
    }
  }

  /**
   * Pure, exact balanced exchange plan. Only actual transfers earn credit:
   * every participant gives exactly as many stickers as they receive.
   * available includes all offered surplus; unsafe available sums are rejected.
   *
   * Objectives, in strict lexicographic order: transfer count; receipts of
   * stickers with exactly one eligible missing recipient; summed recipient ranks for
   * useful outgoing copies (sum min(offered, pool demand)), total surplus,
   * ownedCount, then ascending participant id. Equal metric values share ranks.
   * Remaining ties and output ordering use code-unit-sorted ids, not locale.
   */
  function optimize(participants) {
    const users = normalize(participants);
    const bySticker = new Map();
    for (let user = 0; user < users.length; user++) {
      for (const [id, quantity] of users[user].offered) {
        if (quantity === 0) continue;
        if (!bySticker.has(id)) bySticker.set(id, { id, donors: [], recipients: [] });
        bySticker.get(id).donors.push({ user, quantity });
      }
    }
    for (let user = 0; user < users.length; user++) {
      for (const id of users[user].missing) {
        const sticker = bySticker.get(id);
        if (sticker) sticker.recipients.push(user);
      }
    }
    const stickers = Array.from(bySticker.values())
      .filter((sticker) => sticker.recipients.length > 0)
      .sort((a, b) => compareIds(a.id, b.id));
    const incoming = Array(users.length).fill(0);
    let receiptCount = 0;
    for (const sticker of stickers) {
      receiptCount = safeSum(receiptCount, sticker.recipients.length, "Total receipt opportunities");
      for (const user of sticker.recipients) incoming[user]++;
      for (const donor of sticker.donors) {
        users[donor.user].useful = safeSum(
          users[donor.user].useful,
          Math.min(donor.quantity, sticker.recipients.length),
          "Useful outgoing quantity",
        );
      }
    }
    const summary = users.map(({ id, available }) => ({
      id, available, given: 0, received: 0, balance: 0,
    }));
    if (receiptCount === 0) return { totalTransfers: 0, transfers: [], participants: summary };

    const usefulRanks = ranks(users.map((user) => user.useful));
    const offeredRanks = ranks(users.map((user) => user.available));
    const ownedRanks = ranks(users.map((user) => user.ownedCount));
    // Every summed lower digit is < radix. One transfer therefore outweighs
    // ALL secondary bonuses in a plan. BigInt keeps costs/potentials exact even
    // with MAX_SAFE_INTEGER inventory counts; output counts remain numbers.
    const radix = BigInt(receiptCount) * BigInt(users.length) + 1n;
    const ownedWeight = radix;
    const offeredWeight = ownedWeight * radix;
    const usefulWeight = offeredWeight * radix;
    const degreeWeight = usefulWeight * radix;
    const transferWeight = degreeWeight * radix;
    const source = users.length + stickers.length;
    const sink = source + 1;
    const graph = Array.from({ length: sink + 1 }, () => []);
    for (let index = 0; index < stickers.length; index++) {
      const sticker = stickers[index];
      const node = users.length + index;
      const degreeBonus = sticker.recipients.length === 1 ? degreeWeight : 0n;
      for (const donor of sticker.donors) {
        // No sticker can be received more often than its pool demand.
        donor.edge = addEdge(
          graph, donor.user, node, Math.min(donor.quantity, sticker.recipients.length), 0n,
        );
      }
      sticker.receipts = sticker.recipients.map((user) => {
        const recipient = users[user];
        const reward = transferWeight + degreeBonus
          + usefulRanks.get(recipient.useful) * usefulWeight
          + offeredRanks.get(recipient.available) * offeredWeight
          + ownedRanks.get(recipient.ownedCount) * ownedWeight
          + BigInt(users.length - 1 - user);
        const edge = addEdge(graph, node, user, 1, -reward);
        edge.capacity = 0;
        graph[user][edge.reverse].capacity = 1;
        return { user, edge };
      });
      addEdge(graph, node, sink, sticker.recipients.length, 0n);
    }
    for (let user = 0; user < users.length; user++) {
      if (incoming[user] > 0) addEdge(graph, source, user, incoming[user], 0n);
    }

    // User -> sticker -> user circulation enforces both balance and supply.
    // Start with all negative-cost receipt edges saturated: all residual costs
    // are nonnegative. Repair the resulting imbalances by min-cost max-flow
    // (Dijkstra potentials + zero-reduced-cost Dinic). Cancelling every receipt
    // is always feasible. A completed minimum-cost repair is consequently a
    // minimum-cost circulation, including cycles of any participant count.
    repairCirculation(graph, source, sink, receiptCount);

    const transfers = [];
    for (const sticker of stickers) {
      let donorIndex = 0;
      const donors = sticker.donors.map(({ user, edge }) => ({
        user, remaining: edge.original - edge.capacity,
      }));
      for (const receipt of sticker.receipts) {
        if (receipt.edge.capacity !== 0) continue;
        while (donorIndex < donors.length && donors[donorIndex].remaining === 0) donorIndex++;
        if (donorIndex === donors.length) {
          throw new Error("Internal optimizer error: receipt has no donor.");
        }
        const donor = donors[donorIndex];
        donor.remaining--;
        summary[donor.user].given++;
        summary[receipt.user].received++;
        transfers.push({
          from: users[donor.user].id,
          to: users[receipt.user].id,
          stickerId: sticker.id,
          quantity: 1,
        });
      }
    }
    for (const participant of summary) {
      participant.balance = participant.given - participant.received;
      if (participant.balance !== 0) throw new Error("Internal optimizer error: unbalanced plan.");
    }
    transfers.sort((a, b) => compareIds(a.from, b.from)
      || compareIds(a.to, b.to) || compareIds(a.stickerId, b.stickerId));
    return { totalTransfers: transfers.length, transfers, participants: summary };
  }

  const api = { optimize };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.PaniniPool = api;
})();
