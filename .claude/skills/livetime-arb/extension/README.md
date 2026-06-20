# Livetime Arb — Chrome rozšíření (sběr kurzů)

Náš vlastní plugin (žádný cizí Tampermonkey). Běží v tvém **normálním
prohlížeči**, takže ho sázkovky neblokují jako robota. Odchytí interní API
stránek a pošle do dashboardu, který je sám naparsuje na kurzy.

## Instalace (jednou, ~1 minuta)

1. Spusť dashboard: v Terminalu
   ```bash
   cd ~/Desktop/pobrezni22/.claude/skills/livetime-arb/webapp
   python3 server.py
   ```
2. V Chrome (nebo Brave) otevři **chrome://extensions**
3. Vpravo nahoře zapni **Režim pro vývojáře** (Developer mode).
4. Klikni **Načíst rozbalené** (Load unpacked) a vyber složku:
   `~/Desktop/pobrezni22/.claude/skills/livetime-arb/extension`
5. Hotovo — rozšíření je aktivní.

## Použití (automatické)

1. Otevři sázkovku (Tipsport / Fortuna / Betano) ve svém prohlížeči jako vždy.
2. Vpravo dole se objeví panel **🟢 Livetime Arb** a začne hlásit
   `📡 zachyceno N · z toho M kurzů do dashboardu`.
3. Procházej přehledy a zápasy normálně — co stránka načte, to se sebere.
   (Tvoje IP + tvá relace → žádné 403, žádný blok.)
4. V dashboardu **http://localhost:8000** → Příležitosti → Zdroj dat
   **„Moje DB"** → Najít.

> Panel má i tlačítko **„Sejmi DOM (záloha)"** pro případ, že by API odchyt
> u nějaké stránky nestačil.

## Kontrola

- **http://localhost:8000/api/raw** — co se zachytilo (sázkovka, URL, velikost).
- Když některá sázkovka kurzy nedává, pošli mi obsah z
  **http://localhost:8000/api/raw/sample?book=tipsport** — doladím parser.

## Poznámky

- Port dashboardu je napevno `8000`. Když ho měníš, uprav `DASH` v `background.js`.
- Čteš data ze své relace pro osobní použití; nepřetěžuj servery. 18+,
  jen licencované sázkovky.
