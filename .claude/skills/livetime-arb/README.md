# livetime-arb — finder sázkových příležitostí (surebet · value · bonusy)

Engine + Claude Code skill, který hledá **„livetime"** příležitosti napříč
sázkovkami **Tipsport, Betano, bet365, Fortuna**:

- **Surebety (arbitráž)** — stejný trh vsazený na všechny výsledky se
  **zaručeným ziskem** (např. Tipsport 3.00 „nad 28.5 es" + bet365 1.83
  „pod 28.5" → **+13.66 %**, vklad 1000 Kč rozdělen 380/620 Kč).
- **Value bety** — +EV jednotlivé sázky (kurz vyšší než férová pravd.).
- **Konverze bonusů / free betů** — bezztrátová (matched betting).

Kurzy se berou **bez API** — importem ze zkopírovaných stránek do vlastní DB.

## Obsah balíčku

| Soubor / složka | Co je uvnitř |
|---|---|
| `SKILL.md` | popis skillu pro Claude Code + postupy |
| **`SPEC_WEBAPP.md`** | **kompletní zadání pro stavbu webového dashboardu (paste-ready)** |
| `STRATEGY.md` | rizika a plán bankrollu na 100 000 Kč (upřímně) |
| `ACCOUNT_LONGEVITY.md` | legální plán, jak udržet účty živé (aby tě nelimitovaly) |
| `scripts/arb.py` | jádro arbitráže (2 i N cest), rozdělení vkladů |
| `scripts/analyze.py` | najde VŠECHNY příležitosti (surebety + value bety, Kelly) |
| `scripts/ingest.py` | import kurzů ze zkopírovaných stránek do DB |
| `scripts/normalize.py` | fuzzy párování zápasů/trhů napříč sázkovkami |
| `scripts/db.py` | lokální SQLite DB kurzů + deník sázek |
| `scripts/freebet.py` | kalkulačka bonusů / free betů |
| `scripts/scan.py` + `bookmakers/` | volitelné adaptéry pro live endpointy |
| `examples/` | demo data (`seed_events.json`, `quotes_sample.json`, …) |
| `tests/` | pytest testy jádra (ověřují i referenčních 13,66 %) |

## Rychlý start (čistý Python 3, žádné závislosti)

```bash
# 1) Test, že engine počítá správně
python3 tests/test_engine.py

# 2) Demo: najdi a seřaď příležitosti v ukázkových datech
python3 scripts/analyze.py examples/seed_events.json -B 100000 --min-margin 0
#   …nebo větší dataset (25 zápasů) pro test řazení/filtrů:
python3 scripts/analyze.py examples/seed_events_large.json -B 100000 --min-margin 1
#   (regenerace: python3 examples/generate_seed.py > examples/seed_events_large.json)

# 3) Rychlý výpočet z konkrétních kurzů
python3 scripts/arb.py calc 3.00 1.83 -T 1000 --labels "Nad 28.5" "Pod 28.5" --books tipsport bet365

# 4) Bez API: import ze zkopírované stránky -> DB -> analýza
python3 scripts/db.py init
python3 scripts/ingest.py paste.txt --db
python3 scripts/analyze.py --db --min-margin 5 --min-edge 5 -B 100000

# 5) Bonus / free bet na jisto
python3 scripts/freebet.py free2 1000 2.00 2.10
```

Blokový formát pro `ingest.py` (zkopíruj kurzy ze stránky, doplň `@` kontext):
```
@book tipsport
@sport tenis
@event Alexander Zverev | Taylor Fritz
@market Esa v zápase | 28.5
Nad | 3.00
Pod | 1.78
```

## Jak to funguje (matematika)

Implikovaná pravd. výsledku = `1 / kurz`. Když `S = Σ(1/kurz) < 1`, existuje
arbitráž s marží `1/S − 1` a vklady `T · (1/kurz_i) / S`. Value bet = kurz
vyšší, než odpovídá férové pravd. spočítané z konsensu sázkovek (po odečtení
marže); velikost sázky přes zlomkový Kelly.

## Důležité (přečti před sázením)

- **20 %+ „jasných" surebetů poctivě skoro neexistuje** — bývá to chyba
  sázkovky (palpable error), kterou stornují, nebo rozdílná pravidla trhu.
  V demu je takový případ schválně označený.
- **Hlavní riziko není matematika, ale limitace účtů.** Viz `STRATEGY.md` a
  `ACCOUNT_LONGEVITY.md`.
- Stabilní výdělek = objem malých marží (1–3 %) + bonusy.
- Jen licencované sázkovky, vlastní jméno, žádné multiúčty. Sázej zodpovědně
  (18+). Daně v ČR konzultuj s poradcem.

## Stavba webového rozhraní

Otevři **`SPEC_WEBAPP.md`** — je to kompletní zadání, které vložíš do Claude
Code. Postaví z toho dashboard (FastAPI + React/Tailwind) s kartami
příležitostí, řazením, filtry, rizikovými štítky, deníkem P/L, bankrollem a
import­ní stránkou. Engine z `scripts/` se znovupoužije, nepřepisuje.
