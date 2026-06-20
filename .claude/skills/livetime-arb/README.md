# livetime-arb — finder arbitrážních (surebet) příležitostí

Claude Code skill, který hledá **„livetime"** arbitráže napříč sázkovkami
**Tipsport, Betano, bet365, Fortuna**: stejný trh vsazený na opačné strany
u různých sázkovek tak, aby byl **zisk zaručený** ať padne cokoliv.

Příklad (z reálného snímku): Tipsport **3.00** na „nad 28.5 es" + bet365
**1.83** na „pod 28.5 es" → **+13.66 % jistý zisk**, vklad 1000 Kč se rozdělí
**379 / 621 Kč**.

## Spuštění

```bash
cd .claude/skills/livetime-arb/scripts

# 1) Rychlý výpočet z kurzů
python3 arb.py calc 3.00 1.83 -T 1000 --labels "Nad 28.5" "Pod 28.5" --books tipsport bet365

# 2) Sken JSON s kurzy z více sázkovek (vybere nejlepší kurz na výsledek)
python3 arb.py scan ../examples/odds_sample.json -m 1.0

# 3) Sloučení kotací z různých sázkovek (fuzzy párování jmen) -> sken
python3 normalize.py ../examples/quotes_sample.json | python3 arb.py scan /dev/stdin -m 1.0
```

Žádné externí závislosti — čistý Python 3.

## Jak to funguje

Implikovaná pravděpodobnost výsledku = `1 / kurz`. Když součet přes všechny
výsledky trhu `S = Σ(1/kurz) < 1`, existuje arbitráž s marží `1/S − 1` a
vklady `T · (1/kurz_i) / S`.

## Sběr live kurzů

Sázkovky nemají veřejné API a blokují automatický přístup. Hlavní cesta je
nechat kurzy nasbírat Clauda (WebFetch) nebo je vložit ručně a spustit výpočet
(viz `SKILL.md`). Adaptéry v `bookmakers/` jsou volitelná kostra pro případ,
že máš ověřený live endpoint (nastav přes proměnné `*_LIVE_URL`).

## Upozornění

Ověř, že obě sázky jsou stejný zápas/trh/hranice a mají stejná pravidla při
skreči. Live kurzy se rychle mění. Nástroj počítá a porovnává — není to
garance výplaty. Sázej zodpovědně (18+).
