---
name: livetime-arb
description: >-
  Hledá "livetime" arbitrážní příležitosti (surebety) napříč sázkovkami
  Tipsport, Betano, bet365 a Fortuna. Stejný trh (např. esa v zápase nad/pod,
  1X2, počet gemů) vsazený na opačné strany u různých sázkovek tak, aby byl
  zisk zaručený. Spočítá rozdělení vkladů, výplatu a marži. Použij, když uživatel
  chce najít surebet / arbitráž / "livetime" příležitost, porovnat kurzy mezi
  sázkovkami nebo spočítat jisté rozdělení vsazené částky.
---

# Livetime arbitráž (surebet) finder

Najde příležitosti jako na referenčním příkladu: **Tipsport kurz 3.00 na
„nad 28.5 es"** + **bet365 kurz 1.83 na „pod 28.5 es"** → ať padne cokoliv,
**zaručený zisk ~13.66 %**. Rozdělení vkladu 1000 Kč: 379 Kč / 621 Kč.

## Princip (co je arbitráž)

Vsadíme **všechny výsledky jednoho trhu**, každý u sázkovky s **nejvyšším
kurzem**. Když je součet implikovaných pravděpodobností `S = Σ(1/kurz) < 1`,
je výplata stejná ať padne cokoliv → jistý zisk `1/S − 1`.

Vklad na výsledek *i* z celkové částky *T*: `vklad_i = T · (1/kurz_i) / S`.

Sázkovky se musí krýt: **stejný zápas, stejný trh, stejná hranice (line)** a
stejná pravidla při skreči/odstoupení. To je největší riziko — vždy ověř.

## Nástroje (`scripts/`)

| Soubor | K čemu |
|---|---|
| `arb.py` | jádro: výpočet arbitráže (2 i N cest), rozdělení vkladů, sken events JSON |
| `analyze.py` | **najde VŠECHNY příležitosti**: surebety (jakákoliv marže) + value bety (+EV single, Kelly) |
| `ingest.py` | **import kurzů ze zkopírovaných stránek** (žádné API) do kotací/DB |
| `db.py` | vlastní lokální DB kurzů (SQLite) + deník vsazených arbitráží |
| `normalize.py` | spáruje stejné zápasy/trhy napříč sázkovkami (i „Zverev A." vs „Alexander Zverev") |
| `freebet.py` | bezztrátová konverze bonusů/free betů (matched betting) |
| `scan.py` | kompletní sken přes adaptéry (volitelné live endpointy) |
| `bookmakers/` | adaptéry Tipsport / Betano / bet365 / Fortuna |
| `examples/` | vzorové vstupy (`odds_sample.json`, `quotes_sample.json`) |

> **Strategie, rizika a plán na 100 000 Kč: viz `STRATEGY.md`.** Důležité:
> 20 %+ „jasných" surebetů poctivě skoro neexistuje (bývá to chyba sázkovky,
> kterou stornují). Stabilní výdělek = objem malých marží (1–3 %) + bonusy;
> hlavní riziko není matematika, ale **limitace účtů**.

## Hlavní postup (bez API, ze zkopírovaných stránek)

```bash
python3 scripts/db.py init                       # založ DB
python3 scripts/ingest.py paste_tipsport.txt --db   # importuj zkopírovanou stránku
python3 scripts/ingest.py paste_bet365.txt  --db
python3 scripts/analyze.py --db --min-margin 5 --min-edge 5 -B 100000
```

Blokový formát pro `ingest.py` (zkopíruj kurzy ze stránky a doplň @ kontext):
```
@book tipsport
@sport tenis
@event Alexander Zverev | Taylor Fritz
@market Esa v zápase | 28.5
Nad | 3.00
Pod | 1.78
```
`analyze.py` pak vybere nejlepší kurz na každý výsledek napříč sázkovkami,
spočítá surebety i value bety. `--min-margin` / `--min-edge` jsou filtry v %.

## Postup, který používej

### 1) Rychlý výpočet z konkrétních kurzů (nejčastější)
Když uživatel dá kurzy (jako ze snímku z WhatsApp):
```bash
python3 scripts/arb.py calc 3.00 1.83 -T 1000 \
    --labels "Nad 28.5" "Pod 28.5" --books tipsport bet365
```
Vypíše, jestli je to surebet, rozdělení vkladů, výplatu a zisk. Funguje i pro
3-cestné trhy (1X2): `python3 scripts/arb.py calc 2.20 3.60 3.90`.

### 2) Sken více trhů z JSON
Pro každý výsledek dej kurzy z více sázkovek; skript vybere nejvyšší:
```bash
python3 scripts/arb.py scan scripts/../examples/odds_sample.json -m 1.0
```
`-m` = minimální marže v % (filtr).

### 3) Sběr live kurzů (hlavní „scraper" cesta)
Sázkovky nemají veřejné API a aktivně blokují boty (Cloudflare, websockety,
geo-blok, bet365 binární protokol). **Spolehlivý postup je:**

1. **Posbírej kurzy** pro live zápasy ze 4 sázkovek. Možnosti:
   - Claude přes `WebFetch` / `WebSearch` načte aktuální kurzy z veřejných
     stránek (live sekce daného zápasu), nebo
   - uživatel je vloží ručně (typicky bet365 stranu, ta je nejhůř dostupná).
2. **Zapiš je jako plochý list kotací** (formát viz `examples/quotes_sample.json`):
   každý řádek = sázkovka + zápas + trh + line + výsledek + kurz.
3. **Sluč a najdi arbitráž:**
   ```bash
   python3 scripts/normalize.py quotes.json | python3 scripts/arb.py scan /dev/stdin -m 1.0
   ```

`normalize.py` spáruje stejné zápasy i při různém zápisu jmen a sjednotí
názvy trhů (esa/aces, 1X2, počet gemů, dvojchyby).

### 4) Automatické adaptéry (volitelné)
Pokud máš ověřený live endpoint sázkovky (najdeš v DevTools → Network → XHR),
nastav proměnnou prostředí a spusť sken:
```bash
TIPSPORT_LIVE_URL="https://..." FORTUNA_LIVE_URL="https://..." \
  python3 scripts/scan.py --sport tenis --books tipsport fortuna -m 1.0
```
Adaptéry, které endpoint nemají, vrátí prázdno a sken pokračuje s ostatními.
Parsing v `bookmakers/*.py` uprav podle reálné struktury JSONu.

## Co vždy zmínit uživateli (rizika)

- Ověř, že obě sázky jsou **stejný zápas, stejný trh, stejná hranice** a mají
  **stejná pravidla při skreči/odstoupení** (u tenisu časté) — jinak to není
  jistota, ale riziko.
- Kurzy v live se mění během sekund; surebet může zmizet dřív, než vsadíš.
- Limity sázek a možné omezení/zrušení účtu sázkovkou.
- Tohle je nástroj na výpočet a porovnání, ne garance výplaty. Sázej zodpovědně.

## Reference výpočtu (ověřeno)
Kurzy 3.00 a 1.83, vklad 1000 Kč → S = 0.8798, marže 13.66 %,
vklady 379 / 621 Kč, výplata ~1136 Kč, zisk ~136 Kč. (Sedí na referenční snímky.)
