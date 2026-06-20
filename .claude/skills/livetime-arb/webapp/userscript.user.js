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
// @run-at       document-start
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

  // ════════════════════════════════════════════════════════════════
  //  AUTOMATICKÝ ODCHYT API  (hlavní mechanismus)
  //  Stránka sázkovky si sama stahuje kurzy přes interní JSON API.
  //  Tyhle hooky zachytí KAŽDOU takovou odpověď a pošlou ji do
  //  dashboardu — takže na přehledu soutěže získáš VŠECHNY zápasy
  //  najednou, automaticky, bez klikání a bez scrapování DOMu.
  // ════════════════════════════════════════════════════════════════
  const RAW_URL = "http://localhost:" + PORT + "/api/raw";
  const RAWMATCH = /offer|event|match|sport|odds|kurz|nab[ií]dka|z[aá]pas|prematch|live|market|selection|outcome|fixture|competition|tournament|betoffer/i;
  let captured = 0, statusEl = null;
  const setStatus = s => { if (statusEl) statusEl.textContent = s; };

  function forwardRaw(url, text) {
    if (!text || text.length < 150 || text.length > 4e6) return;
    if (!RAWMATCH.test(url) && !RAWMATCH.test(text.slice(0, 3000))) return;
    let json; try { json = JSON.parse(text); } catch (e) { return; }
    captured++; setStatus("📡 zachyceno API odpovědí: " + captured + " (jdou do dashboardu)");
    GM_xmlhttpRequest({
      method: "POST", url: RAW_URL,
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({ bookmaker: BOOK, url: String(url).slice(0, 300), json: json }),
      onerror: () => setStatus("❌ dashboard neběží? Spusť server.py (port " + PORT + ")"),
    });
  }

  (function hookFetch() {
    const _f = window.fetch;
    if (!_f) return;
    window.fetch = function () {
      const p = _f.apply(this, arguments);
      try {
        p.then(res => { try { res.clone().text().then(t => forwardRaw(res.url || arguments[0], t)).catch(() => {}); } catch (e) {} }).catch(() => {});
      } catch (e) {}
      return p;
    };
  })();

  (function hookXHR() {
    const _open = XMLHttpRequest.prototype.open, _send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (m, url) { this.__url = url; return _open.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function () {
      this.addEventListener("load", () => {
        try {
          const ct = this.getResponseHeader && (this.getResponseHeader("content-type") || "");
          if (this.responseType === "json") forwardRaw(this.__url || "", JSON.stringify(this.response));
          else if (!this.responseType || this.responseType === "text") {
            if (/json/i.test(ct) || /^[\s]*[\[{]/.test(this.responseText || "")) forwardRaw(this.__url || "", this.responseText);
          }
        } catch (e) {}
      });
      return _send.apply(this, arguments);
    };
  })();

  // nadpis trhu = krátký český text typu „… v zápasu", „Výsledek zápasu" …
  const MARKET_RE = /(v z[aá]pasu|v[yý]sledek z[aá]pasu|po[cč]et (g[oó]l[uů]|roh[uů]|karet|tref|gem|set)|kdo (d[aá]|bude)|v[ií]ce roh[uů]|padne g[oó]l|ka[zž]d[yý] t[yý]m|vst[rř]el|hlavou|dvojtip|handicap|polo[cč]as|p[rř]esn[yý] v[yý]sledek|oba t[yý]my|s[aá]zka bez|celkem g[oó]l|v[ií]t[eě]z|asijsk|1\. ?pol|2\. ?pol|\bBTTS\b)/i;
  // popisek výsledku, který se NEpočítá jako nadpis
  const OUTCOME_RE = /^(ano|ne|v[ií]ce ne[zž]|m[eé]n[eě] ne[zž]|nad|pod|remíza|neprohra|nebude remíza|\d+\. g[oó]l)/i;

  function eventNames() {
    // Tipsport: z URL /live/zapas/fotbal-nemecko-pobrezi-slonoviny/ID
    const m = location.pathname.match(/zapas\/[a-z]+-([a-z0-9-]+?)-([a-z0-9-]+)\/\d+/i);
    if (m) {
      const deslug = s => s.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      return { home: deslug(m[1]), away: deslug(m[2]) };
    }
    const sel = document.querySelector('[class*="participant" i],[class*="event-name" i],[class*="header" i] h1,h1');
    let title = sel ? clean(sel.textContent) : clean(document.title);
    title = title.split("|")[0];  // Fortuna: "Domácí - Hosté | Fortuna"
    let parts = title.split(/\s+(?:vs?\.?|–|—|·|•|-|:)\s+/i).map(clean).filter(Boolean);
    return parts.length >= 2 ? { home: parts[0], away: parts[1] } : { home: title.slice(0, 40) || "?", away: "?" };
  }

  // popisek výsledku z buňky vlevo od kurzu
  function outcomeLabel(el) {
    let p = el.previousElementSibling;
    while (p) { const t = clean(p.textContent); if (t && !ODDS_RE.test(t) && /[a-záčďéěíňóřšťúůýž]/i.test(t) && t.length <= 40) return t; p = p.previousElementSibling; }
    let n = el.parentElement;
    for (let i = 0; i < 3 && n; i++, n = n.parentElement) {
      const t = clean(n.textContent.replace(clean(el.textContent), ""));
      if (/[a-záčďéěíňóřšťúůýž]/i.test(t) && t.length <= 40) return t;
    }
    return "?";
  }

  function lineFrom(label) {
    if (!/(v[ií]ce|m[eé]n[eě]|nad|pod|over|under)/i.test(label)) return null;
    const m = label.match(/(\d+(?:[.,]\d+)?)/);
    return m ? parseFloat(m[1].replace(",", ".")) : null;
  }

  // hlavní scanner: projde DOM v pořadí, drží aktuální nadpis trhu,
  // a ke každému kurzu přiřadí trh + popisek výsledku. Funguje na Tipsport
  // layoutu (bloky trhů s českým nadpisem + řádky popisek→kurz).
  function scanSmart() {
    const { home, away } = eventNames();
    const sport = localStorage.getItem("la_sport") || "?";
    const out = [], seen = new Set();
    let market = "?";
    const all = document.body ? document.body.getElementsByTagName("*") : [];
    for (let i = 0; i < all.length; i++) {
      const el = all[i];
      const t = clean(el.textContent);
      if (el.children.length === 0 && ODDS_RE.test(t)) {
        const odds = parseFloat(t.replace(",", "."));
        if (odds > 1.01 && odds < 1000) {
          const label = outcomeLabel(el);
          if (label && label !== "?") {
            const key = market + "|" + label + "|" + odds;
            if (!seen.has(key)) {
              seen.add(key);
              out.push({ bookmaker: BOOK, sport, home, away, market, line: lineFrom(label), outcome: label, odds });
            }
          }
        }
      } else if (t.length <= 60 && MARKET_RE.test(t) && !OUTCOME_RE.test(t) && !ODDS_RE.test(t)) {
        // nadpis trhu (list i kontejner s krátkým textem)
        market = t.replace(/[📌▲▼^]+\s*$/, "").trim().slice(0, 60);
      }
    }
    return out;
  }

  function scrape() {
    try { return scanSmart(); }
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
  let auto = null;
  function panel() {
    if (document.querySelector("#la_box")) return;
    const box = document.createElement("div");
    box.id = "la_box";
    box.style.cssText = "position:fixed;z-index:2147483647;right:12px;bottom:12px;background:#0b0f17;color:#e5e9f0;border:1px solid #1d4ed8;border-radius:10px;padding:10px;font:12px system-ui;width:250px;box-shadow:0 6px 24px #000a";
    box.innerHTML = `<b>🟢 Livetime Arb · ${BOOK}</b>
      <div style="margin:6px 0;color:#94a3b8">Automaticky odchytávám API stránky. Otevři <b>přehled soutěže / nadcházející</b> a roluj — zachytí se všechny zápasy.</div>
      <div style="margin:6px 0">Sport: <input id="la_sport" value="${localStorage.getItem("la_sport")||""}" placeholder="fotbal" style="width:70px;background:#0e141f;color:#fff;border:1px solid #29384d;border-radius:4px">
      Port: <input id="la_port" value="${PORT}" style="width:48px;background:#0e141f;color:#fff;border:1px solid #29384d;border-radius:4px"></div>
      <button id="la_grab" style="background:#334155;color:#fff;border:0;border-radius:6px;padding:5px 8px;cursor:pointer" title="záložní sběr z DOMu">Sejmi DOM (záloha)</button>
      <div id="la_status" style="margin-top:6px;color:#94a3b8">📡 čekám na data stránky…</div>`;
    document.body.appendChild(box);
    statusEl = box.querySelector("#la_status");
    if (captured) setStatus("📡 zachyceno API odpovědí: " + captured);
    box.querySelector("#la_sport").onchange = e => localStorage.setItem("la_sport", e.target.value);
    box.querySelector("#la_port").onchange = e => localStorage.setItem("la_port", e.target.value);
    box.querySelector("#la_grab").onclick = send;
  }
  if (document.body) panel(); else window.addEventListener("DOMContentLoaded", panel);
})();
