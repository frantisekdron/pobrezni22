// background.js — service worker. Přeposílá data do lokálního dashboardu.
// (Fetch z rozšíření nepodléhá CORS ani mixed-content omezení stránky.)
const DASH = "http://localhost:8000";

async function post(path, payload) {
  try {
    const r = await fetch(DASH + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await r.json().catch(() => ({}));
  } catch (e) {
    return { error: String(e) };
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.type) return;
  if (msg.type === "raw") {
    post("/api/raw", { bookmaker: msg.bookmaker, url: msg.url, json: msg.json })
      .then(r => sendResponse(r || {}));
    return true;  // async odpověď
  }
  if (msg.type === "quotes") {
    post("/api/ingest", { quotes: msg.quotes }).then(r => sendResponse(r || {}));
    return true;
  }
});
