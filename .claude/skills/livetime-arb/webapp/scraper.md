# Plně automatický scraper (bez Tampermonkey)

Robot, který si **sám otevře prohlížeč**, projede přehledy sázkovek, odchytí
jejich API i kurzy a nasype je do dashboardu. Spustíš jeden příkaz.

## Spuštění — dvě okna Terminalu

**Okno 1 — dashboard:**
```bash
cd ~/Desktop/pobrezni22/.claude/skills/livetime-arb/webapp
python3 server.py
```

**Okno 2 — scraper:**
```bash
cd ~/Desktop/pobrezni22/.claude/skills/livetime-arb/webapp
bash scrape.sh
```

`scrape.sh` si **sám** doinstaluje Playwright + prohlížeč Chromium (jednorázově,
chvíli to trvá) a spustí sběr. Otevře se okno prohlížeče — nech ho běžet.
Kdyby vyskočila cookie lišta nebo přihlášení, klikni v něm (profil se uloží,
příště už ne).

Pak v dashboardu (**http://localhost:8000**) → Příležitosti → Zdroj dat
**„Moje DB"** → Najít.

## Co to dělá

- Projíždí přehledy z `BOOKS` ve `scraper.py` (default prematch fotbal na
  Tipsport/Fortuna/Betano) každých 90 s.
- Z DOMu vytáhne kurzy (stejný scanner jako userscript) → `/api/ingest`.
- Odchytí interní API odpovědi → uloží syrový JSON do `/api/raw`
  (z něj doladím přesné parsery per sázkovka).

## Ladění

- Jiné sporty/ligy: uprav `BOOKS` (URL přehledů) nahoře ve `scraper.py`.
- Bez okna (na pozadí): `HEADLESS=1 bash scrape.sh` (ale pro přihlášení nech
  okno viditelné).
- Rychlost obnovy: `REFRESH_S=60 bash scrape.sh`.

## Po prvním běhu

Pošli mi obsah z **http://localhost:8000/api/raw/sample?book=tipsport**
(a fortuna/betano) — podle tvaru JSONu napíšu přesný parser a sběr bude
100% spolehlivý napříč všemi trhy.

## Poznámky

- Běží na tvém Macu (tvá IP, tvá relace) → žádné 403.
- Osobní použití, nepřetěžuj servery (90 s stačí). 18+, licencované sázkovky.
- Potřebuje Python 3 (máš) a internet pro stažení Chromia (~150 MB).
