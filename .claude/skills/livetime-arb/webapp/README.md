# Livetime Arb Dashboard (webapp)

Funkční webové rozhraní nad enginem `livetime-arb`. **Žádné závislosti** —
backend běží na čisté Python stdlib, frontend je jedna HTML stránka. Není
potřeba Node, npm ani pip.

## Spuštění (macOS / Linux)

```bash
cd .claude/skills/livetime-arb/webapp
python3 server.py
# nebo:  ./run.sh        (případně PORT=9000 ./run.sh)
```

Pak otevři **http://localhost:8000** v prohlížeči.

## Co umí

- **Příležitosti** — surebety (karty s rozdělením vkladů, rizikový štítek,
  tlačítka „zkopírovat" a „Vsadit") + value bety, řazené a filtrovatelné
  (min. marže/EV, vklad, bankroll, Kelly). Zdroj: demo data nebo moje DB.
- **Import kurzů** — vlož zkopírovanou stránku v blokovém formátu, naparsuje
  se a uloží do DB; pak se objeví v Příležitostech (zdroj „Moje DB").
- **Deník** — vsazené sázky, změna stavu (open/won/lost/void/settled),
  realizovaný P/L.
- **Bankroll** — zůstatky, max vklad (trend = signál limitace), zdraví účtu.
- **Bonusy** — kalkulačka free betu na jistý zisk.

## Data

SQLite soubor `../data/odds.db` (vytvoří se sám). Přepíšeš přes
`LIVETIME_DB=/cesta/k.db python3 server.py`.

> ⚠ Tohle je nástroj na výpočet a porovnání, ne garance výplaty. 20 %+
> „jasných" surebetů reálně skoro neexistuje. Hlavní riziko = limitace účtů.
> Jen licencované sázkovky, vlastní jméno, 18+. Viz `../STRATEGY.md` a
> `../ACCOUNT_LONGEVITY.md`.
