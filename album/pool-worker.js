"use strict";

importScripts("pool-optimizer.js?v=1");

self.addEventListener("message", (event) => {
  try {
    const result = self.PaniniPool.optimize(event.data.participants);
    self.postMessage({ result });
  } catch (error) {
    console.error("No se pudo optimizar el intercambio grupal.", error);
    self.postMessage({
      error: error instanceof Error ? error.message : "No se pudo optimizar el intercambio grupal.",
    });
  }
});
