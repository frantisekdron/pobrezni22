// ==UserScript==
// @name         Livetime Arb — automatický sběr kurzů
// @namespace    livetime-arb
// @version      0.2
// @description  Běží v TVÉM prohlížeči na stránkách sázkovek, sebere VŠECHNY zobrazené kurzy (všechny trhy) a pošle je do lokálního dashboardu (http://localhost:8000). Obchází 403 i mixed-content přes GM_xmlhttpRequest.
// @match        https://www.tipsport.cz/*
// @match        https://*.tipsport.cz/*
// @match        https://www.ifortuna.cz/*
// @match        https://www.betano.cz/*
// @match        https://*.betano.cz/*
// @match        https://www.bet365.com/*
// @match        https://*.bet365.com/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==
/*
  POZNÁMKA K PŘESNOSTI:
  Každá sázkovka má jinou (a často obfuskovanou) strukturu stránky. Tenhle
  skript má GENERICKÝ scanner, který bere každý prvek vypadající jako kurz
  (desetinné číslo 1.01–1000) a hledá k němu nejbližší popisek a nadpis trhu.
  Zabere hodně trhů, ale názvy trhů/výsledků nemusí být vždy přesné.

  Pro PŘESNÝ sběr dané sázkovky vyplň adaptér v ADAPTERS[...] (selektory) —
  stačí mi poslat ukázku HTML jednoho živého zápasu a selektory doplním.
*/
(function () {
  "use strict";
  const PORT = localStorage.getItem("la_port") || "8000";
  const ENDPOINT = "http://localhost:" + PORT + "/api/ingest";

  const HOST = location.host;
  const BOOK =
    /tipsport/.test(HOST) ? "tipsport" :
    /ifortuna|fortuna/.test(HOST) ? "fortuna" :
    /betano/.test(HOST) ? "betano" :
    /bet365/.test(HOST) ? "bet365" : "?";

  const ODDS_RE = /^\d{1,3}[.,]\d{1,2}$/;
  const clean = s => (s || "").replace(/\s+/g, " ").trim();

  // ── popisek výsledku poblíž kurzu ────────────────────────────────
  function labelNear(el) {
    const aria = el.getAttribute("aria-label") || el.getAttribute("title");
    if (aria && !ODDS_RE.test(clean(aria))) return clean(aria);
    // projdi nahoru max 4 úrovně a vezmi text bez čísla kurzu
    let n = el, hops = 0;
    while (n && hops++ < 4) {
      const t = clean(n.getAttribute && (n.getAttribute("aria-label") || ""));
      if (t && !ODDS_RE.test(t)) return t;
      n = n.parentElement;
    }
    // sourozenec vlevo
    let p = el.previousElementSibling;
    while (p) { const t = clean(p.textContent); if (t && !ODDS_RE.test(t)) return t.slice(0, 40); p = p.previousElementSibling; }
    return "?";
  }

  // ── nadpis trhu nad kurzem ───────────────────────────────────────
  function marketNear(el) {
    let n = el;
    for (let i = 0; i < 8 && n; i++, n = n.parentElement) {
      const h = n.querySelector && n.querySelector('h1,h2,h3,h4,[role="heading"],[class*="market" i],[class*="trh" i]');
      if (h) { const t = clean(h.textContent); if (t && !ODDS_RE.test(t)) return t.slice(0, 60); }
    }
    return "?";
  }

  // ── název zápasu ─────────────────────────────────────────────────
  function eventNames() {
    const sel = document.querySelector('[class*="participant" i],[class*="event-name" i],[class*="match" i] h1,h1');
    let title = sel ? clean(sel.textContent) : clean(document.title);
    let parts = title.split(/\s+(?:vs?\.?|–|—|-|:)\s+/i).map(clean).filter(Boolean);
    if (parts.length >= 2) return { home: parts[0], away: parts[1] };
    return { home: title.slice(0, 40) || "?", away: "?" };
  }

  // ── adaptéry (přesné selektory per sázkovka — k doplnění) ─────────
  const ADAPTERS = {
    // tipsport: function(){ return [ {market, outcome, odds, line} ... ]; },
    // fortuna:  function(){ ... },
    // betano:   function(){ ... },
    // bet365:   function(){ ... },
  };

  function genericScan() {
    const { home, away } = eventNames();
    const sport = localStorage.getItem("la_sport") || "?";
    const out = [], seen = new Set();
    document.querySelectorAll("button,span,a,div,td").forEach(el => {
      if (el.children.length) return;                 // jen listové prvky
      const txt = clean(el.textContent);
      if (!ODDS_RE.test(txt)) return;
      const odds = parseFloat(txt.replace(",", "."));
      if (!(odds > 1.01 && odds < 1000)) return;
      const label = labelNear(el), market = marketNear(el);
      const key = market + "|" + label + "|" + odds;
      if (seen.has(key)) return; seen.add(key);
      let line = null;
      const lm = label.match(/(\d+(?:[.,]\d+)?)/);
      if (lm && /(nad|pod|over|under|vice|mene|\+|\-)/i.test(label)) line = parseFloat(lm[1].replace(",", "."));
      out.push({ bookmaker: BOOK, sport, home, away, market, line, outcome: label, odds });
    });
    return out;
  }

  function scrape() {
    try { return ADAPTERS[BOOK] ? ADAPTERS[BOOK]() : genericScan(); }
    catch (e) { console.error("[livetime-arb] scrape error", e); return []; }
  }

  function send() {
    const quotes = scrape();
    setStatus(`sbírám… ${quotes.length} kurzů`);
    if (!quotes.length) { setStatus("nic nenalezeno (zkus jiný trh / adaptér)"); return; }
    GM_xmlhttpRequest({
      method: "POST", url: ENDPOINT,
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({ quotes }),
      onload: r => setStatus(`✅ odesláno ${quotes.length} → dashboard (${r.status})`),
      onerror: () => setStatus("❌ dashboard neběží? Spusť server.py na portu " + PORT),
    });
  }

  // ── plovoucí ovládací panel ──────────────────────────────────────
  let auto = null, statusEl;
  function setStatus(s) { if (statusEl) statusEl.textContent = s; }
  function panel() {
    const box = document.createElement("div");
    box.style.cssText = "position:fixed;z-index:999999;right:12px;bottom:12px;background:#0b0f17;color:#e5e9f0;border:1px solid #1d4ed8;border-radius:10px;padding:10px;font:12px system-ui;width:230px;box-shadow:0 6px 24px #000a";
    box.innerHTML = `<b>🟢 Livetime Arb · ${BOOK}</b>
      <div style="margin:6px 0">Sport: <input id="la_sport" value="${localStorage.getItem("la_sport")||""}" placeholder="tenis" style="width:70px;background:#0e141f;color:#fff;border:1px solid #29384d;border-radius:4px">
      Port: <input id="la_port" value="${PORT}" style="width:48px;background:#0e141f;color:#fff;border:1px solid #29384d;border-radius:4px"></div>
      <button id="la_grab" style="background:#1d4ed8;color:#fff;border:0;border-radius:6px;padding:5px 8px;cursor:pointer">Sejmi & odešli</button>
      <button id="la_auto" style="background:#334155;color:#fff;border:0;border-radius:6px;padding:5px 8px;cursor:pointer">Auto 20s</button>
      <div id="la_status" style="margin-top:6px;color:#94a3b8">připraveno</div>`;
    document.body.appendChild(box);
    statusEl = box.querySelector("#la_status");
    box.querySelector("#la_sport").onchange = e => localStorage.setItem("la_sport", e.target.value);
    box.querySelector("#la_port").onchange = e => localStorage.setItem("la_port", e.target.value);
    box.querySelector("#la_grab").onclick = send;
    box.querySelector("#la_auto").onclick = e => {
      if (auto) { clearInterval(auto); auto = null; e.target.textContent = "Auto 20s"; e.target.style.background = "#334155"; }
      else { auto = setInterval(send, 20000); send(); e.target.textContent = "Auto ON"; e.target.style.background = "#16a34a"; }
    };
  }
  if (document.body) panel(); else window.addEventListener("DOMContentLoaded", panel);
})();
