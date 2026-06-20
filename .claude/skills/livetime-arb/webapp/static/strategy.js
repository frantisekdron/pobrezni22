/* strategy.js — měsíční plánovač diverzifikace, který plyne s reálným časem.
 *
 * Generuje pro každý den konkrétní strategii: fázi rozjezdu, denní limit
 * vkladu, rotaci sázkovek (diverzifikace), poměr mug/ostrých sázek, postupné
 * vklady/výběry kapitálu a odškrtávací checklist. Vše deterministicky z:
 *   - data startu, bankrollu, seznamu sázkovek a DNEŠNÍHO data.
 * Žádné závislosti; používá Tailwind třídy stránky. Persistence v localStorage.
 *
 * Vychází z ACCOUNT_LONGEVITY.md (rekreační profil, mug betting, diverzifikace,
 * pomalé škálování) — vše legálně, jeden účet na sázkovku, vlastní jméno.
 *
 * Veřejné API:  window.PlanUI.render(containerEl, {bankroll, bankrollRows})
 */
(function () {
  "use strict";

  const DAY = 86400000;
  const PLAN_DAYS = 60;
  const fmt = n => Math.round(n || 0).toLocaleString("cs-CZ");
  const lerp = (a, b, t) => a + (b - a) * Math.max(0, Math.min(1, t));
  const round = (n, step) => Math.round(n / step) * step;
  const iso = d => d.toISOString().slice(0, 10);
  const stripTime = d => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
  const addDays = (d, n) => new Date(stripTime(d).getTime() + n * DAY);
  const daysBetween = (a, b) => Math.round((stripTime(b) - stripTime(a)) / DAY);
  const csDate = d => d.toLocaleDateString("cs-CZ", { weekday: "short", day: "numeric", month: "numeric" });

  /* ── fáze rozjezdu ───────────────────────────────────────────── */
  const PHASES = [
    { key: "setup",  name: "Příprava",        from: 0,  to: 1,   color: "#64748b",
      goal: "Založ účty, dokonči KYC a rozlož počáteční kapitál. Žádné sázky na zisk." },
    { key: "warmup", name: "Rozjezd · bonusy + mug", from: 2, to: 13, color: "#0ea5e9",
      cap: [300, 600], goal: "Aktivuj bonusy a převáděj free bety. Pár mug betů, vypadej rekreačně. Žádné agresivní arby." },
    { key: "ramp",   name: "Náběh · lehké arby 1–3 %", from: 14, to: 44, color: "#22c55e",
      cap: [800, 1500], goal: "Surebety 1–3 % + value bety, drž rekreační vklady. 1 mug na ~5 ostrých. Rotuj sázkovky." },
    { key: "scale",  name: "Škálování",       from: 45, to: 59, color: "#a855f7",
      cap: [2000, 4000], goal: "Navyšuj vklady na zdravých účtech, rotuj objem z limitovaných. Hlídej trend max vkladu." },
    { key: "steady", name: "Provoz",          from: 60, to: 9999, color: "#eab308",
      cap: [2000, 5000], goal: "Ustálený režim: objem malých marží + bonusy. Disciplína a sledování zdraví účtů." },
  ];
  const phaseFor = d => PHASES.find(p => d >= p.from && d <= p.to) || PHASES[0];
  const phaseProgress = (d, p) => p.to >= 9990 ? 1 : (d - p.from) / Math.max(1, (p.to - p.from));

  // postupné nasazování kapitálu (podíl bankrollu „v oběhu")
  const DEPLOY = [[0, 0.20], [2, 0.25], [14, 0.30], [45, 0.60], [60, 1.0], [9999, 1.0]];
  function deployFraction(d) {
    for (let i = 0; i < DEPLOY.length - 1; i++) {
      const [d0, f0] = DEPLOY[i], [d1, f1] = DEPLOY[i + 1];
      if (d <= d1) return lerp(f0, f1, (d - d0) / Math.max(1, d1 - d0));
    }
    return 1;
  }

  /* ── výpočet jednoho dne ─────────────────────────────────────── */
  function rotation(d, books) {
    const n = books.length;
    return { focus: books[((d % n) + n) % n], secondary: books[((d + 1) % n + n) % n] };
  }

  function perBookTarget(d, B, n) {
    return Math.min(B * deployFraction(d) / n, 0.30 * B); // diverzifikace: max 30 % na sázkovku
  }

  function buildDay(d, S) {
    const { B, books, health } = S;
    const n = books.length;
    const phase = phaseFor(d);
    const pp = phaseProgress(d, phase);
    const date = addDays(S.start, d);

    // rotace + přesměrování od limitovaných účtů
    let { focus, secondary } = rotation(d, books);
    const limited = new Set((health || []).filter(h => h.balance > 0 && h.max_stake > 0 && h.max_stake < 1000).map(h => h.bookmaker));
    const warnings = [];
    const healthy = books.filter(b => !limited.has(b));
    if (limited.has(focus) && healthy.length) {
      warnings.push(`Účet „${focus}" má nízký max vklad → dnes ho vynech z fokusu.`);
      focus = healthy[d % healthy.length];
    }
    if ((limited.has(secondary) || secondary === focus)) {
      const pool = books.filter(b => b !== focus && !limited.has(b));
      if (pool.length) secondary = pool[d % pool.length];
      else { const any = books.filter(b => b !== focus); secondary = any.length ? any[d % any.length] : focus; }
    }
    limited.forEach(b => warnings.push(`„${b}" se blíží limitace — rotuj objem na „${focus}".`));

    // denní limit vkladu (rekreační), případně omezený zdravím účtu
    let cap = phase.cap ? round(lerp(phase.cap[0], phase.cap[1], pp), 50) : 0;
    const fh = (health || []).find(h => h.bookmaker === focus);
    if (fh && fh.max_stake > 0) cap = Math.min(cap, fh.max_stake);

    // nasazený kapitál + dnešní vkladová tranše do fokus sázkovky
    const deployed = round(B * deployFraction(d), 500);
    const tgtNow = perBookTarget(d, B, n);
    const tgtPrev = d >= n ? perBookTarget(d - n, B, n) : 0;
    let deposit = Math.max(0, round(tgtNow - tgtPrev, 500));
    if (d === 0) deposit = round(perBookTarget(0, B, n), 500); // počáteční vklad

    // postupný výběr (vypadat přirozeně, realizovat zisk) — od náběhu
    let withdraw = 0, wbook = null;
    if (phase.key === "ramp" || phase.key === "scale" || phase.key === "steady") {
      if (d % 3 === 0) { wbook = books[(d + 2) % n]; withdraw = round(cap * 1.5, 500); }
    }

    // poměr mug / ostrých sázek
    let sharp = 0, mug = 0, ratio = 10;
    if (phase.key === "warmup") { sharp = 0; mug = 2; ratio = 2; }
    else if (phase.key === "ramp") { sharp = Math.round(lerp(3, 6, pp)); ratio = 5; mug = Math.max(1, Math.round(sharp / ratio)); }
    else if (phase.key === "scale") { sharp = Math.round(lerp(6, 10, pp)); ratio = 8; mug = Math.max(1, Math.round(sharp / ratio)); }
    else if (phase.key === "steady") { sharp = 8; ratio = 10; mug = 1; }

    return { d, date, phase, pp, focus, secondary, cap, deployed, deposit,
             withdraw, wbook, sharp, mug, ratio, warnings, healthy, limited: [...limited],
             tasks: tasksFor({ d, phase, focus, secondary, cap, deposit, withdraw, wbook, sharp, mug, ratio, books, date }) };
  }

  /* ── konkrétní úkoly dne (checklist) ─────────────────────────── */
  function tasksFor(x) {
    const t = [];
    const date = iso(x.date);
    const add = s => t.push({ id: date + "#" + t.length, text: s });
    if (x.phase.key === "setup") {
      x.books.forEach(b => add(`Založ účet „${b}" na vlastní jméno + dokonči KYC (doklad, adresa).`));
      add(`Vlož počáteční kapitál rozloženě — cca ${fmt(x.deposit)} Kč na každou sázkovku (ne vše najednou).`);
      add(`Projdi si STRATEGY.md a ACCOUNT_LONGEVITY.md (rekreační profil, diverzifikace).`);
      add(`Pozn.: bet365 v ČR nesází — ber ho jen jako zdroj kurzu k porovnání.`);
    } else if (x.phase.key === "warmup") {
      add(`Aktivuj uvítací bonus / free bet na „${x.focus}".`);
      add(`Převeď free bet na jistý zisk přes záložku Bonusy (vsaď opačnou stranu na „${x.secondary}").`);
      add(`Vsaď ${x.mug} mug bet (populární trh, kulatá částka ≤ ${fmt(x.cap)} Kč) na „${x.focus}" / „${x.secondary}".`);
      if (x.deposit > 0) add(`Doplň kapitál: ~${fmt(x.deposit)} Kč na „${x.focus}".`);
      add(`Zkontroluj max vklad u všech účtů (záložka Bankroll).`);
    } else if (x.phase.key === "ramp") {
      add(`Najdi ${x.sharp} surebety 1–3 % (záložka Příležitosti), vklad ≤ ${fmt(x.cap)} Kč, kulaté částky.`);
      add(`Objem dej hlavně na „${x.focus}" a „${x.secondary}" (dnešní rotace).`);
      add(`Vsaď ${x.mug} mug bet jako kamufláž (1 mug na ~${x.ratio} ostrých).`);
      if (x.withdraw > 0) add(`Vyber postupně ~${fmt(x.withdraw)} Kč z „${x.wbook}" (přirozený výběr, ne vše).`);
      if (x.deposit > 0) add(`Doplň ~${fmt(x.deposit)} Kč na „${x.focus}" (postupné navyšování).`);
      add(`Aktualizuj Bankroll: zůstatky a hlavně max vklad (trend = signál limitace).`);
    } else if (x.phase.key === "scale") {
      add(`Navyš denní vklad na ≤ ${fmt(x.cap)} Kč POUZE na zdravých účtech.`);
      add(`Najdi ${x.sharp} surebety + value bety; rotuj objem na „${x.focus}" / „${x.secondary}".`);
      add(`Vsaď ${x.mug} mug bet (1 na ~${x.ratio} ostrých).`);
      if (x.withdraw > 0) add(`Vyber ~${fmt(x.withdraw)} Kč z „${x.wbook}".`);
      add(`Zkontroluj trend max vkladu — kde klesá, uber objem a rotuj jinam.`);
    } else {
      add(`Drž objem malých marží: ${x.sharp} sázek ≤ ${fmt(x.cap)} Kč.`);
      add(`1 mug bet na ~${x.ratio} ostrých, sázej i populární trhy.`);
      add(`Týdně: bonusové akce + kontrola zdraví všech účtů.`);
      if (x.withdraw > 0) add(`Postupný výběr ~${fmt(x.withdraw)} Kč z „${x.wbook}".`);
    }
    return t;
  }

  /* ── localStorage ────────────────────────────────────────────── */
  const SET_KEY = "plan_settings", DONE_KEY = "plan_done";
  const getJSON = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } };
  const setJSON = (k, v) => localStorage.setItem(k, JSON.stringify(v));

  function loadSettings(bankroll) {
    const s = getJSON(SET_KEY, null);
    if (s) return s;
    return { start: iso(new Date()), bankroll: bankroll || 100000,
             books: ["tipsport", "betano", "fortuna", "chance"] };
  }
  const done = () => getJSON(DONE_KEY, {});
  const isDone = id => !!done()[id];
  function toggleDone(id, v) { const d = done(); if (v) d[id] = true; else delete d[id]; setJSON(DONE_KEY, d); }

  /* ── render ──────────────────────────────────────────────────── */
  let CT, OPTS, SETTINGS, SELECTED;

  function render(container, opts) {
    CT = container; OPTS = opts || {};
    SETTINGS = loadSettings(OPTS.bankroll);
    const today = daysBetween(new Date(SETTINGS.start), new Date());
    SELECTED = (SELECTED == null) ? Math.max(0, today) : SELECTED;
    draw();
  }

  function S() {
    return { B: +SETTINGS.bankroll, books: SETTINGS.books, start: new Date(SETTINGS.start),
             health: OPTS.bankrollRows || [] };
  }

  function draw() {
    const st = S();
    const todayIdx = daysBetween(st.start, new Date());
    const day = buildDay(SELECTED, st);
    CT.innerHTML = [
      controlsHTML(todayIdx),
      legendHTML(),
      dayHTML(day, todayIdx),
      timelineHTML(st, todayIdx),
      diversificationHTML(st, todayIdx),
      progressHTML(st, todayIdx),
    ].join("");
    wire(st, todayIdx);
  }

  function controlsHTML(todayIdx) {
    return `<div class="card rounded-lg p-3 mb-3 flex flex-wrap gap-3 items-end text-sm">
      <label>Start plánu<br><input id="pl_start" type="date" value="${SETTINGS.start}" class="rounded px-2 py-1 mt-1"></label>
      <label>Bankroll (Kč)<br><input id="pl_bank" type="number" value="${SETTINGS.bankroll}" class="rounded px-2 py-1 w-28 mt-1"></label>
      <label class="flex-1 min-w-[16rem]">Sázkovky (čárkou)<br><input id="pl_books" value="${SETTINGS.books.join(", ")}" class="rounded px-2 py-1 w-full mt-1"></label>
      <button id="pl_save" class="bg-blue-700 hover:bg-blue-600 px-4 py-1.5 rounded font-semibold">Uložit plán</button>
      <button id="pl_today" class="bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded">Skok na dnešek</button>
      <span class="text-slate-400">Dnes je den ${todayIdx < 0 ? "(plán začíná v budoucnu)" : todayIdx + 1} / ${PLAN_DAYS}</span>
    </div>`;
  }

  function legendHTML() {
    return `<div class="flex flex-wrap gap-2 mb-3 text-xs">` +
      PHASES.map(p => `<span class="px-2 py-1 rounded" style="background:${p.color}22;border:1px solid ${p.color}">${p.name}</span>`).join("") +
      `</div>`;
  }

  function dayHTML(day, todayIdx) {
    const when = SELECTED < todayIdx ? "📅 minulý den" : SELECTED === todayIdx ? "⭐ DNES" : "🔮 budoucí den";
    const editable = SELECTED <= todayIdx;
    const total = day.tasks.length;
    const doneN = day.tasks.filter(t => isDone(t.id)).length;
    const pct = total ? Math.round(doneN / total * 100) : 0;
    const tasks = day.tasks.map(t => `<label class="flex items-start gap-2 py-1 ${editable ? "" : "opacity-60"}">
        <input type="checkbox" class="pl_task mt-1" data-id="${t.id}" ${isDone(t.id) ? "checked" : ""} ${editable ? "" : "disabled"}>
        <span class="text-sm">${t.text}</span></label>`).join("");
    const warn = day.warnings.length ? `<div class="mt-2 text-xs text-amber-300">⚠ ${day.warnings.join(" ")}</div>` : "";
    const metric = (label, val) => `<div class="bg-slate-900/60 rounded p-2"><div class="text-xs text-slate-400">${label}</div><div class="font-semibold">${val}</div></div>`;
    return `<div class="card rounded-lg p-4 mb-4 border-l-4" style="border-color:${day.phase.color}">
      <div class="flex justify-between items-center flex-wrap gap-2">
        <div><span class="text-xs px-2 py-0.5 rounded mr-2" style="background:${day.phase.color}33">${when}</span>
          <b class="text-lg">${csDate(day.date)}</b>
          <span class="ml-2 text-sm" style="color:${day.phase.color}">● ${day.phase.name}</span></div>
        <div class="text-sm text-slate-400">Den ${day.d + 1} / ${PLAN_DAYS}</div>
      </div>
      <div class="text-sm text-slate-300 mt-1 mb-3">${day.phase.goal}</div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3 text-sm">
        ${metric("Nasazený kapitál", fmt(day.deployed) + " Kč")}
        ${metric("Denní limit vkladu", day.cap ? "≤ " + fmt(day.cap) + " Kč" : "—")}
        ${metric("Fokus sázkovky", `<span class='text-blue-300'>${day.focus}</span> + ${day.secondary}`)}
        ${metric("Cíl sázek", `${day.sharp} ostrých · ${day.mug} mug`)}
        ${metric("Vklad dnes", day.deposit ? "+" + fmt(day.deposit) + " Kč → " + day.focus : "—")}
        ${metric("Výběr dnes", day.withdraw ? "−" + fmt(day.withdraw) + " Kč z " + day.wbook : "—")}
        ${metric("Poměr mug:ostré", "1 : " + day.ratio)}
        ${metric("Hotovo", doneN + " / " + total)}
      </div>
      ${warn}
      <div class="mt-2">
        <div class="flex justify-between text-xs text-slate-400 mb-1"><span>Dnešní checklist</span><span>${pct} %</span></div>
        <div class="h-2 bg-slate-800 rounded mb-2"><div class="h-2 rounded" style="width:${pct}%;background:${day.phase.color}"></div></div>
        ${tasks}
      </div>
    </div>`;
  }

  function timelineHTML(st, todayIdx) {
    let cells = "";
    for (let d = 0; d < PLAN_DAYS; d++) {
      const p = phaseFor(d);
      const isToday = d === todayIdx, isSel = d === SELECTED;
      cells += `<button class="pl_cell text-[10px] leading-none rounded" data-d="${d}"
        title="Den ${d + 1} · ${p.name}"
        style="background:${p.color}${isSel ? "" : "55"};width:1.55rem;height:2rem;
        ${isToday ? "outline:2px solid #fff;" : ""}${isSel ? "box-shadow:0 0 0 2px #1d4ed8;" : ""}">${d + 1}</button>`;
    }
    return `<div class="card rounded-lg p-3 mb-4">
      <div class="text-sm font-semibold mb-2">Měsíční timeline <span class="text-xs text-slate-400">(klikni na den)</span></div>
      <div class="flex flex-wrap gap-1">${cells}</div></div>`;
  }

  function diversificationHTML(st, todayIdx) {
    const { B, books } = st, n = books.length;
    const tgt = perBookTarget(Math.max(todayIdx, 0), B, n);
    const bars = books.map(b => {
      const pct = Math.round(tgt / B * 100);
      const warn = pct > 30;
      return `<div class="flex items-center gap-2 text-sm">
        <div class="w-24 text-blue-300">${b}</div>
        <div class="flex-1 h-3 bg-slate-800 rounded"><div class="h-3 rounded" style="width:${Math.min(100, pct)}%;background:${warn ? "#ef4444" : "#22c55e"}"></div></div>
        <div class="w-28 text-right">${fmt(tgt)} Kč (${pct}%)</div></div>`;
    }).join("");
    // rotace fokusu na příštích 14 dní
    let grid = `<table class="text-[10px] mt-2"><tr><td class="text-slate-400 pr-1">den→</td>`;
    for (let i = 0; i < 14; i++) grid += `<td class="text-center text-slate-400 px-0.5">${Math.max(0, todayIdx) + i + 1}</td>`;
    grid += `</tr>`;
    books.forEach(b => {
      grid += `<tr><td class="text-blue-300 pr-1">${b}</td>`;
      for (let i = 0; i < 14; i++) {
        const d = Math.max(0, todayIdx) + i;
        const r = rotation(d, books);
        const on = r.focus === b ? "●" : r.secondary === b ? "·" : "";
        grid += `<td class="text-center px-0.5">${on}</td>`;
      }
      grid += `</tr>`;
    });
    grid += `</table>`;
    return `<div class="card rounded-lg p-3 mb-4">
      <div class="text-sm font-semibold mb-2">Diverzifikace kapitálu <span class="text-xs text-slate-400">(cílové rozdělení dnes · max 30 % na sázkovku)</span></div>
      <div class="grid gap-1">${bars}</div>
      <div class="text-sm font-semibold mt-3 mb-1">Rotace fokusu (● hlavní · · vedlejší) — rozkládá objem, aby žádná sázkovka neviděla moc</div>
      <div class="overflow-auto">${grid}</div></div>`;
  }

  function progressHTML(st, todayIdx) {
    const upto = Math.min(todayIdx, PLAN_DAYS - 1);
    let total = 0, doneN = 0, streak = 0, broke = false;
    for (let d = 0; d <= upto; d++) {
      const day = buildDay(d, st);
      const td = day.tasks.length, dn = day.tasks.filter(t => isDone(t.id)).length;
      total += td; doneN += dn;
    }
    for (let d = upto; d >= 0; d--) {
      const day = buildDay(d, st);
      const all = day.tasks.length > 0 && day.tasks.every(t => isDone(t.id));
      if (all && !broke) streak++; else broke = true;
    }
    const pct = total ? Math.round(doneN / total * 100) : 0;
    return `<div class="card rounded-lg p-3 mb-2 text-sm flex flex-wrap gap-6">
      <div><div class="text-xs text-slate-400">Splněno z plánu (dosud)</div><div class="font-semibold">${doneN} / ${total} úkolů (${pct} %)</div></div>
      <div><div class="text-xs text-slate-400">Série splněných dní</div><div class="font-semibold">🔥 ${streak}</div></div>
      <div class="text-xs text-slate-500 self-center max-w-md">Plán se přepočítává z dnešního data — každý den otevři Plán a projdi „DNES". Cílem není maximální zisk z jedné sázky, ale životnost účtů.</div>
    </div>`;
  }

  function wire(st, todayIdx) {
    const q = s => CT.querySelector(s);
    q("#pl_save").onclick = () => {
      SETTINGS = { start: q("#pl_start").value || SETTINGS.start,
                   bankroll: +q("#pl_bank").value || SETTINGS.bankroll,
                   books: q("#pl_books").value.split(",").map(s => s.trim()).filter(Boolean) };
      if (!SETTINGS.books.length) SETTINGS.books = ["tipsport", "betano", "fortuna", "chance"];
      setJSON(SET_KEY, SETTINGS);
      SELECTED = Math.max(0, daysBetween(new Date(SETTINGS.start), new Date()));
      draw();
    };
    q("#pl_today").onclick = () => { SELECTED = Math.max(0, daysBetween(new Date(SETTINGS.start), new Date())); draw(); };
    CT.querySelectorAll(".pl_cell").forEach(b => b.onclick = () => { SELECTED = +b.dataset.d; draw(); });
    CT.querySelectorAll(".pl_task").forEach(c => c.onchange = () => {
      toggleDone(c.dataset.id, c.checked); draw();
    });
  }

  window.PlanUI = { render };
})();
