// content.js — běží v ISOLATED světě. Přijímá zachycené API odpovědi od
// inject.js, posílá je do dashboardu (přes background.js), zobrazuje panel
// a umí zálohový DOM sběr.
(function () {
  "use strict";
  const HOST = location.host;
  const BOOK = /tipsport/.test(HOST) ? "tipsport"
    : /ifortuna|fortuna/.test(HOST) ? "fortuna"
    : /betano/.test(HOST) ? "betano"
    : /bet365/.test(HOST) ? "bet365" : "?";
  const RAWMATCH = /offer|event|odds|kurz|nab[ií]dka|z[aá]pas|prematch|market|selection|outcome|fixture|competition|betoffer|top-events/i;
  let captured = 0, sent = 0, statusEl = null;
  const setStatus = s => { if (statusEl) statusEl.textContent = s; };

  // příjem zachycených odpovědí ze stránky
  window.addEventListener("message", ev => {
    const d = ev.data;
    if (!d || d.__livetimeArb !== 1 || !d.text) return;
    if (d.text.length < 150 || d.text.length > 4e6) return;
    if (!RAWMATCH.test(d.url) && !RAWMATCH.test(d.text.slice(0, 3000))) return;
    let json; try { json = JSON.parse(d.text); } catch (e) { return; }
    captured++;
    chrome.runtime.sendMessage({ type: "raw", bookmaker: BOOK, url: d.url.slice(0, 300), json },
      resp => { if (resp && typeof resp.parsed === "number") { sent += resp.parsed; }
                setStatus(`📡 zachyceno ${captured} · z toho ${sent} kurzů do dashboardu`); });
  });

  // ── zálohový DOM scanner ───────────────────────────────────────────
  const clean = s => (s || "").replace(/\s+/g, " ").trim();
  const ODDS_RE = /^\d{1,3}[.,]\d{1,2}$/;
  const MARKET_RE = /(v z[aá]pasu|v[yý]sledek z[aá]pasu|po[cč]et (g[oó]l[uů]|roh[uů]|karet|tref|gem|set)|kdo (d[aá]|bude)|v[ií]ce roh[uů]|padne g[oó]l|ka[zž]d[yý] t[yý]m|vst[rř]el|hlavou|dvojtip|handicap|polo[cč]as|p[rř]esn[yý] v[yý]sledek|oba t[yý]my|s[aá]zka bez|celkem g[oó]l|v[ií]t[eě]z|asijsk|1\. ?pol|2\. ?pol|\bBTTS\b)/i;
  const OUTCOME_RE = /^(ano|ne|v[ií]ce ne[zž]|m[eé]n[eě] ne[zž]|nad|pod|remíza|neprohra|nebude remíza|\d+\. g[oó]l)/i;
  const EVENT_RE = /^[\p{L}][\p{L}\p{M}.\s]{1,28}\s[-–·]\s[\p{L}][\p{L}\p{M}.\s]{1,28}$/u;
  function outcomeLabel(el) {
    let p = el.previousElementSibling;
    while (p) { const t = clean(p.textContent); if (t && !ODDS_RE.test(t) && /[a-záčďéěíňóřšťúůýž]/i.test(t) && t.length <= 40) return t; p = p.previousElementSibling; }
    let n = el.parentElement;
    for (let i = 0; i < 3 && n; i++, n = n.parentElement) { const t = clean(n.textContent.replace(clean(el.textContent), "")); if (/[a-záčďéěíňóřšťúůýž]/i.test(t) && t.length <= 40) return t; }
    return "?";
  }
  function lineFrom(label) { if (!/(v[ií]ce|m[eé]n[eě]|nad|pod|over|under)/i.test(label)) return null; const m = label.match(/(\d+(?:[.,]\d+)?)/); return m ? parseFloat(m[1].replace(",", ".")) : null; }
  function scanDOM() {
    const sport = localStorage.getItem("la_sport") || "?";
    let home = "?", away = "?", market = "?";
    const out = [], seen = new Set();
    const all = document.body ? document.body.getElementsByTagName("*") : [];
    for (let i = 0; i < all.length; i++) {
      const el = all[i], t = clean(el.textContent);
      if (el.children.length === 0 && ODDS_RE.test(t)) {
        const odds = parseFloat(t.replace(",", "."));
        if (odds > 1.01 && odds < 1000) {
          const label = outcomeLabel(el);
          if (label && label !== "?") {
            const key = home + "|" + away + "|" + market + "|" + label + "|" + odds;
            if (!seen.has(key)) { seen.add(key); out.push({ bookmaker: BOOK, sport, home, away, market, line: lineFrom(label), outcome: label, odds }); }
          }
        }
      } else if (t.length <= 50 && EVENT_RE.test(t) && !MARKET_RE.test(t)) {
        const parts = t.split(/\s[-–·]\s/); if (parts.length === 2) { home = clean(parts[0]); away = clean(parts[1]); market = "?"; }
      } else if (t.length <= 60 && MARKET_RE.test(t) && !OUTCOME_RE.test(t) && !ODDS_RE.test(t)) {
        market = t.replace(/[\u{1F4CC}▲▼^]+\s*$/u, "").trim().slice(0, 60);
      }
    }
    return out;
  }

  // ── auto-rozkliknutí všech trhů na stránce ─────────────────────────
  const EXPAND_TXT = /zobrazit v[sš]e|v[ií]ce trh|v[sš]echny trhy|zobrazit dal|více mo[zž]nost|show all|all markets|rozbalit/i;
  function expandAll() {
    let n = 0;
    const els = document.querySelectorAll('button,a,[role="button"],[aria-expanded="false"]');
    for (const el of els) {
      if (el.dataset && el.dataset.laExpanded) continue;
      const t = (el.textContent || "").trim();
      const collapsed = el.getAttribute && el.getAttribute("aria-expanded") === "false";
      if (collapsed || (t.length < 40 && EXPAND_TXT.test(t))) {
        try { el.click(); if (el.dataset) el.dataset.laExpanded = "1"; n++; } catch (e) {}
      }
    }
    return n;
  }

  // ── odkazy na detaily zápasů (pro „projet vše") ────────────────────
  const DETAIL = {
    tipsport: /tipsport\.cz\/(kurzy|live)\/.*?[a-z]-\d{5,}/i,
    fortuna: /ifortuna\.cz\/sazeni\/[^/]+\/[^/]+\/[^/]+\/[^/?#]+/i,
    betano: /betano\.cz\/(live|sport)\/[^/]+\/\d{6,}/i,
    bet365: /bet365\.com\/.+#/i,
  };
  function detailLinks() {
    const rx = DETAIL[BOOK]; if (!rx) return [];
    const set = new Set();
    document.querySelectorAll("a[href]").forEach(a => {
      const h = (a.href || "").split("#")[0];
      if (rx.test(a.href) && h !== location.href.split("#")[0]) set.add(h);
    });
    return [...set].slice(0, 40);
  }

  // ── plovoucí panel ─────────────────────────────────────────────────
  function panel() {
    if (document.querySelector("#la_box")) return;
    const box = document.createElement("div");
    box.id = "la_box";
    box.style.cssText = "position:fixed;z-index:2147483647;right:12px;bottom:12px;background:#0b0f17;color:#e5e9f0;border:1px solid #1d4ed8;border-radius:10px;padding:10px;font:12px system-ui;width:250px;box-shadow:0 6px 24px #000a";
    box.innerHTML = '<b>🟢 Livetime Arb · ' + BOOK + '</b>'
      + '<div style="margin:6px 0;color:#94a3b8">Sbírám API stránky automaticky a sám rozklikávám trhy.</div>'
      + '<div style="margin:6px 0">Sport: <input id="la_sport" placeholder="fotbal" style="width:80px;background:#0e141f;color:#fff;border:1px solid #29384d;border-radius:4px">'
      + ' <label style="color:#94a3b8"><input type="checkbox" id="la_exp" checked> rozklikávat</label></div>'
      + '<button id="la_crawl" style="background:#1d4ed8;color:#fff;border:0;border-radius:6px;padding:5px 8px;cursor:pointer">Projet všechny zápasy</button>'
      + ' <button id="la_grab" style="background:#334155;color:#fff;border:0;border-radius:6px;padding:5px 8px;cursor:pointer">Sejmi DOM</button>'
      + '<div id="la_status" style="margin-top:6px;color:#94a3b8">📡 čekám na data stránky…</div>';
    document.body.appendChild(box);
    statusEl = box.querySelector("#la_status");
    const si = box.querySelector("#la_sport");
    si.value = localStorage.getItem("la_sport") || "";
    si.onchange = e => localStorage.setItem("la_sport", e.target.value);
    box.querySelector("#la_grab").onclick = () => {
      const q = scanDOM();
      chrome.runtime.sendMessage({ type: "quotes", quotes: q },
        () => setStatus("DOM: odesláno " + q.length + " kurzů"));
    };
    box.querySelector("#la_crawl").onclick = () => {
      const urls = detailLinks();
      if (!urls.length) { setStatus("Na téhle stránce nevidím odkazy na zápasy — otevři přehled soutěže."); return; }
      setStatus("Projíždím " + urls.length + " zápasů v tabech na pozadí…");
      chrome.runtime.sendMessage({ type: "crawl", urls });
    };

    // auto-rozklikávání trhů co pár sekund
    setInterval(() => {
      if (box.querySelector("#la_exp") && box.querySelector("#la_exp").checked) {
        const n = expandAll();
        if (n) setStatus(`📡 zachyceno ${captured} · ${sent} kurzů · rozkliknuto ${n} trhů`);
      }
    }, 2500);
    if (captured) setStatus(`📡 zachyceno ${captured} · ${sent} kurzů`);
  }
  if (document.body) panel(); else window.addEventListener("DOMContentLoaded", panel);
})();
