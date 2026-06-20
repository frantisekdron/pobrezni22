#!/usr/bin/env python3
"""
scraper.py — plně automatický sběr kurzů řízeným prohlížečem (Playwright).

ŽÁDNÝ Tampermonkey, žádné klikání. Spustíš a robot:
  1) otevře skutečný prohlížeč (na TVÉM Macu = tvá IP, můžeš se přihlásit),
  2) projede přehledy nastavených sázkovek (prematch nabídku),
  3) odchytí interní API odpovědi (uloží syrový JSON do dashboardu /api/raw),
  4) zároveň z DOMu vytáhne kurzy (scanSmart) → pošle do /api/ingest,
  5) opakuje každých REFRESH_S sekund.

Spuštění (vyřeší vše skript scrape.sh):
    bash scrape.sh
nebo ručně:
    pip install playwright && python -m playwright install chromium
    python3 scraper.py

Dashboard musí běžet: v jiném okně  python3 server.py
"""

import asyncio
import json
import os
import re
import urllib.request

DASH = os.environ.get("LIVETIME_DASH", "http://localhost:8000")
REFRESH_S = int(os.environ.get("REFRESH_S", "90"))
HEADLESS = os.environ.get("HEADLESS", "0") == "1"
PROFILE = os.path.expanduser("~/.livetime-arb-browser")  # uchová přihlášení

# Přehledové stránky (prematch) + vzor URL detailu zápasu (kde jsou všechny
# trhy = příležitosti). Scraper z přehledu posbírá odkazy na zápasy odpovídající
# `detail` a každý rozklikne. Klidně uprav / přidej.
BOOKS = [
    {"book": "fortuna", "sport": "fotbal",
     "urls": ["https://www.ifortuna.cz/sazeni/fotbal"],
     "detail": r"ifortuna\.cz/sazeni/[^/]+/[^/]+/[^/]+/[^/?#]+"},
    {"book": "tipsport", "sport": "fotbal",
     "urls": ["https://www.tipsport.cz/kurzy/fotbal-16"],
     "detail": r"tipsport\.cz/(kurzy|live)/.*?[a-z]-\d{5,}"},
    {"book": "betano", "sport": "fotbal",
     "urls": ["https://www.betano.cz/sport/fotbal/", "https://www.betano.cz"],
     "detail": r"betano\.cz/(live|sport)/[^/]+/\d{6,}"},
]
MAX_MATCHES = int(os.environ.get("MAX_MATCHES", "30"))   # strop detailů na sázkovku/cyklus

# tlačítka pro odklepnutí cookie/consent lišty (blokuje obsah)
CONSENT = [
    "#onetrust-accept-btn-handler",
    'button:has-text("Souhlasím se vším")', 'button:has-text("Přijmout vše")',
    'button:has-text("Souhlasím")', 'button:has-text("Přijmout")',
    'button:has-text("Rozumím")', 'button:has-text("Accept all")',
    'button:has-text("Accept")', 'button:has-text("OK")',
]

API_RE = re.compile(r"offer|event|odds|kurz|nab[ií]dka|z[aá]pas|prematch|market|selection|outcome|fixture|competition|betoffer", re.I)

# JS scanner spuštěný uvnitř stránky (stejná logika jako userscript scanSmart)
SCANNER_JS = r"""
(cfg) => {
  const BOOK = cfg.book, SPORT = cfg.sport;
  const clean = s => (s||'').replace(/\s+/g,' ').trim();
  const ODDS_RE = /^\d{1,3}[.,]\d{1,2}$/;
  const MARKET_RE = /(v z[aá]pasu|v[yý]sledek z[aá]pasu|po[cč]et (g[oó]l[uů]|roh[uů]|karet|tref|gem|set)|kdo (d[aá]|bude)|v[ií]ce roh[uů]|padne g[oó]l|ka[zž]d[yý] t[yý]m|vst[rř]el|hlavou|dvojtip|handicap|polo[cč]as|p[rř]esn[yý] v[yý]sledek|oba t[yý]my|s[aá]zka bez|celkem g[oó]l|v[ií]t[eě]z|asijsk|1\. ?pol|2\. ?pol|\bBTTS\b)/i;
  const OUTCOME_RE = /^(ano|ne|v[ií]ce ne[zž]|m[eé]n[eě] ne[zž]|nad|pod|remíza|neprohra|nebude remíza|\d+\. g[oó]l)/i;
  function outcomeLabel(el){
    let p=el.previousElementSibling;
    while(p){const t=clean(p.textContent); if(t&&!ODDS_RE.test(t)&&/[a-záčďéěíňóřšťúůýž]/i.test(t)&&t.length<=40)return t; p=p.previousElementSibling;}
    let n=el.parentElement;
    for(let i=0;i<3&&n;i++,n=n.parentElement){const t=clean(n.textContent.replace(clean(el.textContent),'')); if(/[a-záčďéěíňóřšťúůýž]/i.test(t)&&t.length<=40)return t;}
    return '?';
  }
  function lineFrom(label){ if(!/(v[ií]ce|m[eé]n[eě]|nad|pod|over|under)/i.test(label))return null; const m=label.match(/(\d+(?:[.,]\d+)?)/); return m?parseFloat(m[1].replace(',','.')):null; }
  const EVENT_RE=/^[\p{L}][\p{L}\p{M}.\s]{1,28}\s[-–·]\s[\p{L}][\p{L}\p{M}.\s]{1,28}$/u;
  let home='?', away='?', market='?';
  const out=[], seen=new Set();
  const all=document.body?document.body.getElementsByTagName('*'):[];
  for(let i=0;i<all.length;i++){
    const el=all[i], t=clean(el.textContent);
    if(el.children.length===0 && ODDS_RE.test(t)){
      const odds=parseFloat(t.replace(',','.'));
      if(odds>1.01&&odds<1000){
        const label=outcomeLabel(el);
        if(label&&label!=='?'){
          const key=home+'|'+away+'|'+market+'|'+label+'|'+odds;
          if(!seen.has(key)){ seen.add(key);
            out.push({bookmaker:BOOK,sport:SPORT,home,away,market,line:lineFrom(label),outcome:label,odds});
          }
        }
      }
    } else if(t.length<=50 && EVENT_RE.test(t) && !MARKET_RE.test(t)){
      const parts=t.split(/\s[-–·]\s/); if(parts.length===2){ home=clean(parts[0]); away=clean(parts[1]); market='?'; }
    } else if(t.length<=60 && MARKET_RE.test(t) && !OUTCOME_RE.test(t) && !ODDS_RE.test(t)){
      market=t.replace(/[\u{1F4CC}▲▼^]+\s*$/u,'').trim().slice(0,60);
    }
  }
  return out;
}
"""


def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(DASH + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f"  [dashboard?] {path}: {e}  (běží server.py?)")
        return False


async def main():
    from playwright.async_api import async_playwright
    state = {"book": "?"}

    async def on_response(resp):
        try:
            ct = (await resp.header_value("content-type")) or ""
            if "json" not in ct.lower():
                return
            url = resp.url
            if not API_RE.search(url):
                return
            body = await resp.text()
            if len(body) < 150 or len(body) > 4_000_000:
                return
            try:
                obj = json.loads(body)
            except ValueError:
                return
            post("/api/raw", {"bookmaker": state["book"], "url": url[:300], "json": obj})
        except Exception:
            pass

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            PROFILE, headless=HEADLESS,
            viewport={"width": 1400, "height": 1000})
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))

        async def prep(url):
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            for sel in CONSENT:                      # odklepni cookie lištu
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.click(timeout=1500)
                        await page.wait_for_timeout(500)
                        break
                except Exception:
                    pass
            try:
                await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            for _ in range(6):                       # lazy-load: roluj dolů
                await page.mouse.wheel(0, 2200)
                await page.wait_for_timeout(600)

        print(f"🟢 Scraper běží. Dashboard: {DASH}. Obnova každých {REFRESH_S}s.")
        print("   Rozklikávám zápasy do detailu (tam jsou všechny trhy = příležitosti).")
        print("   (Když je potřeba přihlášení / cookie lišta, klikni v okně prohlížeče.)\n")
        while True:
            for b in BOOKS:
                state["book"] = b["book"]
                # 1) přehled → posbírej odkazy na detaily zápasů
                links = []
                for url in b["urls"]:
                    try:
                        await prep(url)
                        hrefs = await page.eval_on_selector_all(
                            "a[href]", "els => els.map(e => e.href)")
                        rx = re.compile(b["detail"], re.I)
                        for h in hrefs:
                            if rx.search(h) and h not in links:
                                links.append(h)
                    except Exception as e:
                        print(f"  {b['book']:<9} přehled chyba: {e}")
                links = links[:MAX_MATCHES]
                print(f"  {b['book']:<9} nalezeno {len(links)} zápasů → rozklikávám…")
                # 2) každý detail → sejmi všechny trhy
                total = 0
                for h in links:
                    try:
                        await prep(h)
                        quotes = await page.evaluate(
                            SCANNER_JS, {"book": b["book"], "sport": b["sport"]})
                        if quotes:
                            post("/api/ingest", {"quotes": quotes})
                            total += len(quotes)
                    except Exception:
                        pass
                print(f"  {b['book']:<9} ✓ {total} kurzů z {len(links)} detailů odesláno")
            print(f"  …spím {REFRESH_S}s (Ctrl+C ukončí)\n")
            await asyncio.sleep(REFRESH_S)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKonec.")
