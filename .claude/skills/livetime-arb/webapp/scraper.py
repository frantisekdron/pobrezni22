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

# Přehledové stránky (prematch). Klidně uprav / přidej.
BOOKS = [
    {"book": "tipsport", "sport": "fotbal",
     "urls": ["https://www.tipsport.cz/kurzy/fotbal-16"]},
    {"book": "fortuna", "sport": "fotbal",
     "urls": ["https://www.ifortuna.cz/sazeni/fotbal"]},
    {"book": "betano", "sport": "fotbal",
     "urls": ["https://www.betano.cz/sport/fotbal/nadchazejici/"]},
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
  const out=[], seen=new Set(); let market='?';
  const all=document.body?document.body.getElementsByTagName('*'):[];
  for(let i=0;i<all.length;i++){
    const el=all[i], t=clean(el.textContent);
    if(el.children.length===0 && ODDS_RE.test(t)){
      const odds=parseFloat(t.replace(',','.'));
      if(odds>1.01&&odds<1000){
        const label=outcomeLabel(el);
        if(label&&label!=='?'){
          const key=market+'|'+label+'|'+odds;
          if(!seen.has(key)){ seen.add(key);
            out.push({bookmaker:BOOK,sport:SPORT,home:'?',away:'?',market,line:lineFrom(label),outcome:label,odds});
          }
        }
      }
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

        print(f"🟢 Scraper běží. Dashboard: {DASH}. Obnova každých {REFRESH_S}s.")
        print("   (Když je potřeba přihlášení / cookie lišta, klikni v okně prohlížeče.)")
        while True:
            for b in BOOKS:
                state["book"] = b["book"]
                for url in b["urls"]:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(4000)
                        for _ in range(6):           # lazy-load: roluj dolů
                            await page.mouse.wheel(0, 2200)
                            await page.wait_for_timeout(700)
                        quotes = await page.evaluate(SCANNER_JS, {"book": b["book"], "sport": b["sport"]})
                        ok = post("/api/ingest", {"quotes": quotes}) if quotes else False
                        print(f"  {b['book']:<9} {len(quotes):>4} kurzů z DOMu  {'✓' if ok else ''}  ({url})")
                    except Exception as e:
                        print(f"  {b['book']:<9} chyba: {e}")
            print(f"  …spím {REFRESH_S}s (Ctrl+C ukončí)\n")
            await asyncio.sleep(REFRESH_S)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKonec.")
